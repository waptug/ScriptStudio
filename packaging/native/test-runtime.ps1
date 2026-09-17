param([string]$Repo, [string]$Action = 'browser', [string]$Exe)
$ErrorActionPreference = 'Stop'
if (-not $Exe) {$Exe = Join-Path $Repo 'artifacts\native\ScriptStudio-Native-Windows-x64.exe'}
$data = Join-Path (Split-Path -Parent $Exe) 'ScriptStudioNative\test-data'
$env:SCRIPTSTUDIO_TEST_DATA = $data
$env:TEMP = Join-Path $data 'temp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force $env:TEMP | Out-Null
$ready = Get-Content (Join-Path $data 'ready.json') | ConvertFrom-Json
$env:SCRIPTSTUDIO_URL = $ready.url
$env:SCRIPTSTUDIO_BROWSER = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
if ($Action -eq 'browser') {
  Set-Location (Join-Path $Repo 'frontend')
  & (Join-Path $Repo 'artifacts\native\node\node-v24.13.1-win-x64\node.exe') (Join-Path $Repo 'frontend\node_modules\@playwright\test\cli.js') test
  exit $LASTEXITCODE
}
if ($Action -eq 'storage') {
  $root = Split-Path -Parent $data
  if (-not (Get-Process -Id $ready.pid).Path.StartsWith($root)) {throw 'Backend is outside portable folder'}
  foreach ($part in @('database','media','temp','cache\python','profile','browser\Default')) {
    if (-not (Test-Path (Join-Path $data $part))) {throw ('Missing portable path: ' + $part)}
  }
  $prefs = Get-Content (Join-Path $data 'browser\Default\Preferences') | ConvertFrom-Json
  if ($prefs.download.default_directory -ne (Join-Path $root 'downloads')) {throw 'Browser download path is not portable'}
  $profile = Join-Path $data 'browser'
  $browser = Get-CimInstance Win32_Process -Filter "Name='msedge.exe' OR Name='chrome.exe'" | Where-Object {$_.CommandLine -and $_.CommandLine.Contains($profile)}
  if (-not $browser) {throw 'Portable browser profile was not launched'}
  Write-Output 'PASS backend, database, media, temp, Python cache, browser profile and download default stay beside EXE'
  exit 0
}
if ($Action -eq 'stop') {
  Set-Content -Path (Join-Path $data 'stop.request') -Value 'stop'
  exit 0
}
if ($Action -eq 'health') {
  Invoke-RestMethod ($ready.url + '/api/health') | ConvertTo-Json
  exit 0
}
if ($Action -eq 'modules') {
  $process = Get-CimInstance Win32_Process -Filter "Name='postgres.exe'" | Where-Object {$_.ExecutablePath -like '*ScriptStudioNative*'} | Select-Object -First 1
  $modules = (Get-Process -Id $process.ProcessId).Modules | Where-Object {$_.ModuleName -match 'msvcp140|vcruntime140'}
  if (-not $modules) {throw 'Expected native C++ modules were not found'}
  foreach ($module in $modules) {
    if ($module.FileName -notlike '*ScriptStudioNative*') {throw ('External runtime dependency: ' + $module.FileName)}
    Write-Output ('Bundled runtime: ' + $module.FileName)
  }
  exit 0
}
if ($Action -in @('tests','concurrency','snapshot')) {
  $python = (Get-Process -Id $ready.pid).Path
  & $python -X utf8 (Join-Path $Repo 'packaging\native\validate.py') $Action --repo $Repo
  exit $LASTEXITCODE
}
throw 'Unknown test action'
