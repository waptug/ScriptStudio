Download **ScriptStudio-Setup.exe** and verify its SHA-256 using the attached checksum.
This EXE is unsigned. Review Windows security prompts and the source before accepting it; do not disable security controls.

Windows 11 x64, at least 4 logical CPU cores, 8 GiB RAM, Edge/Chrome, a writable fixed local disk, and 10 GiB of project reserve are required. No Docker, WSL, installed Python, compiler, or development tools are needed on the target machine.

The single EXE contains the native core. Optional selected models download automatically after acceptance and require internet. CUDA media screens for 32 GiB RAM and 12 GiB dedicated NVIDIA VRAM; runtime verification establishes device support. Gemma/Ollama requires 16 GiB RAM. Stable Audio requires separate upstream terms and authorized access through Admin.

Run the wizard, scan, select features and locations, review/save accounting, check the initially unchecked acceptance box, and click **Accept and install**. Failed optional features remain unavailable. Projects, credentials, models and media are preserved during uninstall. Stop an existing installation before upgrade; setup backs up its database before migration and never merges database directories.

Source and build tooling: https://github.com/waptug/ScriptStudio . After cloning a release tag, run `python3 scripts/download-installer.py` to download and verify its matching EXE.

This draft must pass the clean Windows 11 qualification matrix in packaging/setup/README.md before publication. Runtime probes alone do not certify media model generation.
