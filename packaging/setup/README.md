# Windows 11 single-EXE setup

`ScriptStudio-Setup.exe` is the distributed file. It contains a rebuilt native core
launcher and complete payload. Extraction creates persistent application/storage
files. Optional weights and Ollama download automatically only after acceptance.
There are no companion files the user must install manually.

The wizard uses version 1 JSON contracts for inventory, accounting plan, acceptance,
journal and verification. Its initial acceptance box is unchecked. Changing the
selection or either location invalidates the plan and acceptance. Preaccept scans
only read bounded system/service metadata. Saving a requested report writes that
report alone. Inventory stays local. Detection failures are Unknown, never Ready.
The screen shows all artifacts, hashes, sizes, sources, licenses, runtime revisions,
locations, storage allowances and unavailable features. Save JSON or printable HTML.

Core screens for Windows 11 AMD64, 4 logical cores, 8 GiB RAM and Edge/Chrome.
Kokoro uses SSE2 CPU screening. Writing/planning screens for 16 GiB RAM. CUDA media
screens for 32 GiB RAM, 12 GiB dedicated NVIDIA memory and compute capability 7+;
actual driver/CUDA support is established by the runtime probe. This policy is
conservative and does not guarantee generation speed. Unknown adapter shared memory,
CPU AVX support, available storage write permissions and CUDA runtime compatibility
are not guessed. Stable Audio requires separate upstream acceptance and a token
in Admin, and is unavailable in the initial wizard. No driver/power/container settings
are changed. Official NVIDIA driver guidance is in the report.

Defaults: `%LOCALAPPDATA%\Programs\ScriptStudio` for versioned applications,
`%LOCALAPPDATA%\ScriptStudio` for writable storage. Destinations must be separate
fixed local folders without junctions. Model downloads retain `.part` files on
interruption and verify SHA-256 before activation. An OS lock prevents concurrent
setup. The durable journal records interruptions; rerun and review/accept the plan
to resume. Runtime packages use staging and atomic directory moves. Projects and
model storage are never deleted by the uninstaller. Stop the studio before upgrade;
a cold database backup and matching runtime credential configuration are retained
before migrations. PostgreSQL major-version mismatch refuses upgrade. Never merge
another database directory into this storage.

Accounting credits selected existing downloads only after complete SHA-256 verification, with a bounded ten-second file-scan budget. Unverified files receive no credit; installed runtime storage remains a conservative allowance until its probe. Separate per-model
runtime copies are counted separately because the backend actually stores them
separately. Gemma automatically adds its single Ollama dependency. Ollama's pinned
archive expansion has a conservative 6 GiB allowance; extraction refuses a larger
archive. The final report distinguishes runtime probes from generation checks.
Core smoke verification creates its own `setup-verification` workspace, checks
native narration, preview/final MP4, SRT/VTT, OpenShot bundle and database/API startup.
Gemma receives a short real text check. Media models receive runtime probes;
Kokoro/ACE-Step receive short real audio checks; the separately offered lengthy Wan check still needs clean-machine qualification. Browser availability is detected; interactive launch is not
claimed as verified. Failed optional media installs remain unavailable.

## Build

Build host: WSL attached to Windows 11, Python 3.12, Node 24.13.1, Windows .NET
Framework C# compiler, and extracted native input distributions described in
`../native/README.md`. Target users need none of these build tools.

```sh
export SCRIPTSTUDIO_NATIVE_INPUT=/path/to/prepared/native-inputs
python3 packaging/setup/verify_inputs.py
npm ci --prefix frontend
npm run build --prefix frontend
python3 packaging/native/build.py
python3 packaging/setup/build.py
python3 packaging/setup/validate.py artifacts/setup/ScriptStudio-Setup.exe
python3 packaging/setup/test_setup.py
python3 packaging/native/test_launcher.py
```

The tag workflow expects a self-hosted runner labeled `scriptstudio-windows11` with
these pinned inputs. It creates a **draft** release until clean-machine qualification
is complete. It does not provision a runner or install dependencies on client machines.
`pin_ollama.py` is a maintainer resolver, never executed during setup. Native inputs
are checksum-locked; prepared extracted trees must be recreated from those downloads.
The runtime Python dependency lock is in `../native/requirements.lock`. Every
embedded payload file is inventoried and hashed. The outer EXE also embeds the exact current first-party build/source snapshot; `ScriptStudio-Setup.exe --export-source <source.zip>` exports it without installation. Build uses only allowlisted source paths;
workstation projects, browser profiles, caches, analytics and promotional trees
are excluded. The EXE size guard rejects assets at or above 2 GiB, consistent with
[GitHub's release limit](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).

## Qualification before publication

Run the downloaded EXE on clean Windows 11 x64 machines without Docker, WSL,
installed Python, or development tools. Record evidence for:

- Offline core installation, narration, preview/final MP4, SRT/VTT, OpenShot import and browser launch.
- Unsupported OS/architecture, insufficient RAM/storage, unknown inventory, unsupported NVIDIA driver/GPU, and core-only selections.
- Unchecked acceptance, changed selections/locations, no preaccept extraction/download/database initialization.
- Corrupted installer/native payload and cached components, unsafe archive paths, permission failure, disk exhaustion.
- Cancel during download/extraction, interruption/restart/resume/repair, concurrent installers.
- Existing Ollama reuse, private Ollama lifecycle, real Kokoro/ACE-Step generation and optional lengthy Wan check; Stable Audio upstream-access denial/acceptance.
- Upgrades against isolated copies with database backup, failed migration recovery, uninstaller preservation and no database-directory merging.

Do not publish a draft until this matrix passes. The current implementation still
still needs complete runtime reuse accounting, automated upgrade/migration recovery qualification, and clean-machine qualification. Rerunning setup revalidates cached components and resumes model downloads; activation remains on the previous version until verification succeeds.
These limitations are not covered by the C# policy harness alone.
