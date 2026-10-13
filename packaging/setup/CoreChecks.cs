using System;
using System.IO;
using System.Reflection;
static class CoreChecks {
 static int Main(string[] args){
  var ready=SetupProgram.Read(Path.Combine(args[0],"ready.json"));
  typeof(SetupProgram).GetField("url",BindingFlags.Static|BindingFlags.NonPublic).SetValue(null,(string)ready["url"]);
  try{SetupProgram.SmokeCore(Console.WriteLine);Console.WriteLine("PASS isolated native database/API, narration, preview/final MP4, SRT/VTT and OpenShot bundle");return 0;}
  catch(Exception e){Console.Error.WriteLine(e);return 1;}
 }
}
