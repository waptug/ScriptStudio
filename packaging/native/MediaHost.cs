// Runs the bundled OpenShot Python ABI in a dedicated native process.
using System;
using System.IO;
using System.Runtime.InteropServices;
class MediaHost {
 [DllImport("kernel32", CharSet=CharSet.Unicode, SetLastError=true)] static extern IntPtr LoadLibrary(string path);
 [DllImport("kernel32", CharSet=CharSet.Ansi)] static extern IntPtr GetProcAddress(IntPtr module, string name);
 [DllImport("kernel32", CharSet=CharSet.Unicode)] static extern bool SetDllDirectory(string path);
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate void SetPath([MarshalAs(UnmanagedType.LPWStr)] string path);
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate void Initialize();
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int Run([MarshalAs(UnmanagedType.LPStr)] string code);
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int Finish();
 static T Get<T>(IntPtr dll,string name) { return (T)(object)Marshal.GetDelegateForFunctionPointer(GetProcAddress(dll,name),typeof(T)); }
 static int Main(string[] args) {
  try {
   string root=AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\');
   SetDllDirectory(Path.Combine(root,"lib"));
   Environment.SetEnvironmentVariable("PATH",root+";"+Path.Combine(root,"lib")+";"+Environment.GetEnvironmentVariable("PATH"));
   Environment.SetEnvironmentVariable("QT_PLUGIN_PATH",root);
   Environment.SetEnvironmentVariable("QT_QPA_PLATFORM","offscreen");
   Environment.SetEnvironmentVariable("OMP_NUM_THREADS","2");
   Environment.SetEnvironmentVariable("SS_MEDIA_SCRIPT",Path.GetFullPath(args[0]));
   Environment.SetEnvironmentVariable("SS_MEDIA_INPUT",args.Length>1?Path.GetFullPath(args[1]):"");
   IntPtr dll=LoadLibrary(Path.Combine(root,"libpython3.8.dll"));
   if(dll==IntPtr.Zero) throw new Exception("Cannot load OpenShot Python runtime: "+Marshal.GetLastWin32Error());
   Get<SetPath>(dll,"Py_SetPath")(Path.Combine(root,"lib","library.zip")+";"+Path.Combine(root,"lib"));
   Marshal.WriteInt32(GetProcAddress(dll,"Py_NoSiteFlag"),1);
   Get<Initialize>(dll,"Py_Initialize")();
   int result=Get<Run>(dll,"PyRun_SimpleString")("import sys, os\nsys.argv=[os.environ['SS_MEDIA_SCRIPT'],os.environ.get('SS_MEDIA_INPUT','')]\nexec(compile(open(sys.argv[0],encoding='utf-8').read(),sys.argv[0],'exec'),{'__name__':'__main__','__file__':sys.argv[0]})\n");
   Get<Finish>(dll,"Py_FinalizeEx")();
   return result==0?0:1;
  } catch(Exception e) { Console.Error.WriteLine(e); return 1; }
 }
}
