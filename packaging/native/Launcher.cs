using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Runtime.InteropServices;
[assembly: AssemblyTitle("ScriptStudio Native")]
[assembly: AssemblyDescription("Standalone native Windows script-to-video studio")]
[assembly: AssemblyVersion("0.3.0.0")]
static class Program {
 public static readonly string LaunchDirectory=Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
 public static string Root=Path.Combine(LaunchDirectory,"ScriptStudioNative");
 public const long WorkingReserve=2L*1024*1024*1024;
 public static string Data=Path.Combine(Root,"data");
 public static Action<string> Log=delegate(string s){};
 public static Process Backend;
 public static NativeJob Job;
 public static string Url;
 static bool browserStarted;
 public static string WorkspaceData(string name) {
  if(name==null||!System.Text.RegularExpressions.Regex.IsMatch(name,"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"))
   throw new ArgumentException("Workspace names must contain 1-64 letters, numbers, underscores or hyphens, starting with a letter or number.");
  return Path.Combine(Root,"workspace-"+name.ToLowerInvariant());
 }
 [STAThread] static int Main(string[] args) {
  Application.EnableVisualStyles();
  string installed=Path.Combine(LaunchDirectory,"installation.json");
  if(File.Exists(installed)) {
   var config=new System.Web.Script.Serialization.JavaScriptSerializer().Deserialize<System.Collections.Generic.Dictionary<string,object>>(File.ReadAllText(installed));
   Root=Path.GetFullPath((string)config["storage"]);Data=Path.Combine(Root,"data");
  }
  bool autoStart=args.Length>0&&args[args.Length-1]=="--start";
  if(autoStart)args=args.Take(args.Length-1).ToArray();
  string workspace=null;
  if(args.Length>0&&args[0]=="--workspace") {
   try {
    if(args.Length!=2)throw new ArgumentException("Use --workspace followed by one workspace name.");
    Data=WorkspaceData(args[1]);workspace=args[1].ToLowerInvariant();args=new string[0];
   } catch(Exception e) {Console.Error.WriteLine(e.Message);return 1;}
  }
  bool owned;
  using(var mutex=new Mutex(true,"Local\\ScriptStudio.NativeLauncher"+(workspace!=null?".Workspace."+workspace:args.Length>0?".Checks":""),out owned)) {
   if(!owned) { MessageBox.Show("ScriptStudio is already running. Use its launcher window."); return 2; }
   try {
    if(args.Length>0) {
     if(args[0]=="--ui-test") {
      using(var form=new Launcher()) {
       form.Show();Application.DoEvents();
       using(var bitmap=new Bitmap(form.Width,form.Height)) {
        form.DrawToBitmap(bitmap,new Rectangle(0,0,form.Width,form.Height));
        bitmap.Save(args[1],System.Drawing.Imaging.ImageFormat.Png);
       }
      }
      return 0;
     }
     if(args[0]=="--verify") { Console.WriteLine(Extract()); return 0; }
     if(args[0]=="--setup-serve") {
      if(args.Length==2&&args[1]=="--check")Data=Path.Combine(Root,"setup-verification");
      Directory.CreateDirectory(Data);
      Log=delegate(string s){File.AppendAllText(Path.Combine(Data,"launcher.log"),s+Environment.NewLine);};
      Start();Backend.WaitForExit();return Backend.ExitCode;
     }
     if(args[0]=="--serve-test") {
      Data=Path.Combine(Root,"test-data");
      Directory.CreateDirectory(Data);
      Log=delegate(string s){File.AppendAllText(Path.Combine(Data,"launcher.log"),s+Environment.NewLine);};
      Start(); if(args.Length>1&&args[1]=="--open-browser")OpenStudio(); Backend.WaitForExit(); return Backend.ExitCode;
     }
     throw new Exception("Unknown argument");
    }
    Application.Run(new Launcher(autoStart)); return 0;
   } catch(Exception e) { Log(e.ToString()); Console.Error.WriteLine(e.Message); if(args.Length==0)MessageBox.Show(e.Message,"ScriptStudio");return e is DiskSpaceException?3:1; }
   finally { if(Job!=null)Job.Dispose(); }
  }
 }
 public static void Start(int port=0) {
  try {StartBackend(port);} catch {if(Job!=null){Job.Dispose();Job=null;}throw;}
 }
 static void StartBackend(int port) {
  string package=Extract();
  CheckSpace(WorkingReserve);
  Directory.CreateDirectory(Data);
  string ready=Path.Combine(Data,"ready.json");
  if(File.Exists(ready))File.Delete(ready);
  browserStarted=false;
  Log("Starting native PostgreSQL, API, and job worker…");
  Job=new NativeJob();
  var info=new ProcessStartInfo(Path.Combine(package,"python","python.exe"),
   "-X utf8 "+Quote(Path.Combine(package,"runtime.py"))+" --data "+Quote(Data)+" --port "+port) {
    UseShellExecute=false,CreateNoWindow=true,WorkingDirectory=package,RedirectStandardOutput=true,RedirectStandardError=true
   };
  ConfigureEnvironment(info);
  Backend=Process.Start(info); Job.Add(Backend);
  Backend.OutputDataReceived+=(s,e)=>{if(e.Data!=null)Log(e.Data);};
  Backend.ErrorDataReceived+=(s,e)=>{if(e.Data!=null)Log(e.Data);};
  Backend.BeginOutputReadLine();Backend.BeginErrorReadLine();
  DateTime deadline=DateTime.UtcNow.AddMinutes(5);
  while(DateTime.UtcNow<deadline) {
   if(Backend.HasExited)throw new Exception("Native runtime stopped. See "+Path.Combine(Data,"runtime.log"));
   string endpoint;
   if(TryReadReady(ready,out endpoint)&&Healthy(endpoint)){Url=endpoint;Log("Ready: "+Url);return;}
   Thread.Sleep(250);
  }
  throw new Exception("Startup timed out. See the logs in "+Data);
 }
 public static bool TryReadReady(string file,out string endpoint) {
  endpoint=null;
  try {
   using(var stream=new FileStream(file,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))using(var reader=new StreamReader(stream)){
    var record=new System.Web.Script.Serialization.JavaScriptSerializer().Deserialize<System.Collections.Generic.Dictionary<string,object>>(reader.ReadToEnd());
    object value;Uri uri;if(record==null||!record.TryGetValue("url",out value)||!(value is string)||!Uri.TryCreate((string)value,UriKind.Absolute,out uri)||uri.Scheme!="http"||uri.Host!="127.0.0.1")return false;
    endpoint=(string)value;return true;
   }
  }catch(IOException){return false;}catch(UnauthorizedAccessException){return false;}catch(ArgumentException){return false;}
 }
 public static bool Healthy(string endpoint) {
  try {var request=(System.Net.HttpWebRequest)System.Net.WebRequest.Create(endpoint+"/api/health");request.Proxy=null;request.Timeout=1000;request.ReadWriteTimeout=1000;
   using(var response=request.GetResponse())using(var reader=new StreamReader(response.GetResponseStream())){var record=new System.Web.Script.Serialization.JavaScriptSerializer().Deserialize<System.Collections.Generic.Dictionary<string,object>>(reader.ReadToEnd());return record!=null&&record.ContainsKey("status")&&(string)record["status"]=="ok";}
  }catch(System.Net.WebException){return false;}catch(IOException){return false;}catch(ArgumentException){return false;}
 }
 public static void Stop() {
  if(Backend==null||Backend.HasExited)return;
  Log("Finishing active jobs and stopping native services…");
  File.WriteAllText(Path.Combine(Data,"stop.request"),"stop");
  Backend.WaitForExit();
  Job.Dispose();Job=null;Log("Stopped. Projects and media are saved.");
 }
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern bool GetDiskFreeSpaceEx(string path, out ulong available, out ulong total, out ulong free);
    public static void CheckSpace(long required) {
        ulong available,total,free;
        string volume=Root;while(!Directory.Exists(volume))volume=Path.GetDirectoryName(volume);
        if(!GetDiskFreeSpaceEx(volume,out available,out total,out free))
            throw new IOException("Cannot check free space in " + LaunchDirectory + ". Close the launcher and move the EXE to a writable local folder.");
        RequireSpace(required,(long)Math.Min(available,(ulong)long.MaxValue));
    }
    public static void RequireSpace(long required,long available) {
        if(available<required) throw new DiskSpaceException(
            "Not enough free disk space in " + LaunchDirectory + ".\r\n\r\n" +
            "Required: " + (required/1073741824.0).ToString("F2") + " GiB (including 2 GiB working space).\r\n" +
            "Available: " + (available/1073741824.0).ToString("F2") + " GiB.\r\n\r\n" +
            "Close the launcher, free space on this drive, or move the EXE and its ScriptStudioNative folder together to a drive with more space. No services were started. Click OK to close the launcher.");
    }
    public static void ConfigureEnvironment(ProcessStartInfo info) {
        string temp=Path.Combine(Data,"temp"), profile=Path.Combine(Data,"profile");
        foreach(string directory in new[]{temp,profile,Path.Combine(profile,"AppData","Local"),Path.Combine(profile,"AppData","Roaming")})Directory.CreateDirectory(directory);
        foreach(string key in new[]{"TEMP","TMP","TMPDIR"})info.EnvironmentVariables[key]=temp;
        info.EnvironmentVariables["USERPROFILE"]=profile;
        info.EnvironmentVariables["HOME"]=profile;
        info.EnvironmentVariables["LOCALAPPDATA"]=Path.Combine(profile,"AppData","Local");
        info.EnvironmentVariables["APPDATA"]=Path.Combine(profile,"AppData","Roaming");
        info.EnvironmentVariables["PYTHONPYCACHEPREFIX"]=Path.Combine(Data,"cache","python");
        info.EnvironmentVariables["XDG_CACHE_HOME"]=Path.Combine(Data,"cache");
    }
    public static void OpenStudio() {
        if(Url==null||Backend==null||Backend.HasExited)return;
        string browser=new[]{
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),"Microsoft","Edge","Application","msedge.exe"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),"Microsoft","Edge","Application","msedge.exe"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),"Google","Chrome","Application","chrome.exe"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Google","Chrome","Application","chrome.exe")
        }.FirstOrDefault(File.Exists);
        if(browser==null)throw new Exception("Microsoft Edge or Google Chrome is required to open the studio with a portable browser profile.");
        string profile=Path.Combine(Data,"browser"), downloads=Path.Combine(Root,"downloads");
        Directory.CreateDirectory(downloads);
        string preferences=Path.Combine(profile,"Default","Preferences");
        // Refresh absolute download paths after moving the portable folder, before launching its browser.
        if(!browserStarted){
            Directory.CreateDirectory(Path.GetDirectoryName(preferences));
            var json=new System.Web.Script.Serialization.JavaScriptSerializer();
            var settings=File.Exists(preferences)?json.Deserialize<System.Collections.Generic.Dictionary<string,object>>(File.ReadAllText(preferences)):new System.Collections.Generic.Dictionary<string,object>();
            settings["download"]=new {default_directory=downloads,prompt_for_download=false,directory_upgrade=true};
            File.WriteAllText(preferences,json.Serialize(settings));
        }
        var info=new ProcessStartInfo(browser,"--user-data-dir="+Quote(profile)+" --disk-cache-dir="+Quote(Path.Combine(Data,"cache","browser"))+
            " --no-first-run --no-default-browser-check --disable-background-mode --app="+Quote(Url)) {UseShellExecute=false,WorkingDirectory=Root};
        ConfigureEnvironment(info);
        var browserProcess=Process.Start(info);
        if(!browserStarted){Job.Add(browserProcess);browserStarted=true;}
    }
    public static string Extract() {
        using(var input = File.OpenRead(Assembly.GetExecutingAssembly().Location)) {
            if(input.Length < 48) throw new Exception("Package footer is missing.");
            input.Position = input.Length - 48;
            var reader = new BinaryReader(input);
            if(Encoding.ASCII.GetString(reader.ReadBytes(8)) != "SSTPKG01") throw new Exception("Package footer is invalid.");
            long length = reader.ReadInt64();
            byte[] expected = reader.ReadBytes(32);
            if(length <= 0 || length > input.Length - 48) throw new Exception("Invalid package length.");
            string id = Hex(expected);
            string destination = Path.Combine(Root,"packages",id.Substring(0,16));
            string marker = Path.Combine(destination,"package.sha256");
            using(var payload=new PayloadStream(input,input.Length-48-length,length)) {
                Log("Verifying bundled Windows runtimes…");
                using(var hash=SHA256.Create())
                    if(!hash.ComputeHash(payload).SequenceEqual(expected))throw new Exception("Package checksum failed. Obtain a fresh copy of the EXE.");
                bool cached=File.Exists(marker) && File.ReadAllText(marker)==id;
                payload.Position=0;
                using(var archive=new ZipArchive(payload,ZipArchiveMode.Read,true)) {
                    long required=WorkingReserve;
                    var names=new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase);
                    foreach(var entry in archive.Entries) {
                        string file=Path.GetFullPath(Path.Combine(destination,entry.FullName));
                        if(!file.StartsWith(destination+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase) || entry.FullName.Contains(":"))
                            throw new Exception("Unsafe package entry.");
                        if(!names.Add(file)||entry.FullName.Split(new[]{'/','\\'}).Any(p=>p==".."||p.EndsWith(".")||p.EndsWith(" ")||System.Text.RegularExpressions.Regex.IsMatch(p,"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\\.|$)",System.Text.RegularExpressions.RegexOptions.IgnoreCase)))throw new IOException("Ambiguous Windows archive path");
                        if(!cached)required=checked(required+entry.Length+4096);
                    }
                    CheckSpace(required); // No extraction or temporary ZIP is written before this check.
                    if(cached){
                        try {
                            var embedded=archive.GetEntry("file-inventory.json");
                            if(embedded!=null){using(var source=embedded.Open())using(var hash=SHA256.Create())using(var existing=File.OpenRead(Path.Combine(destination,"file-inventory.json")))if(!hash.ComputeHash(source).SequenceEqual(hash.ComputeHash(existing)))throw new IOException("Cached inventory changed");}
                            VerifyInventory(destination);return destination;
                        } catch(IOException) {
                            // Rebuild from the verified payload; retain changed files for inspection.
                            CheckSpace(checked(WorkingReserve+archive.Entries.Sum(e=>e.Length+4096)));
                            Directory.Move(destination,destination+".repair-"+Guid.NewGuid().ToString("N"));
                            cached=false;
                        }
                    }
                    if(Directory.Exists(destination))throw new Exception("Incomplete package directory exists: "+destination);
                    string staging=destination+".staging-"+Guid.NewGuid().ToString("N");
                    Directory.CreateDirectory(staging);
                    try {
                        foreach(var entry in archive.Entries) {
                            string file=Path.GetFullPath(Path.Combine(staging,entry.FullName));
                            if(entry.Name.Length==0){Directory.CreateDirectory(file);continue;}
                            Directory.CreateDirectory(Path.GetDirectoryName(file));
                            using(var source=entry.Open())using(var target=File.Create(file))source.CopyTo(target);
                        }
                        foreach(string name in new[]{"runtime.py","python/python.exe","postgres/bin/postgres.exe","openshot/MediaHost.exe","source.zip","LICENSE.txt","README.txt"})
                            if(!File.Exists(Path.Combine(staging,name)))throw new Exception("Package is missing "+name);
                        VerifyInventory(staging);
                        File.WriteAllText(Path.Combine(staging,"package.sha256"),id);
                        Directory.Move(staging,destination);
                    } catch {
                        try {Directory.Delete(staging,true);}catch {} // Preserve the original failure, including a full disk.
                        throw;
                    }
                }
                return destination;
            }
        }
    }

    public static string Hex(byte[] data) { return BitConverter.ToString(data).Replace("-","").ToLowerInvariant(); }
    public static void VerifyInventory(string directory) {
        string inventory=Path.Combine(directory,"file-inventory.json");
        // Legacy portable packages did not include this inventory. New setup builds require it.
        if(!File.Exists(inventory))return;
        var serializer=new System.Web.Script.Serialization.JavaScriptSerializer {MaxJsonLength=64*1024*1024};
        var files=serializer.Deserialize<System.Collections.Generic.Dictionary<string,string>>(File.ReadAllText(inventory));
        foreach(var pair in files){
            string file=Path.GetFullPath(Path.Combine(directory,pair.Key));
            if(!file.StartsWith(directory+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)||!File.Exists(file))throw new IOException("Missing or unsafe component: "+pair.Key);
            string cursor=file;while(cursor!=directory){if((File.GetAttributes(cursor)&FileAttributes.ReparsePoint)!=0)throw new IOException("Component link refused");cursor=Path.GetDirectoryName(cursor);}
            using(var source=File.OpenRead(file))using(var hash=SHA256.Create())if(Hex(hash.ComputeHash(source))!=pair.Value)throw new IOException("Component needs repair: "+pair.Key);
        }
        VerifyNames(directory,directory,new System.Collections.Generic.HashSet<string>(files.Keys,StringComparer.OrdinalIgnoreCase));
    }
    static void VerifyNames(string root,string folder,System.Collections.Generic.HashSet<string> expected){
        if((File.GetAttributes(folder)&FileAttributes.ReparsePoint)!=0)throw new IOException("Component directory link refused");
        foreach(string file in Directory.GetFiles(folder)){
            string name=file.Substring(root.Length+1).Replace('\\','/');
            if(name!="file-inventory.json"&&name!="package.sha256"&&!expected.Contains(name))throw new IOException("Unexpected component: "+name);
        }
        foreach(string child in Directory.GetDirectories(folder))VerifyNames(root,child,expected);
    }
    public static string Quote(string arg) {
        // Windows command-line quoting (no shell is involved).
        // WSL's option parser needs bare switches, unlike CommandLineToArgvW.
        if(arg.Length > 0 && !arg.Any(Char.IsWhiteSpace) && !arg.Contains("\"")) return arg;
        var output = new StringBuilder("\""); int slashes=0;
        foreach(char c in arg) {
            if(c=='\\') { slashes++; continue; }
            if(c=='"') { output.Append('\\',slashes*2+1); output.Append(c); slashes=0; continue; }
            output.Append('\\',slashes); slashes=0; output.Append(c);
        }
        output.Append('\\',slashes*2); return output.Append('"').ToString();
    }
}
sealed class DiskSpaceException : IOException { public DiskSpaceException(string message):base(message){} }
// Seekable view of the appended ZIP: avoids a second compressed copy on disk.
sealed class PayloadStream : Stream {
 readonly Stream source; readonly long offset,length; long position;
 public PayloadStream(Stream source,long offset,long length){this.source=source;this.offset=offset;this.length=length;}
 public override bool CanRead{get{return true;}} public override bool CanSeek{get{return true;}} public override bool CanWrite{get{return false;}}
 public override long Length{get{return length;}}
 public override long Position{get{return position;}set{Seek(value,SeekOrigin.Begin);}}
 public override int Read(byte[] buffer,int start,int count){source.Position=offset+position;int read=source.Read(buffer,start,(int)Math.Min(count,length-position));position+=read;return read;}
 public override long Seek(long value,SeekOrigin origin){long next=origin==SeekOrigin.Begin?value:origin==SeekOrigin.Current?position+value:length+value;if(next<0||next>length)throw new IOException("Invalid package seek");return position=next;}
 public override void Flush(){} public override void SetLength(long value){throw new NotSupportedException();}
 public override void Write(byte[] buffer,int start,int count){throw new NotSupportedException();}
}
// OS-owned process containment: closing/crashing the launcher leaves no service
// orphan. PostgreSQL performs crash recovery if a hard process termination occurs.
sealed class NativeJob : IDisposable {
 [DllImport("kernel32",CharSet=CharSet.Unicode)] static extern IntPtr CreateJobObject(IntPtr a,string n);
 [DllImport("kernel32")] static extern bool SetInformationJobObject(IntPtr h,int c,IntPtr p,uint l);
 [DllImport("kernel32")] static extern bool AssignProcessToJobObject(IntPtr h,IntPtr p);
 [DllImport("kernel32")] static extern bool CloseHandle(IntPtr h);
 [StructLayout(LayoutKind.Sequential)] struct Basic {public long PerProcess,PerJob;public uint Flags;public UIntPtr Min,Max;public uint Active;public UIntPtr Affinity;public uint Priority,Scheduling;}
 [StructLayout(LayoutKind.Sequential)] struct IO {public ulong ReadOps,WriteOps,OtherOps,ReadBytes,WriteBytes,OtherBytes;}
 [StructLayout(LayoutKind.Sequential)] struct Extended {public Basic Basic;public IO IO;public UIntPtr ProcessMemory,JobMemory,PeakProcess,PeakJob;}
 IntPtr handle;
 public NativeJob() {
  handle=CreateJobObject(IntPtr.Zero,null);
  var limits=new Extended();limits.Basic.Flags=0x2000;
  int size=Marshal.SizeOf(limits);IntPtr p=Marshal.AllocHGlobal(size);
  try {Marshal.StructureToPtr(limits,p,false);if(!SetInformationJobObject(handle,9,p,(uint)size))throw new Exception("Cannot configure native process containment");}
  finally{Marshal.FreeHGlobal(p);}
 }
 public void Add(Process p){if(!AssignProcessToJobObject(handle,p.Handle)){p.Kill();throw new Exception("Cannot contain native service process");}}
 public void Dispose(){if(handle!=IntPtr.Zero){CloseHandle(handle);handle=IntPtr.Zero;}}
}
class Launcher : Form {
 TextBox log=new TextBox {Multiline=true,ReadOnly=true,ScrollBars=ScrollBars.Vertical,Dock=DockStyle.Fill,BackColor=Color.FromArgb(23,29,37),ForeColor=Color.White};
 Button start=new Button {Text="Start studio",Width=125,Height=38,BackColor=Color.FromArgb(188,236,82),ForeColor=Color.Black};
 Button stop=new Button {Text="Stop studio",Width=120,Height=38};
 bool busy,closing;
 public Launcher(bool autoStart=false) {
  Text="ScriptStudio · Native Windows";Width=740;Height=480;StartPosition=FormStartPosition.CenterScreen;
  BackColor=Color.FromArgb(16,22,30);ForeColor=Color.White;Font=new Font("Segoe UI",10);
  Icon=new Icon(Assembly.GetExecutingAssembly().GetManifestResourceStream("ScriptStudio.ico"));
  var title=new Label{Text="ScriptStudio\nStandalone Windows studio · local AI and mock workflows",Dock=DockStyle.Top,Height=78,Padding=new Padding(18,14,0,0),Font=new Font("Segoe UI",14)};
  var buttons=new FlowLayoutPanel{Dock=DockStyle.Bottom,Height=64,Padding=new Padding(10)};
  var open=new Button{Text="Open studio",Width=120,Height=38};
  var files=new Button{Text="Project files",Width=120,Height=38};
  foreach(var button in new[]{stop,open,files}){button.BackColor=Color.LightGray;button.ForeColor=Color.FromArgb(20,25,32);}
  buttons.Controls.AddRange(new Control[]{start,stop,open,files});
  Controls.Add(log);Controls.Add(title);Controls.Add(buttons);
  log.Text="Storage folder: "+Program.Root+Environment.NewLine;
  string legacy=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"ScriptStudioNative","data");
  if(!Directory.Exists(Program.Data)&&Directory.Exists(legacy))log.AppendText("Previous projects found at "+legacy+". To reuse them, close the old studio and move that complete data folder to "+Program.Data+" before starting."+Environment.NewLine);
  Program.Log=s=>{if(!IsDisposed&&IsHandleCreated)BeginInvoke((Action)(()=>log.AppendText(s+Environment.NewLine)));};
  start.Click+=async(s,e)=>await Work(()=>{Program.Start();Program.OpenStudio();});
  stop.Click+=async(s,e)=>await Work(Program.Stop);
  open.Click+=async(s,e)=>await Work(Program.OpenStudio);
  files.Click+=(s,e)=>{Directory.CreateDirectory(Program.Data);Process.Start("explorer.exe",Program.Data);};
  FormClosing+=async(s,e)=>{
   if(closing)return;e.Cancel=true;if(busy)return;
   await Work(Program.Stop);closing=true;Close();
  };
  if(autoStart)Shown+=async(s,e)=>await Work(()=>{Program.Start();Program.OpenStudio();});
 }
 async Task Work(Action action){
  if(busy)return;busy=true;start.Enabled=false;stop.Enabled=false;bool exit=false;
  try{await Task.Run(action);}
  catch(Exception e){
   Program.Log(e.Message);
   if(e is DiskSpaceException){MessageBox.Show(this,e.Message,"ScriptStudio · Insufficient disk space",MessageBoxButtons.OK,MessageBoxIcon.Warning);exit=true;}
   else MessageBox.Show(this,e.Message+"\r\n\r\nStorage folder: "+Program.Root,"ScriptStudio could not complete the operation",MessageBoxButtons.OK,MessageBoxIcon.Error);
  }
  finally{busy=false;start.Enabled=Program.Backend==null||Program.Backend.HasExited;stop.Enabled=!start.Enabled;}
  if(exit){closing=true;Close();}
 }
}
