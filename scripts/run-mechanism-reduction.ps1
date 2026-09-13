param(
    [switch]$ReuseData
)

$ErrorActionPreference = 'Stop'
$root = 'results/mechanism-reduction'

./scripts/build.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $ReuseData) {
    ./build/toy-mlkem.exe --preset e0 --ciphertext-dp --mechanism-reduction `
        --output "$root/data/e0"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    ./build/toy-mlkem.exe --preset e1a --ciphertext-dp --mechanism-reduction `
        --output "$root/data/e1a"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    ./build/toy-mlkem.exe --preset n4q29d43 --sample-keys 128 --seed 20260913 `
        --mechanism-reduction --output "$root/data/n4q29d43"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    ./build/toy-mlkem.exe --preset n4q19d43 --sample-keys 128 --seed 20260913 `
        --mechanism-reduction --output "$root/data/n4q19d43"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

python python/mechanism_reduction.py train --e0 "$root/data/e0" `
    --baseline-artifact results/frozen-normalized-transfer/frozen-score.json `
    --output "$root/frozen-config.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python python/mechanism_reduction.py evaluate --root $root `
    --config "$root/frozen-config.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

foreach ($dataset in @('n4q29d43', 'n4q19d43')) {
    foreach ($name in @('mechanism_margin.csv', 'mechanism_margin_by_key.csv')) {
        $source = "$root/data/$dataset/$name"
        if (Test-Path -LiteralPath $source) {
            python python/compress_result.py $source --remove-source
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        }
        $archive = "$source.gz"
        if ((Test-Path -LiteralPath $archive) -and
            ((Get-Item -LiteralPath $archive).Length -ge 100000000)) {
            python python/split_result.py $archive --remove-source
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        }
    }
}
