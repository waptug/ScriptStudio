# ScriptStudio native Windows package

A Windows x64 EXE with native Python, PostgreSQL, OpenShot, FFmpeg and eSpeak NG.
No Docker, WSL, Redis, installed Python, or internet connection is required to use
local mock generation. Live providers require your credentials and explicit paid
permissions. The launcher uses the .NET Framework supplied with Windows 10/11.

Double-click the EXE and choose Start studio. Keep the launcher open while using
the browser editor. Stop studio or close the launcher to drain active jobs and
stop the database. Projects and credentials remain in
`ScriptStudioNative\data` beside the EXE. Back up this complete directory while
the studio is stopped. The Docker installation is separate; no automatic migration
is performed. The EXE is unsigned.

The native worker polls PostgreSQL through the same job coordinator, row locks,
leases, cost reservations and paid-submission reconciliation as the Linux worker.
OpenShot runs in a separate process with its matching Python ABI. Services bind
only to Windows loopback. A Windows Job Object terminates child processes if the
launcher crashes; PostgreSQL then performs recovery on restart.

Build entrypoint: `python3 packaging/native/build.py`. The current build host is
WSL with access to Windows C# compiler; this is a build requirement only. Download
and extract these upstream distributions under `artifacts/native`:

- Python 3.12.10 embedded amd64 from python.org, into `python`; install Windows
  cp312 wheels from backend requirements under `python/Lib/site-packages` and
  enable that path plus `import site` in python312._pth. Use the resolved
  `packaging/native/requirements.lock`, including Windows-only colorama.
- PostgreSQL 17.11-3 Windows x64 binaries from EDB, into `postgres/pgsql`.
- OpenShot 4.0.0 x86_64 installer from its GitHub release, extracted by innoextract
  into `openshot/app`. No installed OpenShot is read by the build.
- FFmpeg 9.0.1 essentials ZIP from gyan.dev into `ffmpeg`.
- eSpeak NG 1.51 x64 MSI from its GitHub release, extracted by msiextract into
  `speech/eSpeak NG`. Version 1.52.0's upstream MSI failed archive validation.

- Microsoft Visual C++ 14.44.35211 x64 runtime from Microsoft
  `https://aka.ms/vs/17/release/vc_redist.x64.exe`. Extract its Burn cabinets and
  x64 minimum-runtime cabinet, preserve DLL names under `msvc`, and include
  the embedded English `license.rtf` and its plain-text `license.txt` conversion.
  Build copies DLLs beside the API, speech,
  and PostgreSQL executables. No system-wide runtime installer is run.

Build the frontend before packaging. The build records download checksums, embeds
application source, runtime notices, and a hashed file inventory. About shows the
native inventory in this package. Upstream native distributions contain additional
third-party components; the inventory does not certify a complete corresponding-
source distribution for every bundled dependency. Preserve upstream notices and
review redistribution requirements before publishing binaries to third parties.

Validation status is recorded in docs/verification.md. `--serve-test` starts an
isolated native instance on a free loopback port with `ScriptStudioNative/test-data`;
creating `stop.request` there stops it gracefully. `--verify` verifies/extracts
without starting services.

### Portable Windows storage and free space

The native launcher resolves its EXE folder, independently of the current working
directory. Runtime packages, PostgreSQL, projects, logs, temporary files, caches,
and the dedicated Edge/Chrome browser profile stay in `ScriptStudioNative` beside
the EXE. Browser downloads default to `ScriptStudioNative/downloads`. Move the
EXE and that folder together while the launcher is closed. The browser profile
is separate from your usual browser; Windows and separately installed Ollama
remain responsible for their own system files and model storage.

Before extraction, the launcher checks free space on the actual destination
volume for the expanded archive (plus filesystem overhead) and 2 GiB of working
space. Cached launches require 2 GiB free. It reads the ZIP directly from the
EXE, without creating a second compressed copy. Insufficient space shows required
and available space and closes the launcher after acknowledgement, before any
services start. The 2 GiB reserve is a startup minimum, not an estimate of space
needed for arbitrary future video projects. Use a writable local folder.

Older versions stored projects in `%LOCALAPPDATA%\ScriptStudioNative\data`.
To retain those projects, stop and close the old launcher, then move that complete
`data` directory into the new `ScriptStudioNative` folder **before first start**.
Do not merge two database directories. The launcher identifies legacy data but
never copies a potentially running database or deletes existing projects.
