using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Windows.Forms;
static class SetupChecks {
 [STAThread] static int Main(){
  SetupProgram.Manifest=SetupProgram.Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(Environment.GetCommandLineArgs()[1]));
  var inventory=new Dictionary<string,object>{{"windows_build",22000},{"installation_type","Client"},{"architecture","AMD64"},{"logical_cores",4},{"ram_total_bytes",8*SetupProgram.GiB},{"browser","detected"},{"sse2",true},{"nvidia","Unknown"}};
  if(SetupProgram.Reason(inventory,"core")!=null||SetupProgram.Reason(inventory,"kokoro")!=null)throw new Exception("Core/CPU screening failed");
  if(SetupProgram.Reason(inventory,"gemma")==null||SetupProgram.Reason(inventory,"wan")==null)throw new Exception("Insufficient hardware accepted");
  inventory["ram_total_bytes"]=32*SetupProgram.GiB;
  if(SetupProgram.Reason(inventory,"wan")==null)throw new Exception("Unknown GPU accepted");
  inventory["nvidia"]="NVIDIA RTX, 12288, 9000, 560.0, 8.6";
  if(SetupProgram.Reason(inventory,"wan")!=null)throw new Exception("Eligible GPU refused");
  if(SetupProgram.Reason(inventory,"stable_audio")==null)throw new Exception("Gated access silently accepted");
  inventory["windows_build"]=19045;if(SetupProgram.Reason(inventory,"core")==null)throw new Exception("Windows 10 accepted");
  inventory["windows_build"]=null;if(SetupProgram.Reason(inventory,"core")==null)throw new Exception("Unknown Windows accepted");
  inventory["windows_build"]=22000;
  string root=Path.Combine(Path.GetDirectoryName(Environment.GetCommandLineArgs()[1]),"preaccept");
  string app=Path.Combine(root,"application"),storage=Path.Combine(root,"storage");
  var plan=SetupProgram.Plan(inventory,app,storage,new[]{"gemma"});
  if(Directory.Exists(root))throw new Exception("Preaccept scan created files");
  string reuse=Path.Combine(Path.GetDirectoryName(Environment.GetCommandLineArgs()[1]),"reuse-fixture");Directory.CreateDirectory(reuse);
  string artifact=Path.Combine(reuse,"model.bin");File.WriteAllText(artifact,"pinned");string sha=SetupProgram.HashFile(artifact);
  if(!SetupProgram.VerifiedFile(artifact,6,sha,reuse,System.Diagnostics.Stopwatch.StartNew()))throw new Exception("Verified existing download was not credited");
  File.WriteAllText(artifact,"broken");if(SetupProgram.VerifiedFile(artifact,6,sha,reuse,System.Diagnostics.Stopwatch.StartNew()))throw new Exception("Changed existing download received reuse credit");File.Delete(artifact);
  if(!((string[])plan["selected"]).Contains("ollama"))throw new Exception("Gemma omitted shared Ollama dependency");
  if((long)plan["project_reserve_bytes"]!=10*SetupProgram.GiB)throw new Exception("Missing project reserve");
  string before=SetupProgram.Fingerprint(plan);plan["application"]=app+"changed";
  if(before==SetupProgram.Fingerprint(plan))throw new Exception("Material plan change retained acceptance fingerprint");
  try{SetupProgram.LocalPath(@"\\server\share\app");throw new Exception("UNC allowed");}catch(IOException){}
  using(var wizard=new SetupWizard()){
   var fields=typeof(SetupWizard).GetFields(System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance);
   var checkbox=(CheckBox)fields.First(f=>f.Name=="acceptance").GetValue(wizard);
   var button=(Button)fields.First(f=>f.Name=="install").GetValue(wizard);
   if(checkbox.Checked||button.Enabled)throw new Exception("Acceptance starts checked or installation enabled");
  }
  string ready=Path.Combine(reuse,"ready.json"),endpoint;
  File.WriteAllText(ready,"{\"url\":");if(Program.TryReadReady(ready,out endpoint))throw new Exception("Partial readiness accepted");
  File.WriteAllText(ready,"{\"url\":\"http://127.0.0.1:32123\"}");
  using(var writer=new FileStream(ready,FileMode.Open,FileAccess.ReadWrite,FileShare.None))if(Program.TryReadReady(ready,out endpoint))throw new Exception("Locked readiness accepted");
  if(!Program.TryReadReady(ready,out endpoint)||endpoint!="http://127.0.0.1:32123")throw new Exception("Complete readiness refused after writer closed");
  File.WriteAllText(ready,"{\"url\":\"https://example.com\"}");if(Program.TryReadReady(ready,out endpoint))throw new Exception("Non-loopback readiness accepted");File.Delete(ready);
  var production=SetupProgram.Json.Deserialize<Dictionary<string,object>>("{\"assets\":[{\"id\":\"narration\"}],\"timeline\":{\"items\":[{\"track\":\"narration\",\"asset_id\":\"narration\"},{\"track\":\"video\",\"asset_id\":null},{\"track\":\"caption\"}]}}");
  if(SetupProgram.MediaPlaced(production))throw new Exception("Follow-up media was not awaited");
  var timeline=(Dictionary<string,object>)production["timeline"];var items=((System.Collections.IEnumerable)timeline["items"]).Cast<Dictionary<string,object>>().ToArray();items[1]["asset_id"]="video";production["assets"]=new[]{new Dictionary<string,object>{{"id","narration"}},new Dictionary<string,object>{{"id","video"}}};
  if(!SetupProgram.MediaPlaced(production))throw new Exception("Complete media refused");
  string sourceExe=Path.Combine(reuse,"source.exe"),uninstall=Path.Combine(reuse,"Uninstall.exe");File.WriteAllText(sourceExe,"new");File.SetAttributes(sourceExe,FileAttributes.ReadOnly);File.WriteAllText(uninstall,"old");File.SetAttributes(uninstall,FileAttributes.ReadOnly);
  SetupProgram.InstallUninstaller(sourceExe,reuse);if(File.ReadAllText(uninstall)!="new"||(File.GetAttributes(uninstall)&FileAttributes.ReadOnly)!=0)throw new Exception("Read-only uninstaller repair failed");File.SetAttributes(sourceExe,FileAttributes.Normal);File.Delete(sourceExe);File.Delete(uninstall);
  Console.WriteLine("PASS atomic replacement of read-only application-owned uninstaller");
  Console.WriteLine("PASS narration-ready timeline waits for follow-up media placement");
  Console.WriteLine("PASS partial/locked readiness retry and loopback endpoint boundary");
  Console.WriteLine("PASS hardware thresholds, Unknown refusal, gated access, dependency accounting, preaccept no mutation, acceptance invalidation, destination boundary and unchecked UI");return 0;
 }
}
