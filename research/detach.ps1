# Start a long research job as a hidden process that does not depend on the editor or terminal.
#
#   powershell -File research\detach.ps1 -Name pipeline -Command ".venv-gpu\Scripts\python.exe -u -m research.pipeline"
#
# Output goes to research\logs\<Name>.log; research\logs\<Name>.status holds "running", then "done" or "failed".
# The process is created through WMI, so it keeps running if VS Code or the terminal is closed or crashes.
param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Command
)
$root = Split-Path -Parent $PSScriptRoot
$logs = Join-Path $root 'research\logs'
New-Item -ItemType Directory -Force $logs | Out-Null
$log = Join-Path $logs "$Name.log"
$status = Join-Path $logs "$Name.status"
"running $(Get-Date -Format s)" | Set-Content -Encoding ascii $status

$line = "cmd.exe /c `"cd /d $root && set `"KERAS_BACKEND=torch`" && set `"PYTHONUNBUFFERED=1`" && " +
        "($Command) >> $log 2>&1 && (echo done> $status) || (echo failed> $status)`""
$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ ShowWindow = [uint16]0 }
$result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine = $line; CurrentDirectory = $root; ProcessStartupInformation = $startup
}
if ($result.ReturnValue -ne 0) { throw "Could not start $Name (WMI return value $($result.ReturnValue))" }
"started $Name, pid $($result.ProcessId), log $log"
