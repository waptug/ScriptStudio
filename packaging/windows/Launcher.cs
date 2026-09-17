using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

[assembly: AssemblyTitle("ScriptStudio")]
[assembly: AssemblyDescription("Offline application package — requires a Linux Docker engine")]
[assembly: AssemblyVersion("0.1.0.0")]

static class Program {
    public static readonly string Root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "ScriptStudio");
    public static string Package;
    public static Action<string> Log = delegate(string value) {};
    static string docker;
    static bool wsl;
    static string distribution;
    static string project;
    static string envFile;
    static int port;

    [STAThread]
    static int Main(string[] args) {
        Application.EnableVisualStyles();
        bool owned;
        using (var mutex = new Mutex(true, "Local\\ScriptStudio.PackageLauncher", out owned)) {
            if (!owned) { if (args.Length == 0) MessageBox.Show("Another ScriptStudio launcher is already open."); return 2; }
            try {
                if (args.Length > 0) {
                    string report = args.Length > 1 ? args[1] : Path.Combine(Root,"package-check.txt");
                    Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(report)));
                    Log = delegate(string value) { File.AppendAllText(report,value+Environment.NewLine); };
                    if (args[0] == "--ui-test") {
                        using(var form=new Launcher()) {
                            form.Show(); Application.DoEvents();
                            using(var bitmap=new Bitmap(form.Width,form.Height)) {
                                form.DrawToBitmap(bitmap,new Rectangle(0,0,form.Width,form.Height));
                                bitmap.Save(Path.ChangeExtension(report,"png"),System.Drawing.Imaging.ImageFormat.Png);
                            }
                            form.Close();
                        }
                        File.AppendAllText(report,"PASS: native Windows launcher rendered\n"); return 0;
                    }
                    if (args[0] == "--runtime-test") { DetectDocker(); Log("PASS: runtime detection"); return 0; }
                    if (args[0] == "--verify") { Package = Extract(); Log("PASS: embedded package verified and extracted to " + Package); return 0; }
                    if (args[0] == "--start-test" || args[0] == "--stop-test") {
                        // An isolated test project/port, never the user's desktop or development volumes.
                        project = "scriptstudio-exe-test";
                        envFile = Path.Combine(Root,"test.env");
                        port = 18089;
                        Package = Extract(); DetectDocker(); PrepareEnvironment();
                        if (args[0] == "--start-test") Start(); else Stop();
                        Log("PASS: " + args[0]); return 0;
                    }
                    throw new Exception("Unknown command. Supported: --verify, --runtime-test, --ui-test, --start-test, --stop-test [report path].");
                }
                Application.Run(new Launcher());
                return 0;
            } catch(Exception e) {
                Log("ERROR: " + e.Message);
                if(args.Length == 0) MessageBox.Show(e.Message,"ScriptStudio",MessageBoxButtons.OK,MessageBoxIcon.Error);
                return 1;
            }
        }
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
                Log("Verifying bundled application images…");
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
                    foreach(string name in new[]{"compose.json","images.tar.gz","images.txt","source.zip","LICENSE.txt","README.txt"})
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
    static string Run(string file, IEnumerable<string> args, int seconds, Encoding encoding=null) {
        var info = new ProcessStartInfo(file,String.Join(" ",args.Select(Quote))) {
            UseShellExecute=false, CreateNoWindow=true, RedirectStandardOutput=true, RedirectStandardError=true,
            WorkingDirectory=Root
        };
        if(encoding!=null) info.StandardOutputEncoding=encoding;
        // Do not inherit provider credentials or compose overrides from a shell.
        foreach(string key in new[]{"COMPOSE_FILE","COMPOSE_PROJECT_NAME","POSTGRES_PASSWORD","SCRIPTSTUDIO_PORT","LIVE_GENERATION_ENABLED","RUNWAY_API_KEY","ELEVENLABS_API_KEY","DOCKER_HOST","DOCKER_CONTEXT"}) info.EnvironmentVariables.Remove(key);
        using(var process = Process.Start(info)) {
            var output = process.StandardOutput.ReadToEndAsync();
            var error = process.StandardError.ReadToEndAsync();
            if(!process.WaitForExit(seconds*1000)) { process.Kill(); throw new Exception("Command timed out: " + Path.GetFileName(file)); }
            Task.WaitAll(output,error);
            if(process.ExitCode != 0) throw new Exception(Path.GetFileName(file)+" failed: "+error.Result.Trim()+" "+output.Result.Trim());
            return output.Result.Trim();
        }
    }
    static string Docker(params string[] args) {
        return Run(docker,wsl ? WslArgs(new[]{"docker"}.Concat(args).ToArray()) : args,1800);
    }
    static string[] WslArgs(params string[] args) {
        return (distribution==null ? new[]{"--exec"} : new[]{"--distribution",distribution,"--exec"}).Concat(args).ToArray();
    }
    static string DockerPath(string path) {
        return wsl ? Run(docker,WslArgs("wslpath","-u",path),20) : path;
    }
    public static void DetectDocker() {
        Directory.CreateDirectory(Root);
        var candidates = new[]{
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),"Docker","Docker","resources","bin","docker.exe"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","DockerDesktop","resources","bin","docker.exe"),
            "docker.exe"
        };
        foreach(string candidate in candidates) {
            try { if(Run(candidate,new[]{"info","--format","{{.OSType}}"},30)=="linux") { docker=candidate; wsl=false; Docker("compose","version"); Log("Using Docker Desktop / Windows Docker CLI."); return; } } catch { }
        }
        try {
            docker=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System),"wsl.exe"); wsl=true;
            string running=Run(docker,new[]{"--list","--running","--quiet"},30,Encoding.Unicode);
            foreach(string name in running.Split(new[]{'\r','\n'},StringSplitOptions.RemoveEmptyEntries)) {
                distribution=name.Trim('\ufeff',' ','\0');
                if(distribution.Length==0) continue;
                try {
                    if(Run(docker,WslArgs("docker","info","--format","{{.OSType}}"),30)=="linux") {
                        Docker("compose","version"); Log("Using Docker in running WSL distribution: "+distribution); return;
                    }
                } catch { }
            }
        } catch(Exception error) { Log("WSL runtime check: " + error.Message); }
        throw new Exception("Start Docker Desktop with Linux containers, or start your WSL distribution with a working Docker engine and Compose v2, then retry. This EXE includes the app images but does not install Docker or WSL.");
    }
    public static void PrepareEnvironment() {
        if(project==null) {
            using(var hash=SHA256.Create()) project="scriptstudio-desktop-"+Hex(hash.ComputeHash(Encoding.UTF8.GetBytes(Environment.UserDomainName+"\\"+Environment.UserName))).Substring(0,10);
        }
        if(envFile==null) envFile=Path.Combine(Root,"desktop.env");
        if(File.Exists(envFile)) {
            string line=File.ReadAllLines(envFile).First(x=>x.StartsWith("SCRIPTSTUDIO_PORT="));
            port=Int32.Parse(line.Split('=')[1]); return;
        }
        if(port==0) {
            for(int candidate=8088;candidate<8188;candidate++) {
                try { var listener=new TcpListener(IPAddress.Loopback,candidate); listener.Start(); listener.Stop(); port=candidate; break; } catch(SocketException) { }
            }
        }
        if(port==0) throw new Exception("No free localhost port in 8088–8187.");
        var password=new byte[32]; using(var random=RandomNumberGenerator.Create()) random.GetBytes(password);
        File.WriteAllText(envFile,"POSTGRES_PASSWORD="+Hex(password)+"\nSCRIPTSTUDIO_PORT="+port+"\n",new UTF8Encoding(false));
    }
    static string Compose(params string[] args) {
        return Docker(new[]{"compose","--project-directory",DockerPath(Package),"--env-file",DockerPath(envFile),"-f",DockerPath(Path.Combine(Package,"compose.json")),"-p",project}.Concat(args).ToArray());
    }
    public static string Url { get { return "http://127.0.0.1:"+port; } }
    public static void Start() {
        Log("Checking bundled images…");
        bool missing=false;
        foreach(string line in File.ReadAllLines(Path.Combine(Package,"images.txt"))) {
            var parts=line.Split(' ');
            try { if(Docker("image","inspect",parts[0],"--format","{{.Id}}")!=parts[1]) missing=true; } catch { missing=true; }
        }
        if(missing) { Log("Importing offline images. First launch may take several minutes…"); Docker("load","--input",DockerPath(Path.Combine(Package,"images.tar.gz"))); }
        Log("Starting ScriptStudio services…");
        Compose("up","-d","--no-build","--pull","never");
        Log("Waiting for database migration and HTTP health…");
        DateTime deadline=DateTime.UtcNow.AddMinutes(3);
        while(DateTime.UtcNow < deadline) {
            try {
                var request=(HttpWebRequest)WebRequest.Create(Url+"/api/health"); request.Proxy=null; request.Timeout=3000;
                using(var response=request.GetResponse()) using(var stream=new StreamReader(response.GetResponseStream())) {
                    if(stream.ReadToEnd().Contains("\"status\":\"ok\"")) { Log("Ready: "+Url); return; }
                }
            } catch { }
            Thread.Sleep(1500);
        }
        throw new Exception("Services started but the localhost health check did not become ready. Review Docker service status. Project data is retained.");
    }
    public static void Stop() { Compose("stop"); Log("Stopped. Projects, media, and settings are retained."); }
    public static void OpenBrowser() { Process.Start(new ProcessStartInfo(Url){UseShellExecute=true}); }

    class Launcher : Form {
        TextBox log=new TextBox();
        Button start=new Button(), stop=new Button(), open=new Button();
        bool busy;
        public Launcher() {
            Text="ScriptStudio"; ClientSize=new Size(720,450); MinimumSize=new Size(650,420);
            using(var icon=Assembly.GetExecutingAssembly().GetManifestResourceStream("ScriptStudio.ico")) Icon=new Icon(icon);
            BackColor=Color.FromArgb(16,20,25); ForeColor=Color.FromArgb(230,233,237);
            Font=new Font("Segoe UI",10);
            var title=new Label { Text="ScriptStudio · Offline application package", Dock=DockStyle.Top, Height=52, Padding=new Padding(18,15,0,0), Font=new Font("Segoe UI",15,FontStyle.Bold) };
            var note=new Label { Text="Requires a running Linux Docker engine (Docker Desktop or WSL).\nAll app images are bundled. No Python, Node, or source checkout is needed.",Dock=DockStyle.Top,Height=66,Padding=new Padding(18,4,18,0) };
            var buttons=new FlowLayoutPanel {Dock=DockStyle.Bottom,Height=58,Padding=new Padding(12)};
            start.Text="Start studio"; stop.Text="Stop services"; open.Text="Open studio";
            foreach(var button in new[]{start,stop,open}) {
                button.AutoSize=true; button.ForeColor=Color.FromArgb(32,48,26);
                button.BackColor=button==start ? Color.FromArgb(185,241,123) : Color.FromArgb(230,236,224);
                button.FlatStyle=FlatStyle.Flat; buttons.Controls.Add(button);
            }
            var files=new Button {Text="Package files",AutoSize=true,ForeColor=Color.FromArgb(32,48,26),BackColor=Color.FromArgb(230,236,224),FlatStyle=FlatStyle.Flat}; buttons.Controls.Add(files);
            log.Multiline=true; log.ReadOnly=true; log.ScrollBars=ScrollBars.Vertical; log.Dock=DockStyle.Fill; log.BackColor=Color.FromArgb(24,29,36); log.ForeColor=ForeColor; log.BorderStyle=BorderStyle.None;
            Controls.Add(log); Controls.Add(note); Controls.Add(title); Controls.Add(buttons);
            Log=delegate(string value) { if(!IsDisposed) BeginInvoke((Action)delegate {log.AppendText(value+Environment.NewLine+Environment.NewLine);}); };
            start.Click+=async delegate { await Work(delegate { Package=Extract(); DetectDocker(); PrepareEnvironment(); Start(); }); if(open.Enabled) OpenBrowser(); };
            stop.Click+=async delegate { await Work(delegate { Package=Extract(); DetectDocker(); PrepareEnvironment(); Stop(); }); open.Enabled=false; };
            open.Click+=delegate { OpenBrowser(); };
            files.Click+=delegate { Directory.CreateDirectory(Root); Process.Start(new ProcessStartInfo(Root){UseShellExecute=true}); };
            stop.Enabled=false; open.Enabled=false;
            FormClosing+=delegate(object sender,FormClosingEventArgs e) { if(busy) {e.Cancel=true; MessageBox.Show("Wait for the current operation to finish.");} };
            Shown+=delegate { Log("Click Start studio. Closing this launcher leaves services running; Stop services retains your data."); };
        }
        async Task Work(Action action) {
            busy=true; start.Enabled=stop.Enabled=open.Enabled=false;
            try { await Task.Run(action); stop.Enabled=true; open.Enabled=true; }
            catch(Exception error) { Log(error.Message); }
            finally { busy=false; start.Enabled=true; stop.Enabled=Package!=null && project!=null && docker!=null; }
        }
    }
}
