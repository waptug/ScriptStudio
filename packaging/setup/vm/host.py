"""Operate only the disposable ScriptStudio Hyper-V VM, without guest networking."""
import argparse, base64, json, subprocess
from pathlib import Path

ROOT = Path('/mnt/d/ScriptStudio-VM-Tests/Windows11-Core')
NAME = 'ScriptStudio-Clean-Win11'
PS = '/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'

def ps(code, timeout=180):
    command = [PS, '-NoProfile', '-Command', "$ErrorActionPreference='Stop';" + code]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except OSError as error:
        if error.errno != 8:
            raise
        result = subprocess.run(['/init', *command], capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout.strip()

def credentials():
    return "$c=Get-Content 'D:\\ScriptStudio-VM-Tests\\Windows11-Core\\credentials.json'|ConvertFrom-Json;$secure=ConvertTo-SecureString $c.password -AsPlainText -Force;$cred=New-Object System.Management.Automation.PSCredential(('SS-CLEAN-WIN11\\'+$c.username),$secure);"

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['status', 'start-tests', 'collect', 'inspect', 'checkpoint', 'screen', 'type'])
    parser.add_argument("text", nargs="?")
    args = parser.parse_args()
    if args.action == 'status':
        print(ps("$v=Get-VM -Name '"+NAME+"';$s=Get-CimInstance -Namespace root/virtualization/v2 -ClassName Msvm_ComputerSystem -Filter \"Name='$($v.Id)'\";$k=Get-CimAssociatedInstance $s -ResultClassName Msvm_KvpExchangeComponent;$k.GuestExchangeItems|ForEach-Object { $x=[xml]$_;$n=($x.INSTANCE.PROPERTY|Where-Object NAME -eq 'Name').VALUE;$d=($x.INSTANCE.PROPERTY|Where-Object NAME -eq 'Data').VALUE;if($n -like 'ScriptStudio*'){[pscustomobject]@{name=$n;data=$d}}}|ConvertTo-Json"))
    elif args.action == 'start-tests':
        print(ps(credentials()+"Invoke-Command -VMName '"+NAME+"' -Credential $cred -ScriptBlock {New-Item 'C:\\ScriptStudio-TestResults\\start.flag' -ItemType File -Force|Out-Null;'Test gate opened'}"))
    elif args.action == 'collect':
        raw=ps(credentials()+"Invoke-Command -VMName '"+NAME+"' -Credential $cred -ScriptBlock {Get-ChildItem 'C:\\ScriptStudio-TestResults' -File|Where-Object Extension -ne '.exe'|ForEach-Object {[pscustomobject]@{name=$_.Name;content=[Convert]::ToBase64String([IO.File]::ReadAllBytes($_.FullName))}}}|Select-Object name,content|ConvertTo-Json -Compress")
        items=json.loads(raw) if raw else []
        if isinstance(items,dict): items=[items]
        destination=ROOT/'results'; destination.mkdir(exist_ok=True)
        for item in items:
            if Path(item['name']).name!=item['name']: raise ValueError('Unsafe result filename')
            (destination/item['name']).write_bytes(base64.b64decode(item['content']))
        print(f'Collected {len(items)} result files into {destination}')
    elif args.action == 'inspect':
        print(ps(credentials()+"Invoke-Command -VMName '"+NAME+"' -Credential $cred -ScriptBlock {[pscustomobject]@{processes=@(Get-Process GuestChecks,ScriptStudio-Setup,ScriptStudio -ErrorAction SilentlyContinue|Select-Object Name,Id,MainWindowTitle);progress=[string[]](Get-Content 'C:\\ScriptStudio-TestResults\\progress.log' -Tail 15 -ErrorAction SilentlyContinue)}}|Select-Object processes,progress|ConvertTo-Json -Depth 4"))
    elif args.action == 'type':
        if not args.text: raise ValueError('Command text required')
        text=args.text.replace("'","''")
        print(ps("$v=Get-VM -Name '"+NAME+"';$k=Get-CimInstance -Namespace root/virtualization/v2 -ClassName Msvm_Keyboard|Where-Object SystemName -eq $v.Id;Invoke-CimMethod $k -MethodName TypeText -Arguments @{AsciiText='"+text+"'}|Out-Null;Start-Sleep -Seconds 2;Invoke-CimMethod $k -MethodName TypeKey -Arguments @{keyCode=[uint32]13}|Out-Null"))
    elif args.action == 'screen':
        from PIL import Image
        raw=ps("$v=Get-WmiObject -Namespace root/virtualization/v2 -Class Msvm_ComputerSystem -Filter \"ElementName='"+NAME+"'\";$service=Get-WmiObject -Namespace root/virtualization/v2 -Class Msvm_VirtualSystemManagementService;$r=$service.GetVirtualSystemThumbnailImage($v.__PATH,1024,768);if($r.ReturnValue -ne 0){throw 'Thumbnail failed'};[Convert]::ToBase64String($r.ImageData)")
        image=Image.frombytes('RGB',(1024,768),base64.b64decode(raw),'raw','BGR;16')
        image.save(ROOT/'vm-screen.png')
        print(ROOT/'vm-screen.png')
    else:
        print(ps("Set-VM -Name '"+NAME+"' -CheckpointType Standard;Checkpoint-VM -Name '"+NAME+"' -SnapshotName 'Clean-Windows11-before-installer';'Clean baseline checkpoint created'",timeout=1200))
