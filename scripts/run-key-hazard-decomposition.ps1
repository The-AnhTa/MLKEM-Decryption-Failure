param([switch]$ReuseRecovery)

$ErrorActionPreference = 'Stop'
$root = 'results/key-hazard-decomposition'

./scripts/build.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $ReuseRecovery) {
    ./build/key-hazard-recovery.exe --preset n4q29d43 --sample-keys 128 --seed 20260913 --output "$root/recovery/n4q29d43"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    ./build/key-hazard-recovery.exe --preset n4q19d43 --sample-keys 128 --seed 20260913 --output "$root/recovery/n4q19d43"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    ./build/key-hazard-recovery.exe --preset n8q29d43 --sample-keys 128 --sample-y 4 --seed 20260916 --output "$root/recovery/n8q29d43"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

python python/key_hazard_decomposition.py --repo . --root $root
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
