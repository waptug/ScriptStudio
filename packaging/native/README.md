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

All four local media models are installed and generation-tested for the app under
`D:\ScriptStudio` (changed from E: after drive failures). The current source includes Admin controls and model adapters,
but no model should be considered installed until its pinned runtime/weights are
present and real generation succeeds. `resolve_local_models.py` resolves Kokoro,
Wan, ACE-Step, and Stable Audio dependencies using native Windows Python and keeps its downloads and
pip cache in the directory passed with `--work`. It generates the manifests used
by the app installer; it does not itself mark a model ready. Kokoro has generated real narration on Windows, ACE-Step has generated real music,
Wan generated a real 81-frame 480p clip, and local Ollama writing/planning and
native preview playback passed. Stable Audio generated five seconds of real 44.1 kHz stereo sound effects and
passed native MP4 export with non-silent audio. Its separate T5 encoder is pinned
and loaded locally; inference runs with Hugging Face offline mode enabled.
See [the local-model usage guide](../../docs/local-models.md).

On this workstation, E: returned Windows error 21 (device not ready). D: passed
a native write test and has ample space. The exact application backup has been
recovered and its package verified on D:. The current Docker projects were
copied to D: as authorized; E:-only recovery is deferred. Stable Audio requires upstream access and a token
saved through Admin. Do not place credentials in installer command lines.

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

For native verification, `--serve-test --open-browser` also opens the dedicated
portable browser. Pass `-Exe <full Windows EXE path>` to `test-runtime.ps1`; its
`storage` action checks portable paths after the browser workflow creates media.
`test_launcher.py` compiles current launcher sources and covers low-disk refusal,
archive safety, and the C# storage checks. `SCRIPTSTUDIO_EXTRACT_TEST_DIR` can
place those small test EXEs on a chosen drive.

For a gated model, `resolve_local_models.py stable_audio --runtime-only --work <Windows-path>
--locks <Windows-path>` prepares only its public dependency report. It does not
access gated weights, create an installable manifest, or mark the model ready.
The current Stable Audio runtime pins PyTorch Lightning 2.5.5 and torchmetrics
0.11.4 because stable-audio-tools imports its LoRA callbacks during inference.
It uses Python 3.10 with NumPy 1.26.4 for its pinned
PyWavelets dependency. Completing the model manifest still requires approved
upstream access and a token supplied through the encrypted Admin configuration.

`ScriptStudio-Native-Windows-x64.exe --workspace local-models --start` opens a separate
portable workspace in `ScriptStudioNative/workspace-local-models`. Workspace
names use letters, numbers, underscores, and hyphens; they cannot name paths or
escape the portable folder. Names are case-normalized for launch locking.
Each workspace owns its projects and credentials while sharing the model files
under `ScriptStudioNative/local-models`. The default launch still uses `data`.
This permits a separate local-model desktop shortcut while old-drive project
recovery is pending. Close the app before moving any workspace directory.

The optional final `--start` flag starts the services and opens the studio when
the launcher appears. Stop studio and closing the launcher still drain active
jobs before shutdown. Without that flag, use the Start studio button.

The workstation desktop shortcut **ScriptStudio Local Models** targets
`D:\ScriptStudio\ScriptStudio-Local-Models.exe --workspace local-models --start`.
Its visible launcher/editor, three Ready model panels, real-video preview, and
final export were verified. E:-only originals remain preserved; the D: workspace now includes the Docker projects described below.

On 2026-09-19, the user selected the running Docker installation as the project
source. Its 65 projects and media were copied into the D: local-model workspace
while preserving the 10 projects already there. The 75-project dashboard,
imported media playback, and a new native preview render passed. Backups and
checksums are recorded in PLAN.md. E: originals and Docker data remain untouched.
