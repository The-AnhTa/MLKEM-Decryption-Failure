param(
    [switch]$ReuseData
)

$ErrorActionPreference = 'Stop'
$root = 'results/final-su1-confirmation'
$candidates = @('n8q29d43', 'n8q23d43', 'n8q19d43')

./scripts/build.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

foreach ($preset in $candidates) {
    ./build/toy-mlkem.exe --preset $preset --support-bound `
        --output "$root/support/$preset"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

python python/final_su1_confirmation.py preregister --root $root --repo .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$registration = Get-Content -Raw "$root/preregistration.json" | ConvertFrom-Json
$selected = $registration.selected_preset
if ($null -eq $selected) {
    throw 'No preregistered candidate passed feasibility and support checks.'
}

if (-not $ReuseData) {
    ./build/toy-mlkem.exe --preset $selected --sample-keys 128 --sample-y 4 `
        --seed 20260916 --su1-confirmation --output "$root/data/$selected"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

python python/final_su1_confirmation.py evaluate --root $root --repo .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
