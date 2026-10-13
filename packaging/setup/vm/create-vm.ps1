param(
    [string]$TestRoot = 'D:\ScriptStudio-VM-Tests\Windows11-Core',
    [string]$VMName = 'ScriptStudio-Clean-Win11'
)
$ErrorActionPreference = 'Stop'
if (Get-VM -Name $VMName -ErrorAction SilentlyContinue) {
    throw "VM already exists: $VMName. Refusing to replace it."
}
$root = [IO.Path]::GetFullPath($TestRoot)
$volume = Get-Volume -DriveLetter $root.Substring(0,1)
if ($volume.SizeRemaining -lt 120GB) { throw 'At least 120 GiB free host storage is required.' }
$windowsISO = Join-Path $root 'media\Windows11-Enterprise-Eval.iso'
$testISO = Join-Path $root 'media\ScriptStudio-Test.iso'
foreach ($iso in @($windowsISO, $testISO)) {
    if (!(Test-Path $iso -PathType Leaf)) { throw "Missing prepared media: $iso" }
}
$expected = 'BC3F24086EBADC94489066B5AD78089E2CF5C3491E90E790BB81A2B199C10E38'
if ((Get-FileHash $windowsISO -Algorithm SHA256).Hash -ne $expected) {
    throw 'Microsoft Windows evaluation ISO checksum mismatch.'
}
New-VM -Name $VMName -Generation 2 -MemoryStartupBytes 8GB `
    -NewVHDPath (Join-Path $root 'Windows11-Core.vhdx') -NewVHDSizeBytes 100GB -Path $root
# New-VM defaults to dynamic memory on this host. Use a fixed allocation so Windows
# Setup and the core eligibility check retain the required amount of installed RAM.
Set-VMMemory -VMName $VMName -DynamicMemoryEnabled $false -StartupBytes 8GB
Set-VMProcessor -VMName $VMName -Count 4
Set-VM -Name $VMName -AutomaticCheckpointsEnabled $false -CheckpointType Standard
Set-VMKeyProtector -VMName $VMName -NewLocalKeyProtector
Enable-VMTPM -VMName $VMName
Set-VMFirmware -VMName $VMName -EnableSecureBoot On
Disconnect-VMNetworkAdapter -VMName $VMName
Add-VMDvdDrive -VMName $VMName -Path $windowsISO
Add-VMDvdDrive -VMName $VMName -Path $testISO
$dvd = Get-VMDvdDrive -VMName $VMName | Where-Object Path -eq $windowsISO
Set-VMFirmware -VMName $VMName -FirstBootDevice $dvd
Get-VM -Name $VMName
