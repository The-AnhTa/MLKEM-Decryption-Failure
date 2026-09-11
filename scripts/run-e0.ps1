$ErrorActionPreference = 'Stop'
& "$PSScriptRoot\build.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

foreach ($mode in @('none', 'no-compression', 'independent-compression')) {
    & "$PSScriptRoot\..\build\toy-mlkem.exe" --preset e0 --mode $mode --output "$PSScriptRoot\..\results\e0\$mode"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    python "$PSScriptRoot\..\python\analyze.py" "$PSScriptRoot\..\results\e0\$mode" --feature pk
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

python "$PSScriptRoot\..\python\analyze.py" "$PSScriptRoot\..\results\e0\none" --feature pk `
    --derive-independent-output "$PSScriptRoot\..\results\e0\independent-output"
python "$PSScriptRoot\..\python\analyze.py" "$PSScriptRoot\..\results\e0\independent-output" --feature pk
