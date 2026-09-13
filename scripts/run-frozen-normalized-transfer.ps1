param(
    [switch]$ReuseData
)

$ErrorActionPreference = 'Stop'
$root = 'results/frozen-normalized-transfer'

./scripts/build.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $ReuseData) {
    ./build/toy-mlkem.exe --preset e0 --ciphertext-dp --normalized-transfer `
        --output "$root/data/e0"
    ./build/toy-mlkem.exe --preset e1a --ciphertext-dp --normalized-transfer `
        --output "$root/data/e1a"
    ./build/toy-mlkem.exe --preset n4q29d43 --sample-keys 128 --seed 20260913 `
        --scalable-only --normalized-transfer --output "$root/data/n4q29d43"
    ./build/toy-mlkem.exe --preset n4q19d43 --sample-keys 128 --seed 20260913 `
        --scalable-only --normalized-transfer --output "$root/data/n4q19d43"
}

python python/frozen_normalized_transfer.py train --e0 "$root/data/e0" `
    --output "$root/frozen-score.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python python/frozen_normalized_transfer.py evaluate --root $root `
    --artifact "$root/frozen-score.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

foreach ($dataset in @('n4q29d43', 'n4q19d43')) {
    $source = "$root/data/$dataset/normalized_uv_margin_by_key.csv"
    if (Test-Path -LiteralPath $source) {
        python python/compress_result.py $source --remove-source
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}
