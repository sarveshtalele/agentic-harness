# Agentic QE MAF 2.0 Terminal Harness Runner for Windows (PowerShell)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

$env:PYTHONPATH = "$ProjectRoot\src;$ProjectRoot;$env:PYTHONPATH"

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 "$ProjectRoot\src\backend\cli.py" @args
} else {
    & python "$ProjectRoot\src\backend\cli.py" @args
}
