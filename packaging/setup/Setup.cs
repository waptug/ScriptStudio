using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Net;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Runtime.InteropServices;
using Microsoft.Win32;
using System.Web.Script.Serialization;

static class SetupProgram {
 public const long GiB=1073741824L;
 public static JavaScriptSerializer Json=new JavaScriptSerializer {MaxJsonLength=64*1024*1024};
 public static Dictionary<string,object> Manifest;
 public static CancellationTokenSource Cancel=new CancellationTokenSource();
 public static string Exe {get{return Assembly.GetExecutingAssembly().Location;}}
 public static string HashFile(string file){using(var s=File.OpenRead(file))using(var h=SHA256.Create())return Program.Hex(h.ComputeHash(s));}
 public static Dictionary<string,object> Read(string file){return Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(file));}
 public static void Save(string file,object data){Directory.CreateDirectory(Path.GetDirectoryName(file));string temp=file+".tmp";using(var f=new FileStream(temp,FileMode.Create,FileAccess.Write,FileShare.None)){byte[] b=Encoding.UTF8.GetBytes(Json.Serialize(data));f.Write(b,0,b.Length);f.Flush(true);}if(File.Exists(file))File.Replace(temp,file,null);else File.Move(temp,file);}
 public static string DefaultApp {get{return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","ScriptStudio");}}
 public static string DefaultStorage {get{return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"ScriptStudio");}}
 [STAThread] public static int Main(string[] args){
  Application.EnableVisualStyles();
  using(var resource=Assembly.GetExecutingAssembly().GetManifestResourceStream("setup-manifest.json"))using(var r=new StreamReader(resource))Manifest=Json.Deserialize<Dictionary<string,object>>(r.ReadToEnd());
  bool owned;using(var guard=new Mutex(true,"Local\\ScriptStudio.Setup",out owned)){
   if(!owned){MessageBox.Show("Another ScriptStudio installer is running.");return 2;}
   try {
    if(args.Length==2&&args[0]=="--export-source") {using(var source=Assembly.GetExecutingAssembly().GetManifestResourceStream("setup-source.zip"))using(var target=File.Create(Path.GetFullPath(args[1])))source.CopyTo(target);return 0;}
    if(args.Length==2&&args[0]=="--inventory"){var report=Plan(Inventory(),DefaultApp,DefaultStorage,new string[0]);Save(Path.GetFullPath(args[1]),report);return 0;}
    if(args.Length==1&&args[0]=="--uninstall"){Uninstall();return 0;}
    if(args.Length>0)throw new Exception("Use the setup wizard, --inventory <report.json>, or --uninstall.");
    Application.Run(new SetupWizard());return 0;
   }catch(Exception e){MessageBox.Show(e.Message,"ScriptStudio Setup");return 1;}
  }
 }
 [StructLayout(LayoutKind.Sequential)] class Memory {public uint length=(uint)Marshal.SizeOf(typeof(Memory));public uint load;public ulong total,available,pageTotal,pageAvailable,virtualTotal,virtualAvailable,extended;}
 [DllImport("kernel32.dll")] static extern bool GlobalMemoryStatusEx([In,Out] Memory m);
 [DllImport("kernel32.dll")] static extern bool GetPhysicallyInstalledSystemMemory(out ulong kilobytes);
 [DllImport("kernel32.dll")] static extern bool IsProcessorFeaturePresent(uint feature);
 [StructLayout(LayoutKind.Sequential)] struct NativeSystem {public ushort architecture,reserved;public uint pageSize;public IntPtr minimum,maximum,mask;public uint processors,type,granularity;public ushort level,revision;}
 [DllImport("kernel32.dll")] static extern void GetNativeSystemInfo(out NativeSystem info);
 public static string Query(string exe,string arguments,int seconds=8){
  var info=new ProcessStartInfo(exe,arguments){UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true};
  using(var p=Process.Start(info)){
   var output=p.StandardOutput.ReadToEndAsync();var error=p.StandardError.ReadToEndAsync();
   if(!p.WaitForExit(seconds*1000)){try{p.Kill();}catch{}throw new IOException("Detection timed out");}
   if(p.ExitCode!=0)throw new IOException("Query failed");return output.Result.Trim();
  }
 }
 public static Dictionary<string,object> Inventory(){
  var result=new Dictionary<string,object>{{"contract_version",1},{"observed_utc",DateTime.UtcNow.ToString("o")},{"architecture",Environment.GetEnvironmentVariable("PROCESSOR_ARCHITECTURE")??"Unknown"},{"logical_cores",Environment.ProcessorCount},{"sse2",IsProcessorFeaturePresent(10)},{"permission_check","Unknown: destination write test occurs after acceptance"},{"cuda_compatibility","Unknown: selected runtime probe required"}};
  NativeSystem system;GetNativeSystemInfo(out system);result["architecture"]=system.architecture==9?"AMD64":system.architecture==12?"ARM64":"Unknown";
  result["avx_support"]="Unknown: selected CPU runtime probe required";result["graphics_shared_bytes"]="Unknown";
  try{using(var key=Registry.LocalMachine.OpenSubKey(@"SOFTWARE\Microsoft\Windows NT\CurrentVersion")){result["windows_build"]=int.Parse((string)key.GetValue("CurrentBuildNumber"));result["windows_version"]=key.GetValue("DisplayVersion","Unknown");result["installation_type"]=key.GetValue("InstallationType","Unknown");}}catch{result["windows_build"]=null;result["installation_type"]="Unknown";}
  try{using(var key=Registry.LocalMachine.OpenSubKey(@"HARDWARE\DESCRIPTION\System\CentralProcessor\0"))result["cpu_name"]=key.GetValue("ProcessorNameString","Unknown");}catch{result["cpu_name"]="Unknown";}
  var memory=new Memory();if(GlobalMemoryStatusEx(memory)){result["ram_total_bytes"]=memory.total;result["ram_available_bytes"]=memory.available;}else{result["ram_total_bytes"]=null;result["ram_available_bytes"]=null;}
  result["ram_usable_bytes"]=result["ram_total_bytes"];ulong installed;if(GetPhysicallyInstalledSystemMemory(out installed))result["ram_total_bytes"]=checked(installed*1024UL);
  string browser=new[]{Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),@"Microsoft\Edge\Application\msedge.exe"),Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),@"Microsoft\Edge\Application\msedge.exe"),Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),@"Google\Chrome\Application\chrome.exe"),Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),@"Google\Chrome\Application\chrome.exe")}.FirstOrDefault(File.Exists);
  result["browser"]=browser??"Unknown";
  try{result["graphics_adapters"]=Query("powershell.exe","-NoProfile -NonInteractive -Command \"Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,AdapterRAM | ConvertTo-Json -Compress\"");}catch{result["graphics_adapters"]="Unknown";}
  try{string smi=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows),"System32","nvidia-smi.exe");result["nvidia"]=Query(smi,"--query-gpu=name,memory.total,memory.free,driver_version,compute_cap --format=csv,noheader,nounits");}catch{result["nvidia"]="Unknown";}
  try{using(var c=new WebClient()){c.Proxy=null;var task=c.DownloadStringTaskAsync("http://127.0.0.1:11434/api/version");if(!task.Wait(2000))throw new IOException();result["ollama"]=task.Result;}}catch{result["ollama"]="Unknown";}
  return result;
 }
 public static string Reason(Dictionary<string,object> inv,string feature){
  if(inv["windows_build"]==null)return "Unknown: Windows version detection failed.";
  if(Convert.ToInt32(inv["windows_build"])<22000)return "Windows 11 build 22000 or later is required.";
  if(!inv.ContainsKey("installation_type")||(string)inv["installation_type"]=="Unknown")return "Unknown: Windows client edition could not be detected.";
  if((string)inv["installation_type"]!="Client")return "Windows 11 client edition is required; Windows Server is unsupported.";
  if((string)inv["architecture"]!="AMD64")return "Windows x64 (AMD64) is required; detected architecture: "+inv["architecture"]+".";
  if(Convert.ToInt32(inv["logical_cores"])<4)return "At least 4 logical CPU cores are required.";
  long ram=inv["ram_total_bytes"]==null?0:Convert.ToInt64(inv["ram_total_bytes"]);
  if(inv["ram_total_bytes"]==null)return "Unknown: installed RAM could not be detected.";
  if(ram<8*GiB)return "At least 8 GiB RAM is required.";
  if((string)inv["browser"]=="Unknown")return "Install Microsoft Edge or Google Chrome and rescan.";
  if(feature=="core")return null;
  if(!(bool)inv["sse2"])return "Compatible CPU instruction support is unavailable.";
  if(feature=="gemma"||feature=="ollama")return ram<16*GiB?"Writing/planning requires 16 GiB RAM.":null;
  if(feature!="kokoro"){
   if(ram<32*GiB)return "CUDA media requires 32 GiB RAM.";
   if((string)inv["nvidia"]=="Unknown")return "NVIDIA VRAM, driver and GPU architecture are Unknown. Install an official driver and rescan.";
   bool eligible=false;foreach(var line in ((string)inv["nvidia"]).Split('\n')){var columns=line.Split(',');long mib;double cap;if(columns.Length>=5&&long.TryParse(columns[1].Trim(),out mib)&&double.TryParse(columns[4].Trim(),System.Globalization.NumberStyles.Any,System.Globalization.CultureInfo.InvariantCulture,out cap)&&mib>=12288&&cap>=7.0)eligible=true;}
   if(!eligible)return "Requires 12 GiB dedicated NVIDIA VRAM and supported GPU architecture. Runtime verification still required.";
  }
  if(feature=="stable_audio")return "Separate upstream terms acceptance and authorized token are required. Complete access in Admin after core installation.";
  return null;
 }
 public static string LocalPath(string value){string path=Path.GetFullPath(value.Trim());if(path.StartsWith(@"\\")||path.Length<4||!Path.IsPathRooted(path))throw new IOException("Choose a local folder below a drive root.");var drive=new DriveInfo(Path.GetPathRoot(path));if(drive.DriveType!=DriveType.Fixed)throw new IOException("Choose a fixed local drive.");string cursor=path;while(!Directory.Exists(cursor))cursor=Path.GetDirectoryName(cursor);while(cursor!=null){if((File.GetAttributes(cursor)&FileAttributes.ReparsePoint)!=0)throw new IOException("Installation destinations must not traverse links or junctions.");cursor=Path.GetDirectoryName(cursor);}return path;}
 public static object[] Items(object value){return ((IEnumerable)value).Cast<object>().ToArray();}
 public static object[] Features {get{return Items(Manifest["features"]);}}
 public static bool VerifiedFile(string file,long size,string expected,string storage,Stopwatch budget){
  try{if(budget.ElapsedMilliseconds>=10000||!File.Exists(file)||new FileInfo(file).Length!=size)return false;
   string cursor=file;while(cursor!=storage){if((File.GetAttributes(cursor)&FileAttributes.ReparsePoint)!=0)return false;cursor=Path.GetDirectoryName(cursor);if(cursor==null)return false;}
   using(var source=File.OpenRead(file))using(var hash=SHA256.Create()){byte[] bytes=new byte[1024*1024];int count;while((count=source.Read(bytes,0,bytes.Length))>0){if(budget.ElapsedMilliseconds>=10000)return false;hash.TransformBlock(bytes,0,count,bytes,0);}hash.TransformFinalBlock(new byte[0],0,0);return Program.Hex(hash.Hash)==expected;}
  }catch(IOException){return false;}catch(UnauthorizedAccessException){return false;}
 }
 public static Dictionary<string,object> Plan(Dictionary<string,object> inv,string app,string storage,string[] selected){
  app=LocalPath(app);storage=LocalPath(storage);
  if(selected.Contains("gemma")&&!selected.Contains("ollama"))selected=selected.Concat(new[]{"ollama"}).ToArray();
  if(app.Equals(storage,StringComparison.OrdinalIgnoreCase)||app.StartsWith(storage+"\\",StringComparison.OrdinalIgnoreCase)||storage.StartsWith(app+"\\",StringComparison.OrdinalIgnoreCase))throw new IOException("Application and storage folders must be separate.");
  long download=0,expanded=0;var components=new List<object>();var budget=Stopwatch.StartNew();var seen=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
  foreach(Dictionary<string,object> feature in Features){string id=(string)feature["id"];string reason=Reason(inv,id);bool chosen=selected.Contains(id);long reused=0;long remaining=Convert.ToInt64(feature["download_bytes"]);if(chosen&&feature.ContainsKey("artifacts")){remaining=0;foreach(Dictionary<string,object> artifact in Items(feature["artifacts"])){string basePath=id=="gemma"?Path.Combine(storage,"local-llm","models"):id=="ollama"?Path.Combine(storage,"local-llm"):Path.Combine(storage,"local-models",id);string target=Path.GetFullPath(Path.Combine(basePath,(string)artifact["path"]));if(!target.StartsWith(basePath+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new IOException("Unsafe artifact path");if(!seen.Add(target))continue;long size=Convert.ToInt64(artifact["size"]);if(VerifiedFile(target,size,(string)artifact["sha256"],storage,budget))reused+=size;else remaining+=size;}}if(chosen&&reason!=null)throw new IOException(id+": "+reason);components.Add(new {id=id,status=reason!=null?(reason.Contains("Unknown")?"Unknown":"Blocked"):"Needs installation",reason=reason??"Screening passed; runtime verification required",selected=id=="core"||chosen,source=feature["source"],license=feature["license"],revision=feature["revision"],artifacts=feature.ContainsKey("artifacts")?feature["artifacts"]:new object[0],download_bytes=feature["download_bytes"],expanded_bytes=feature["expanded_bytes"],remaining_download_bytes=remaining,reused_download_bytes=reused,reuse=reused>0?"Pinned existing downloads verified by SHA-256; runtime reuse requires its probe":"No reuse credit: existing files absent, unverified or scan budget exceeded"});if(chosen){download+=remaining;expanded+=Convert.ToInt64(feature["expanded_bytes"]);}}
  long launcher=Convert.ToInt64(Manifest["launcher_bytes"]),core=Convert.ToInt64(Manifest["core_expanded_bytes"]);
  long backup=0;string db=Path.Combine(storage,"data","database");if(Directory.Exists(db))backup=Directory.EnumerateFiles(db,"*",SearchOption.AllDirectories).Sum(f=>new FileInfo(f).Length);
  long appPeak=launcher*2+32*1024*1024,storagePeak=core*2+download+expanded+10*GiB+backup;
  string av=Path.GetPathRoot(app),sv=Path.GetPathRoot(storage);long appFree=new DriveInfo(av).AvailableFreeSpace,storageFree=new DriveInfo(sv).AvailableFreeSpace;
  bool same=av.Equals(sv,StringComparison.OrdinalIgnoreCase);bool enough=same?appFree>=appPeak+storagePeak:appFree>=appPeak&&storageFree>=storagePeak;
  return new Dictionary<string,object>{{"contract_version",1},{"inventory",inv},{"components",components},{"application",app},{"storage",storage},{"selected",selected},{"manifest_sha256",Manifest["manifest_sha256"]},{"remaining_download_bytes",download},{"final_storage_bytes",launcher+core+download+expanded},{"peak_installation_bytes",appPeak+storagePeak},{"project_reserve_bytes",10*GiB},{"database_backup_bytes",backup},{"app_free_bytes",appFree},{"storage_free_bytes",storageFree},{"same_volume",same},{"storage_sufficient",enough},{"core_reason",Reason(inv,"core")},{"manual_actions","Unsigned EXE: inspect publisher/source using Windows security prompts. Never disable security controls. GPU drivers: https://www.nvidia.com/Download/index.aspx. Stable Audio access: Admin after installation."}};
 }
 public static string Fingerprint(object plan){using(var h=SHA256.Create())return Program.Hex(h.ComputeHash(Encoding.UTF8.GetBytes(Json.Serialize(plan))));}
 public static string Pretty(object value){string raw=Json.Serialize(value);var text=new StringBuilder();int depth=0;bool quoted=false,escaped=false;foreach(char c in raw){if(quoted){text.Append(c);if(escaped)escaped=false;else if(c=='\\')escaped=true;else if(c=='"')quoted=false;continue;}if(c=='"'){quoted=true;text.Append(c);}else if(c=='{'||c=='['){text.Append(c);text.AppendLine();depth++;text.Append(' ',depth*2);}else if(c=='}'||c==']'){text.AppendLine();depth--;text.Append(' ',depth*2);text.Append(c);}else if(c==','){text.Append(c);text.AppendLine();text.Append(' ',depth*2);}else if(c==':')text.Append(": ");else text.Append(c);}return text.ToString();}
 public static string Html(object report){return "<!doctype html><meta charset='utf-8'><title>ScriptStudio setup accounting</title><style>body{font:15px system-ui;margin:3em}pre{white-space:pre-wrap;overflow-wrap:anywhere}@media print{button{display:none}}</style><h1>ScriptStudio setup accounting</h1><button onclick='print()'>Print</button><pre>"+WebUtility.HtmlEncode(Pretty(report))+"</pre>";}
 public static void Install(Dictionary<string,object> plan,Action<string> log){
  if(plan["core_reason"]!=null||!(bool)plan["storage_sufficient"])throw new IOException("Core requirements or storage screening failed. Rescan and review.");
  string app=(string)plan["application"],storage=(string)plan["storage"];
  var fresh=Plan((Dictionary<string,object>)plan["inventory"],app,storage,(string[])plan["selected"]);
  if(Convert.ToInt64(fresh["remaining_download_bytes"])!=Convert.ToInt64(plan["remaining_download_bytes"]))throw new IOException("Verified download actions changed after review; rescan and accept the updated report.");
  if(!(bool)fresh["storage_sufficient"])throw new IOException("Storage changed after review; rescan and review the accounting report.");
  LocalPath(app);LocalPath(storage);Directory.CreateDirectory(app);Directory.CreateDirectory(storage);
  // Cross-process lock is held through runtime verification and backup.
  using(var guard=new FileStream(Path.Combine(storage,"setup.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None)){
   string journal=Path.Combine(storage,"setup-journal.json");
   Save(Path.Combine(storage,"setup-acceptance.json"),new {contract_version=1,accepted_utc=DateTime.UtcNow.ToString("o"),plan_sha256=Fingerprint(plan),plan=plan});
   Action<string> phase=s=>{Save(journal,new {contract_version=1,phase=s,plan_sha256=Fingerprint(plan),updated_utc=DateTime.UtcNow.ToString("o")});log(s);Cancel.Token.ThrowIfCancellationRequested();};
   try{
    phase("Verifying embedded payload");
    string staging=Path.Combine(app,"staging-"+Guid.NewGuid().ToString("N"));
    try{Extract(staging);Cancel.Token.ThrowIfCancellationRequested();string exe=Path.Combine(staging,"ScriptStudio.exe");if(HashFile(exe)!=(string)Manifest["launcher_sha256"])throw new IOException("Embedded launcher checksum failed");Save(Path.Combine(staging,"installation.json"),new {contract_version=1,storage=storage});
     string releases=Path.Combine(app,"versions");Directory.CreateDirectory(releases);string destination=Path.Combine(releases,((string)Manifest["launcher_sha256"]).Substring(0,16)+"-"+Fingerprint(storage).Substring(0,8));
     if(Directory.Exists(destination)){if(HashFile(Path.Combine(destination,"ScriptStudio.exe"))!=(string)Manifest["launcher_sha256"]){Directory.Move(destination,destination+".repair-"+Guid.NewGuid().ToString("N"));Directory.Move(staging,destination);}else Directory.Delete(staging,true);}else Directory.Move(staging,destination);
     phase("Preparing preserved workspace");
     string data=Path.Combine(storage,"data");Directory.CreateDirectory(data);
     using(var runtimeLock=new FileStream(Path.Combine(data,"runtime.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None)){
      string db=Path.Combine(data,"database");if(Directory.Exists(db)){
       if(File.Exists(Path.Combine(db,"postmaster.pid")))throw new IOException("Database may be active. Stop the existing studio before upgrading.");
       if(File.ReadAllText(Path.Combine(db,"PG_VERSION")).Trim()!="17")throw new IOException("Existing PostgreSQL major version is incompatible. Database directories are never merged.");
       phase("Backing up database before migrations");string backup=Path.Combine(storage,"backups",DateTime.UtcNow.ToString("yyyyMMddHHmmss")+"-"+Guid.NewGuid().ToString("N"));CopyTree(db,backup);if(File.Exists(Path.Combine(data,"runtime.json")))File.Copy(Path.Combine(data,"runtime.json"),backup+".runtime.json");
      }
     string hostConfig=Path.Combine(data,"resource-optimization.json");
     if(File.Exists(hostConfig))File.Copy(hostConfig,hostConfig+".before-setup-"+Guid.NewGuid().ToString("N"));
     Save(hostConfig,new {enabled=false,containers=new string[0],high_performance=false,above_normal_priority=false});
     }
     Program.Root=storage;Program.Data=data;
     // Installed launcher contains the native payload and performs its own bounded extraction.
     phase("Extracting and verifying core application");Run(Path.Combine(destination,"ScriptStudio.exe"),"--verify",600);
     var verification=new List<object>();
     if(((string[])plan["selected"]).Contains("ollama")){
      phase("Installing accepted Ollama components");File.Delete(Path.Combine(storage,"setup.cancel"));
      string package=Directory.GetDirectories(Path.Combine(storage,"packages")).First(p=>File.Exists(Path.Combine(p,"setup_components.py"))&&File.ReadAllText(Path.Combine(p,"package.sha256"))==(string)Manifest["native_payload_sha256"]);
      try{InstallLlm(package,storage,((string[])plan["selected"]).Contains("gemma"),log);}catch(OperationCanceledException){throw;}catch(Exception e){verification.Add(new {feature="ollama",status="failed",reason=e.Message});log("Optional Ollama installation failed; core remains available. "+e.Message);}
     }
     phase("Starting database and API for verification");
     try{
      StartInstalled(destination,data);
      var health=Api("GET","/api/health",null);verification.Add(new {feature="core",status="verified_database_api",detail=health});
      if(((string[])plan["selected"]).Contains("ollama")){
       try{string llmUrl=Convert.ToString(Read(Path.Combine(data,"ready.json"))["ollama_url"]);if(string.IsNullOrEmpty(llmUrl))throw new IOException("Optional Ollama service unavailable");VerifyLlm(llmUrl,((string[])plan["selected"]).Contains("gemma"));Api("PUT","/api/admin/settings",Json.Serialize(new {values=new {OLLAMA_URL=llmUrl,OLLAMA_MODEL=((string[])plan["selected"]).Contains("gemma")?"gemma3:4b":"",SCRIPT_WRITER_MODEL=((string[])plan["selected"]).Contains("gemma")?"gemma3:4b":""}}));verification.Add(new {feature="ollama_gemma",status="verified",detail="Service and selected short generation check passed"});}
       catch(Exception e){verification.Add(new {feature="ollama_gemma",status="failed",reason=e.Message});Api("PUT","/api/admin/settings","{\"values\":{\"OLLAMA_URL\":\"\",\"OLLAMA_MODEL\":\"\",\"SCRIPT_WRITER_MODEL\":\"\"}}");log("Optional writing/planning disabled: "+e.Message);}
      }
      foreach(string model in (string[])plan["selected"]){
       if(model=="ollama"||model=="gemma")continue;
       phase("Installing and probing "+model);
       try{bool generationRequested=false;Api("POST","/api/admin/local-models/"+model+"/resume","{\"accept_license\":false}");while(true){Cancel.Token.ThrowIfCancellationRequested();var catalog=Json.Deserialize<Dictionary<string,object>>(Api("GET","/api/admin/local-models",null));var item=Items(catalog["models"]).Cast<Dictionary<string,object>>().First(m=>(string)m["id"]==model);string state=(string)item["state"];log(model+": "+state+" "+(item.ContainsKey("detail")?item["detail"]:""));if(state=="ready"){if(model!="wan"&&!generationRequested){generationRequested=true;Api("POST","/api/admin/local-models/"+model+"/test","{}");continue;}verification.Add(new {feature=model,status="runtime_verified",generation_test=generationRequested?"verified":"optional_long_test_not_run"});break;}if(state=="failed"||state=="interrupted")throw new IOException(item.ContainsKey("error")?Convert.ToString(item["error"]):state);Thread.Sleep(1500);}}
       catch(OperationCanceledException){Api("POST","/api/admin/local-models/"+model+"/cancel","{}");throw;}
       catch(Exception e){verification.Add(new {feature=model,status="failed",reason=e.Message});log(model+" remains disabled: "+e.Message);}
      }
      StopInstalled(data);
      phase("Verifying narration, preview, final MP4, subtitles and OpenShot in an isolated workspace");
      string checkData=Path.Combine(storage,"setup-verification");Directory.CreateDirectory(checkData);
      try{StartInstalled(destination,checkData,true);SmokeCore(log);verification.Add(new {feature="render_narration_subtitles_openshot",status="verified",workspace=checkData});}
      finally{StopInstalled(checkData);}
      verification.Add(new {feature="browser",status="available",reason="Browser executable detected; interactive launch occurs when you click Launch."});
      Save(Path.Combine(storage,"setup-verification.json"),new {contract_version=1,results=verification});
     }finally{StopInstalled(data);}
     phase("Creating shortcuts and uninstaller");
     File.Copy(Exe,Path.Combine(app,"Uninstall.exe"),true);
     Shortcut(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs),"ScriptStudio.lnk"),Path.Combine(destination,"ScriptStudio.exe"),"--start");
     using(var key=Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Windows\CurrentVersion\Uninstall\ScriptStudio")){key.SetValue("DisplayName","ScriptStudio");key.SetValue("InstallLocation",app);key.SetValue("UninstallString",Program.Quote(Path.Combine(app,"Uninstall.exe"))+" --uninstall");key.SetValue("NoModify",1);key.SetValue("NoRepair",1);}
     Save(Path.Combine(app,"active.json"),new {contract_version=1,directory=destination,storage=storage});
     Save(journal,new {contract_version=1,phase="complete",directory=destination,updated_utc=DateTime.UtcNow.ToString("o")});log("Installation complete. Verification report: "+Path.Combine(storage,"setup-verification.json"));
    }finally{if(Directory.Exists(staging))Directory.Delete(staging,true);}
   }catch(Exception e){Save(journal,new {contract_version=1,phase=e is OperationCanceledException?"canceled":"interrupted",reason=e.Message,updated_utc=DateTime.UtcNow.ToString("o")});throw;}
  }
 }
 public static void CopyTree(string from,string to){Directory.CreateDirectory(to);foreach(string file in Directory.GetFiles(from)){Cancel.Token.ThrowIfCancellationRequested();if((File.GetAttributes(file)&FileAttributes.ReparsePoint)!=0)throw new IOException("Backup refuses filesystem links");File.Copy(file,Path.Combine(to,Path.GetFileName(file)));}foreach(string dir in Directory.GetDirectories(from)){if((File.GetAttributes(dir)&FileAttributes.ReparsePoint)!=0)throw new IOException("Backup refuses filesystem links");CopyTree(dir,Path.Combine(to,Path.GetFileName(dir)));}}
 public static void Extract(string destination){
  using(var input=File.OpenRead(Exe)){
   if(input.Length<48)throw new IOException("Missing payload");input.Position=input.Length-48;var reader=new BinaryReader(input);if(Encoding.ASCII.GetString(reader.ReadBytes(8))!="SSTSET01")throw new IOException("Invalid setup footer");long length=reader.ReadInt64();byte[] expected=reader.ReadBytes(32);if(length<=0||length>input.Length-48)throw new IOException("Invalid payload size");
   using(var payload=new PayloadStream(input,input.Length-48-length,length)){
    using(var hash=SHA256.Create())if(!hash.ComputeHash(payload).SequenceEqual(expected))throw new IOException("Setup payload checksum failed");payload.Position=0;
    using(var zip=new ZipArchive(payload,ZipArchiveMode.Read,true)){
     if(zip.Entries.Count!=1||zip.Entries[0].FullName!="ScriptStudio.exe"||zip.Entries[0].Length!=Convert.ToInt64(Manifest["launcher_bytes"]))throw new IOException("Unexpected setup inventory");
     Cancel.Token.ThrowIfCancellationRequested();Directory.CreateDirectory(destination);using(var source=zip.Entries[0].Open())using(var target=File.Create(Path.Combine(destination,"ScriptStudio.exe"))){var b=new byte[1024*1024];int n;while((n=source.Read(b,0,b.Length))>0){Cancel.Token.ThrowIfCancellationRequested();target.Write(b,0,n);}}
    }
   }
  }
 }
 public static void Run(string exe,string args,int seconds){using(var p=Process.Start(new ProcessStartInfo(exe,args){UseShellExecute=false,CreateNoWindow=true})){if(!p.WaitForExit(seconds*1000)){p.Kill();throw new IOException("Runtime verification timed out");}if(p.ExitCode!=0)throw new IOException("Runtime verification failed: "+p.ExitCode);}}
 static void InstallLlm(string package,string storage,bool gemma,Action<string> log){
  var info=new ProcessStartInfo(Path.Combine(package,"python","python.exe"),"-X utf8 "+Program.Quote(Path.Combine(package,"setup_components.py"))+" --storage "+Program.Quote(storage)+(gemma?" --gemma":"")){UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true};Program.ConfigureEnvironment(info);
  using(var job=new NativeJob())using(var p=Process.Start(info)){job.Add(p);p.OutputDataReceived+=(s,e)=>{if(e.Data!=null)log(e.Data);};p.BeginOutputReadLine();var error=p.StandardError.ReadToEndAsync();while(!p.WaitForExit(500)){if(Cancel.IsCancellationRequested)File.WriteAllText(Path.Combine(storage,"setup.cancel"),"cancel");}Cancel.Token.ThrowIfCancellationRequested();if(p.ExitCode!=0)throw new IOException("Ollama component installation failed; partial downloads preserved. "+error.Result);}
 }
 static Process installed;static NativeJob installedJob;static string url;
 static void StartInstalled(string destination,string data,bool check=false){
  File.Delete(Path.Combine(data,"ready.json"));
  installedJob=new NativeJob();var info=new ProcessStartInfo(Path.Combine(destination,"ScriptStudio.exe"),"--setup-serve"+(check?" --check":"")){UseShellExecute=false,CreateNoWindow=true};info.EnvironmentVariables["SCRIPTSTUDIO_SETUP_DISABLE_PAID"]="1";installed=Process.Start(info);installedJob.Add(installed);
  DateTime deadline=DateTime.UtcNow.AddMinutes(5);while(DateTime.UtcNow<deadline){Cancel.Token.ThrowIfCancellationRequested();if(installed.HasExited)throw new IOException("Core startup failed; inspect launcher.log and runtime.log");string endpoint;if(Program.TryReadReady(Path.Combine(data,"ready.json"),out endpoint)&&Program.Healthy(endpoint)){url=endpoint;return;}Thread.Sleep(250);}throw new IOException("Core startup timeout");
 }
 static void StopInstalled(string data){if(installed!=null&&!installed.HasExited){File.WriteAllText(Path.Combine(data,"stop.request"),"stop");if(!installed.WaitForExit(120000))installed.Kill();}if(installedJob!=null)installedJob.Dispose();}
 static string Api(string method,string route,string body){var request=(HttpWebRequest)WebRequest.Create(url+route);request.Proxy=null;request.Method=method;request.Timeout=15000;request.ContentType="application/json";if(body!=null){byte[] b=Encoding.UTF8.GetBytes(body);request.ContentLength=b.Length;using(var s=request.GetRequestStream())s.Write(b,0,b.Length);}using(var response=request.GetResponse())using(var r=new StreamReader(response.GetResponseStream()))return r.ReadToEnd();}
 static void VerifyLlm(string llmUrl,bool gemma){
  if(!llmUrl.StartsWith("http://127.0.0.1:",StringComparison.Ordinal))throw new IOException("Expected loopback Ollama endpoint");
  Exception failure=null;for(int i=0;i<40;i++){Cancel.Token.ThrowIfCancellationRequested();try{using(var client=new WebClient()){client.Proxy=null;client.DownloadString(llmUrl+"/api/version");}failure=null;break;}catch(Exception e){failure=e;Thread.Sleep(500);}}if(failure!=null)throw new IOException("Ollama service startup failed");
  if(gemma){var request=(HttpWebRequest)WebRequest.Create(llmUrl+"/api/generate");request.Proxy=null;request.Method="POST";request.ContentType="application/json";request.Timeout=180000;byte[] body=Encoding.UTF8.GetBytes("{\"model\":\"gemma3:4b\",\"prompt\":\"Write one short sentence about a sunrise.\",\"stream\":false,\"keep_alive\":0,\"options\":{\"num_predict\":32}}");using(var s=request.GetRequestStream())s.Write(body,0,body.Length);using(var response=request.GetResponse())using(var r=new StreamReader(response.GetResponseStream())){var result=Json.Deserialize<Dictionary<string,object>>(r.ReadToEnd());if(!result.ContainsKey("response")||string.IsNullOrWhiteSpace(Convert.ToString(result["response"])))throw new IOException("Gemma generation check returned no text");}}
 }
 static Dictionary<string,object> Project(string id){return Json.Deserialize<Dictionary<string,object>>(Api("GET","/api/projects/"+id,null));}
 static Dictionary<string,object> WaitProject(string id,string jobId=null){
  DateTime end=DateTime.UtcNow.AddMinutes(10);while(DateTime.UtcNow<end){Cancel.Token.ThrowIfCancellationRequested();var project=Project(id);var jobs=Items(project["jobs"]).Cast<Dictionary<string,object>>().Where(j=>jobId==null||(string)j["id"]==jobId).ToArray();if(jobs.Any(j=>(string)j["state"]=="failed"||(string)j["state"]=="submission_outcome_unknown"))throw new IOException("Core media check failed: "+Json.Serialize(jobs));if(jobs.Length>0&&jobs.All(j=>(string)j["state"]=="ready"))return project;Thread.Sleep(500);}throw new IOException("Media verification timed out");
 }
 static byte[] Bytes(string route,bool range=false){var request=(HttpWebRequest)WebRequest.Create(url+route);request.Proxy=null;request.Timeout=30000;if(range)request.AddRange(0,63);using(var response=request.GetResponse())using(var stream=response.GetResponseStream())using(var memory=new MemoryStream()){stream.CopyTo(memory);return memory.ToArray();}}
 public static void SmokeCore(Action<string> log){
  var project=Json.Deserialize<Dictionary<string,object>>(Api("POST","/api/projects","{\"name\":\"ScriptStudio installation verification\",\"script\":\"[Sunrise over a meadow] Welcome to ScriptStudio. This local installation check verifies narration and video rendering.\",\"settings\":{\"width\":640,\"height\":360,\"target_duration\":10}}"));string id=(string)project["id"];
  Api("POST","/api/projects/"+id+"/plan?planner=local","{}");Api("POST","/api/projects/"+id+"/produce","{}");WaitProject(id);
  foreach(bool preview in new[]{true,false}){Cancel.Token.ThrowIfCancellationRequested();log(preview?"Rendering verification preview":"Rendering verification final MP4");var queued=Json.Deserialize<Dictionary<string,object>>(Api("POST","/api/projects/"+id+"/renders",Json.Serialize(new {preview=preview,draft=false,burn_captions=true})));string jid=(string)((Dictionary<string,object>)Items(queued["jobs"]).Last())["id"];project=WaitProject(id,jid);var job=Items(project["jobs"]).Cast<Dictionary<string,object>>().First(j=>(string)j["id"]==jid);byte[] media=Bytes("/api/assets/"+job["asset_id"]+"/original",true);if(!Encoding.ASCII.GetString(media).Contains("ftyp"))throw new IOException("Invalid MP4 verification output");if(Bytes("/api/jobs/"+jid+"/subtitles/srt").Length==0||Bytes("/api/jobs/"+jid+"/subtitles/vtt").Length==0)throw new IOException("Missing subtitles");if(!preview){byte[] bundle=Bytes("/api/jobs/"+jid+"/openshot");if(bundle.Length<2||bundle[0]!=80||bundle[1]!=75)throw new IOException("Invalid OpenShot export");}}
 }
 static void Shortcut(string file,string target,string args){Type type=Type.GetTypeFromProgID("WScript.Shell");dynamic shell=Activator.CreateInstance(type);dynamic link=shell.CreateShortcut(file);link.TargetPath=target;link.Arguments=args;link.WorkingDirectory=Path.GetDirectoryName(target);link.Save();Marshal.FinalReleaseComObject(link);Marshal.FinalReleaseComObject(shell);}
 static void Uninstall(){string app=Path.GetDirectoryName(Exe),active=Path.Combine(app,"active.json");if(!File.Exists(active))throw new IOException("Installation record missing; nothing removed.");var state=Read(active);string storage=(string)state["storage"];if(MessageBox.Show("Remove ScriptStudio application versions and shortcut? Projects, credentials, media, backups and models in "+storage+" will be preserved.","Uninstall",MessageBoxButtons.OKCancel)!=DialogResult.OK)return;using(var guard=new FileStream(Path.Combine(storage,"data","runtime.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None)){string versions=Path.Combine(app,"versions");if(Directory.Exists(versions))Directory.Delete(versions,true);File.Delete(active);File.Delete(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs),"ScriptStudio.lnk"));Registry.CurrentUser.DeleteSubKeyTree(@"Software\Microsoft\Windows\CurrentVersion\Uninstall\ScriptStudio",false);}MessageBox.Show("Application removed. Storage was preserved. You may delete this remaining uninstaller after closing it.");}
}

class SetupWizard : Form {
 TextBox app=new TextBox {Width=540,Text=SetupProgram.DefaultApp},storage=new TextBox {Width=540,Text=SetupProgram.DefaultStorage};
 TextBox report=new TextBox {Multiline=true,ReadOnly=true,ScrollBars=ScrollBars.Both,Dock=DockStyle.Fill,Font=new Font("Consolas",10)};
 CheckedListBox features=new CheckedListBox {Height=110,Width=680,CheckOnClick=true};
 CheckBox acceptance=new CheckBox {Text="I reviewed the accounting report and accept the selected installation actions and licenses.",AutoSize=true};
 Button scan=new Button {Text="Scan / Review",AutoSize=true},install=new Button {Text="Accept and install",AutoSize=true,Enabled=false},cancel=new Button {Text="Cancel",AutoSize=true,Enabled=false},launch=new Button {Text="Launch",AutoSize=true,Enabled=false};
 Dictionary<string,object> inventory,plan;string fingerprint;bool busy;
 public SetupWizard(){Text="ScriptStudio · Windows 11 Setup";var area=Screen.FromPoint(Cursor.Position).WorkingArea;Width=Math.Min(940,area.Width);Height=Math.Min(780,area.Height);MinimumSize=new Size(Math.Min(760,area.Width),Math.Min(620,area.Height));StartPosition=FormStartPosition.CenterScreen;Font=new Font("Segoe UI",10);
  acceptance.AutoSize=false;acceptance.Width=Math.Max(200,ClientSize.Width-40);acceptance.Height=48;
  var top=new FlowLayoutPanel {Dock=DockStyle.Top,Height=315,FlowDirection=FlowDirection.TopDown,WrapContents=false,Padding=new Padding(12)};
  top.Controls.Add(new Label {Text="Scan → Select features/location → Review accounting → Accept and install → Verify → Launch",AutoSize=true});
  top.Controls.Add(new Label {Text="Application location",AutoSize=true});top.Controls.Add(app);top.Controls.Add(new Label {Text="Writable project/model storage",AutoSize=true});top.Controls.Add(storage);top.Controls.Add(features);
  foreach(Dictionary<string,object> item in SetupProgram.Features)if((string)item["id"]!="core")features.Items.Add(item["id"]);
  var bottom=new FlowLayoutPanel {Dock=DockStyle.Bottom,Height=170,Padding=new Padding(12)};bottom.Controls.Add(acceptance);bottom.SetFlowBreak(acceptance,true);
  var json=new Button {Text="Save JSON",AutoSize=true};var html=new Button {Text="Save printable HTML",AutoSize=true};bottom.Controls.AddRange(new Control[]{scan,json,html,install,cancel,launch});Controls.Add(report);Controls.Add(top);Controls.Add(bottom);
  Action invalidate=()=>{acceptance.Checked=false;install.Enabled=false;plan=null;};app.TextChanged+=(s,e)=>invalidate();storage.TextChanged+=(s,e)=>invalidate();features.ItemCheck+=(s,e)=>invalidate();acceptance.CheckedChanged+=(s,e)=>install.Enabled=!busy&&acceptance.Checked&&plan!=null&&plan["core_reason"]==null&&(bool)plan["storage_sufficient"];
  scan.Click+=async(s,e)=>{busy=true;scan.Enabled=false;invalidate();try{inventory=await Task.Run(()=>SetupProgram.Inventory());plan=SetupProgram.Plan(inventory,app.Text,storage.Text,features.CheckedItems.Cast<string>().ToArray());fingerprint=SetupProgram.Fingerprint(plan);report.Text=SetupProgram.Pretty(plan);}catch(Exception ex){report.Text=ex.Message;}finally{busy=false;scan.Enabled=true;}};
  json.Click+=(s,e)=>Export(false);html.Click+=(s,e)=>Export(true);
  install.Click+=async(s,e)=>{if(plan==null||!acceptance.Checked||fingerprint!=SetupProgram.Fingerprint(plan))return;busy=true;install.Enabled=false;scan.Enabled=false;app.Enabled=storage.Enabled=features.Enabled=acceptance.Enabled=false;cancel.Enabled=true;SetupProgram.Cancel=new CancellationTokenSource();try{await Task.Run(()=>SetupProgram.Install(plan,Log));launch.Enabled=true;}catch(Exception ex){Log(ex.ToString());}finally{busy=false;cancel.Enabled=false;scan.Enabled=true;app.Enabled=storage.Enabled=features.Enabled=acceptance.Enabled=true;acceptance.Checked=false;plan=null;}};
  cancel.Click+=(s,e)=>{SetupProgram.Cancel.Cancel();Log("Cancellation requested; partial model downloads will be preserved.");};
  launch.Click+=(s,e)=>{var record=SetupProgram.Read(Path.Combine(app.Text,"active.json"));Process.Start(new ProcessStartInfo(Path.Combine((string)record["directory"],"ScriptStudio.exe"),"--start"){UseShellExecute=false});};
  FormClosing+=(s,e)=>{if(busy){e.Cancel=true;SetupProgram.Cancel.Cancel();Log("Waiting for cancellation and service shutdown before closing.");}};
  report.Text="Scan performs local inventory only. No application extraction, model downloads, database initialization or system changes occur until you check acceptance and click Accept and install. Optional downloads require internet. Unknown hardware is never treated as ready.";
 }
 void Log(string text){if(IsHandleCreated&&!IsDisposed)BeginInvoke((Action)(()=>report.AppendText(Environment.NewLine+text)));}
 void Export(bool html){if(plan==null)return;using(var dialog=new SaveFileDialog {Filter=html?"HTML|*.html":"JSON|*.json",FileName=html?"ScriptStudio-accounting.html":"ScriptStudio-accounting.json"})if(dialog.ShowDialog()==DialogResult.OK)File.WriteAllText(dialog.FileName,html?SetupProgram.Html(plan):SetupProgram.Json.Serialize(plan));}
}
