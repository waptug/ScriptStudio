using System;
using System.Diagnostics;
using System.IO;
static class StorageChecks {
 static int Main() {
  if(Program.Root!=Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"ScriptStudioNative"))throw new Exception("Storage is not beside the executable");
  if(Program.WorkspaceData("Local-Models")!=Path.Combine(Program.Root,"workspace-local-models"))throw new Exception("Workspace is not portable or case-normalized");
  foreach(string name in new[]{"","..","../data","C:\\data","models/other",new string('a',65)}) {
   try {Program.WorkspaceData(name);throw new Exception("Unsafe workspace accepted");}
   catch(ArgumentException) {}
  }
  Program.RequireSpace(1024,1024);
  try {Program.RequireSpace(1024,1023);throw new Exception("Low space accepted");}
  catch(DiskSpaceException e){if(!e.Message.Contains(Program.LaunchDirectory)||!e.Message.Contains("Close the launcher"))throw;}
  Program.CheckSpace(0);
  var info=new ProcessStartInfo("unused"){UseShellExecute=false};
  Program.ConfigureEnvironment(info);
  foreach(string key in new[]{"TEMP","TMP","TMPDIR","USERPROFILE","HOME","APPDATA","LOCALAPPDATA","XDG_CACHE_HOME","PYTHONPYCACHEPREFIX"})
   if(!info.EnvironmentVariables[key].StartsWith(Program.Root+Path.DirectorySeparatorChar))throw new Exception("Nonportable "+key);
  var bytes=new byte[]{9,1,2,3,9};
  using(var view=new PayloadStream(new MemoryStream(bytes),1,3)) {
   if(view.ReadByte()!=1||view.Seek(-1,SeekOrigin.End)!=2||view.ReadByte()!=3||view.ReadByte()!=-1)throw new Exception("Payload boundary error");
  }
  Console.WriteLine("PASS portable paths, child temp/cache isolation, exact free-space boundary, low-disk message, bounded ZIP stream");
  return 0;
 }
}
