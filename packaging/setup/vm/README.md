# Disposable Windows 11 core qualification VM

`GuestChecks.cs` is compiled on the host and placed with the unchanged release EXE
on a test DVD. No compilers, SDKs, third-party Python, PostgreSQL, Docker, WSL2,
or Node are installed in the guest. Windows' bundled .NET runtime runs the harness.
The harness uses the actual setup wizard through UI Automation, including its
unchecked acceptance control. The VM is authorized solely for core qualification.

The current host fixture is `ScriptStudio-Clean-Win11`, under
`D:\ScriptStudio-VM-Tests\Windows11-Core`: Generation 2, Secure Boot, virtual TPM,
4 CPUs, a fixed 8 GiB RAM allocation, and a 100 GiB dynamic VHDX. Its network adapter is disconnected.
Official Windows Enterprise evaluation media and a separate unattended test DVD
install Windows into the VM's new disk only. The evaluation is time limited.
A generated VM-only local account supports unattended execution and PowerShell
Direct. Credentials and answer files stay outside Git and release artifacts.

The guest pauses before installation so the host can checkpoint clean Windows.
`host.py checkpoint` saves that baseline, and `host.py start-tests` opens the gate.
PowerShell Direct and Hyper-V data exchange work without guest networking.
`host.py status` reads progress; `host.py collect` retrieves reports and screenshots
into the fixture's `results` directory. Run the host utility from WSL.

Checks cover absence of development/runtime dependencies, no guest networking,
the exact release EXE checksum, inventory without installation, unchecked
acceptance, cancellation with a durable journal, resumed offline core installation,
the installer's database/API/narration/preview/final/subtitle/OpenShot smoke tests,
browser launch, a project surviving an actual Windows reboot, automatic repair of
an intentionally corrupted extracted file, and reinstall/repair preserving the
project while backing up PostgreSQL. The harness leaves the installed application
available in the VM after success.

A core VM cannot qualify NVIDIA drivers, CUDA, optional model downloads/generation,
physical GPU inventory, or all supported upgrade versions. Full release decisions
must retain those distinctions. Do not distribute the evaluation VM or test-account
credentials as application release assets.

`create-vm.ps1` creates the fixture from prepared ISOs and refuses an existing VM.
Host tools are Python, optional Pillow for console thumbnails, and pycdlib for
creating the test ISO; all remain outside the guest. The host must have enough
free physical memory to reserve 8 GiB. Preserve existing Windows execution policy
when running host commands.

Use `prepare-media.py` with pycdlib installed to generate the test DVD from the
release EXE and its checksum sidecar. Inspect the visible Windows desktop before
opening the gate; FirstLogonCommands can start before first-login screens finish.
The harness allows five minutes for a cold setup launch and verifies that the
action buttons fit within the guest display working area. A new preview can use
a fresh media directory and the existing VM-only credential file.

Completed core evidence is summarized in `docs/verification.md` and the fixture’s
`results/report.html`. Read-only installer media is intentional: the setup copy
must normalize its application-owned uninstaller before atomic repair. Cold HDD
startup can exceed five minutes, so the harness permits fifteen minutes while
retaining full file verification. A resumed harness preserves already-passed
cache-repair evidence and proceeds with the remaining installer repair.
