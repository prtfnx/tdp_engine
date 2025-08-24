# Activate virtual environment
$env:VIRTUAL_ENV = "$PSScriptRoot\.venv"
$env:PATH = "$env:VIRTUAL_ENV\Scripts;$env:PATH"

# Run py-spy and launch your app, recording a flamegraph for 30 seconds
#py-spy record -o profile.svg --subprocesses python main.py
py-spy top  --subprocesses python main.py
Write-Host "Profiling complete. See profile.svg for results."