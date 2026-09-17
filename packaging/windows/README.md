# ScriptStudio Windows offline package

This is one Windows x64 EXE containing the application, Linux runtime images,
matching application source, and license notices. It is **not a Docker-free native
Windows port**. No Python, Node.js, source checkout, or image download is required
on the target machine after the container runtime is available.

## Run

1. Use Windows with .NET Framework 4.5+ (the launcher uses the Windows-provided
   framework) and a running Linux Docker engine with Compose v2. Docker Desktop
   is supported, or Docker in an already-running WSL distribution. Windows-container
   mode is not supported. Docker Desktop/WSL are not installed by this package;
   their installation terms and system requirements apply separately.
2. Double-click `ScriptStudio-Windows-x64.exe`, then click **Start studio**.
   The launcher checks the package checksum, extracts its payload under
   `%LOCALAPPDATA%\ScriptStudio\packages`, loads missing bundled images, starts
   services, waits for health, and opens your browser.
3. **Stop services** stops this package's services while retaining project data.
   Closing the launcher leaves services running. Open the EXE again to restart
   or stop them. **Package files** opens the local package/configuration folder.

The initial port is the first available Windows loopback port from 8088–8187.
It is saved in `desktop.env`; subsequent launches use the same port. If another
application later takes that port, stop ScriptStudio and edit only
`SCRIPTSTUDIO_PORT` in that file. Do not change the generated database password
after the database has been initialized.

The package uses a per-Windows-user Compose project name beginning with
`scriptstudio-desktop-`. Its database/media volumes are separate from a developer
checkout's `scriptstudio` volumes. Existing developer projects are not imported.
Admin credentials and projects belong to these new persistent volumes, not the
EXE. Keep both volumes and `desktop.env` when backing up. Never run Compose with
`down -v` unless intentionally erasing that installation. Paid generation starts
disabled; no paid credentials or user media are included in the EXE. Local Ollama
is optional and not included; the demonstration works without it.

The EXE is unsigned. This build does not claim a signing identity. Package hashes
detect accidental payload corruption; they are not a substitute for a trusted
distribution channel. Allow several GB of free disk for the EXE, extraction,
loaded images, and growing media, and sufficient memory for Docker/rendering.
Continue using the same Docker engine for an installation: Docker Desktop and
different WSL distributions have separate volume stores. The launcher tries the
Windows Docker CLI first, then Docker in running WSL distributions; it does not
copy projects between engines.

## Build from the repository in WSL

Build and verify the application first, then:

```bash
docker compose up -d --build
python3 packaging/windows/build.py
```

The builder uses the installed Windows .NET Framework C# compiler. Override its
WSL path with `SCRIPTSTUDIO_CSC` if needed. It exports four existing Linux amd64
images (API, web, PostgreSQL, Redis), with shared image layers deduplicated. It
does not export containers or volumes, does not read `.env`, and refuses tracked
environment files other than `.env.example`. All output is ignored under
`artifacts/windows/`. The `manifest.json` records image IDs and a source checksum.

The application source archive includes tracked and nonignored source files at
build time; inspect `git status` before building. License notices are included
and remain inside the images. If redistributing these third-party binaries,
retain their notices and provide any corresponding sources required by their
licenses; the application source archive alone is not the source for all Debian
or other bundled dependencies. This local package is not a public release audit.

## Verification

`ScriptStudio-Windows-x64.exe --verify C:\path\report.txt` verifies the embedded
payload and extracts without running Docker. The Windows process returns a
nonzero exit code on corruption or extraction failure. The package does not
install system services or change Windows features.

For isolated integration verification, `--start-test` and `--stop-test` accept
the same report path and use `scriptstudio-exe-test` with port 18089 and a separate
`test.env`. These switches never use the normal desktop/development volumes.
Use the real Windows process and actual Docker engine, then verify its web UI and
mock video workflow. Record Windows execution, engine backend, and untested
targets separately; compiling an EXE is not evidence that it runs on every PC.

From WSL, `python3 packaging/windows/run_check.py --start-test` captures the
Windows process report. `--runtime-test` checks runtime discovery, and `--ui-test`
briefly opens the native launcher and captures its rendered window beside the
report. `test_launcher.py` runs small valid, corrupted, traversal, and incomplete
package fixtures against the compiled launcher stub. The build/check helpers can
use WSL's explicit `/init` loader if native-executable binfmt registration is absent;
they do not alter system registration or Windows features.
