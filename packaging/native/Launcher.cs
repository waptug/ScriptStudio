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
[assembly: AssemblyVersion("0.2.0.0")]
static class Program {
 public static readonly string Root=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"ScriptStudioNative");
 public static string Data=Path.Combine(Root,"data");
 public static Action<string> Log=delegate(string s){};
 public static Process Backend;
 public static NativeJob Job;
 public static string Url;
 [STAThread] static int Main(string[] args) {
  Application.EnableVisualStyles();
  bool owned;
  using(var mutex=new Mutex(true,"Local\\ScriptStudio.NativeLauncher"+(args.Length>0?".Checks":""),out owned)) {
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
     if(args[0]=="--serve-test") {
      Data=Path.Combine(Root,"test-data");
      Directory.CreateDirectory(Data);
      Log=delegate(string s){File.AppendAllText(Path.Combine(Data,"launcher.log"),s+Environment.NewLine);};
      Start(); Backend.WaitForExit(); return Backend.ExitCode;
     }
     throw new Exception("Unknown argument");
    }
    Application.Run(new Launcher()); return 0;
   } catch(Exception e) { Log(e.ToString()); if(args.Length==0)MessageBox.Show(e.Message,"ScriptStudio");return 1; }
   finally { if(Job!=null)Job.Dispose(); }
  }
 }
 public static void Start(int port=0) {
  string package=Extract();
  Directory.CreateDirectory(Data);
  string ready=Path.Combine(Data,"ready.json");
  if(File.Exists(ready))File.Delete(ready);
  Log("Starting native PostgreSQL, API, and job worker…");
  Job=new NativeJob();
  var info=new ProcessStartInfo(Path.Combine(package,"python","python.exe"),
   "-X utf8 "+Quote(Path.Combine(package,"runtime.py"))+" --data "+Quote(Data)+" --port "+port) {
    UseShellExecute=false,CreateNoWindow=true,WorkingDirectory=package,RedirectStandardOutput=true,RedirectStandardError=true
   };
  Backend=Process.Start(info); Job.Add(Backend);
  Backend.OutputDataReceived+=(s,e)=>{if(e.Data!=null)Log(e.Data);};
  Backend.ErrorDataReceived+=(s,e)=>{if(e.Data!=null)Log(e.Data);};
  Backend.BeginOutputReadLine();Backend.BeginErrorReadLine();
  for(int i=0;i<1200;i++) {
   if(Backend.HasExited)throw new Exception("Native runtime stopped. See "+Path.Combine(Data,"runtime.log"));
   if(File.Exists(ready)) {
    var json=new System.Web.Script.Serialization.JavaScriptSerializer().Deserialize<System.Collections.Generic.Dictionary<string,object>>(File.ReadAllText(ready));
    Url=(string)json["url"];Log("Ready: "+Url);return;
   }
   Thread.Sleep(250);
  }
  throw new Exception("Startup timed out. See the logs in "+Data);
 }
 public static void Stop() {
  if(Backend==null||Backend.HasExited)return;
  Log("Finishing active jobs and stopping native services…");
  File.WriteAllText(Path.Combine(Data,"stop.request"),"stop");
  Backend.WaitForExit();
  Job.Dispose();Job=null;Log("Stopped. Projects and media are saved.");
 }
    public static string Extract() {
        string executable = Assembly.GetExecutingAssembly().Location;
        using(var input = File.OpenRead(executable)) {
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
            // Always check the EXE's payload, including repeat launches.
            input.Position = input.Length - 48 - length;
            Directory.CreateDirectory(Path.Combine(Root,"packages"));
            string temporary = Path.Combine(Root,"packages",Guid.NewGuid().ToString("N")+".zip");
            try {
                Log("Verifying bundled Windows runtimes…");
                using(var output = File.Create(temporary))
                using(var hash = SHA256.Create()) {
                    var buffer = new byte[1024*1024];
                    long remaining = length;
                    while(remaining > 0) {
                        int count = input.Read(buffer,0,(int)Math.Min(buffer.Length,remaining));
                        if(count == 0) throw new Exception("Package is truncated.");
                        output.Write(buffer,0,count); hash.TransformBlock(buffer,0,count,null,0); remaining -= count;
                    }
                    hash.TransformFinalBlock(new byte[0],0,0);
                    if(!hash.Hash.SequenceEqual(expected)) throw new Exception("Package checksum failed. Obtain a fresh copy of the EXE.");
                }
                if(File.Exists(marker) && File.ReadAllText(marker) == id) return destination;
                if(Directory.Exists(destination)) throw new Exception("Incomplete package directory exists: " + destination);
                string staging = destination + ".staging-" + Guid.NewGuid().ToString("N");
                Directory.CreateDirectory(staging);
                try {
                    using(var archive = ZipFile.OpenRead(temporary)) {
                        foreach(var entry in archive.Entries) {
                            string file = Path.GetFullPath(Path.Combine(staging,entry.FullName));
                            if(!file.StartsWith(staging+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase) || entry.FullName.Contains(":"))
                                throw new Exception("Unsafe package entry.");
                            Directory.CreateDirectory(Path.GetDirectoryName(file));
                            using(var source = entry.Open()) using(var target = File.Create(file)) source.CopyTo(target);
                        }
                    }
                    foreach(string name in new[]{"runtime.py","python/python.exe","postgres/bin/postgres.exe","openshot/MediaHost.exe","source.zip","LICENSE.txt","README.txt"})
                        if(!File.Exists(Path.Combine(staging,name))) throw new Exception("Package is missing " + name);
                    File.WriteAllText(Path.Combine(staging,"package.sha256"),id);
                    Directory.Move(staging,destination);
                } catch { Directory.Delete(staging,true); throw; }
                return destination;
            } finally { if(File.Exists(temporary)) File.Delete(temporary); }
        }
    }

    public static string Hex(byte[] data) { return BitConverter.ToString(data).Replace("-","").ToLowerInvariant(); }
    static string Quote(string arg) {
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
 public Launcher() {
  Text="ScriptStudio · Native Windows";Width=740;Height=480;StartPosition=FormStartPosition.CenterScreen;
  BackColor=Color.FromArgb(16,22,30);ForeColor=Color.White;Font=new Font("Segoe UI",10);
  Icon=new Icon(Assembly.GetExecutingAssembly().GetManifestResourceStream("ScriptStudio.ico"));
  var title=new Label{Text="ScriptStudio\nStandalone Windows studio · offline mock mode",Dock=DockStyle.Top,Height=78,Padding=new Padding(18,14,0,0),Font=new Font("Segoe UI",14)};
  var buttons=new FlowLayoutPanel{Dock=DockStyle.Bottom,Height=64,Padding=new Padding(10)};
  var open=new Button{Text="Open studio",Width=120,Height=38};
  var files=new Button{Text="Project files",Width=120,Height=38};
  foreach(var button in new[]{stop,open,files}){button.BackColor=Color.LightGray;button.ForeColor=Color.FromArgb(20,25,32);}
  buttons.Controls.AddRange(new Control[]{start,stop,open,files});
  Controls.Add(log);Controls.Add(title);Controls.Add(buttons);
  Program.Log=s=>{if(!IsDisposed&&IsHandleCreated)BeginInvoke((Action)(()=>log.AppendText(s+Environment.NewLine)));};
  start.Click+=async(s,e)=>await Work(()=>{Program.Start();Process.Start(Program.Url);});
  stop.Click+=async(s,e)=>await Work(Program.Stop);
  open.Click+=(s,e)=>{if(Program.Url!=null&&Program.Backend!=null&&!Program.Backend.HasExited)Process.Start(Program.Url);};
  files.Click+=(s,e)=>{Directory.CreateDirectory(Program.Data);Process.Start("explorer.exe",Program.Data);};
  FormClosing+=async(s,e)=>{
   if(closing)return;e.Cancel=true;if(busy)return;
   await Work(Program.Stop);closing=true;Close();
  };
 }
 async Task Work(Action action){if(busy)return;busy=true;start.Enabled=false;stop.Enabled=false;try{await Task.Run(action);}catch(Exception e){Program.Log(e.Message);}finally{busy=false;start.Enabled=Program.Backend==null||Program.Backend.HasExited;stop.Enabled=!start.Enabled;}}
}
