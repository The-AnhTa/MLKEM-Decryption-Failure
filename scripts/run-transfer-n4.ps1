$ErrorActionPreference = 'Stop'
& "$PSScriptRoot\build.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$root = "$PSScriptRoot\..\results"
$model = "$root\predicate-transfer\e0-model.json"
$expectedModelHash = '45A24137F5D1D6B3F6C18220008D138DA64091A918042DFF2AD53BEF87E3946C'
if ((Get-FileHash -LiteralPath $model -Algorithm SHA256).Hash -ne $expectedModelHash) {
    throw 'The frozen E0 predicate model hash does not match the predeclared model.'
}

python "$PSScriptRoot\..\python\predicate_transfer.py" evaluate --model $model `
    --target "$root\e1a" --output "$root\predicate-transfer\e1a-evaluation.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$presets = @(
    'n4q17d32', 'n4q17d42', 'n4q17d43',
    'n4q19d32', 'n4q19d42', 'n4q19d43',
    'n4q23d32', 'n4q23d42', 'n4q23d43',
    'n4q29d32', 'n4q29d42', 'n4q29d43'
)
foreach ($preset in $presets) {
    & "$PSScriptRoot\..\build\toy-mlkem.exe" --preset $preset --support-bound `
        --output "$root\n4-grid\$preset\certificate"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & "$PSScriptRoot\..\build\toy-mlkem.exe" --preset $preset --screen-keys 12 `
        --seed 20260912 --output "$root\n4-grid\$preset\pilot"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
python "$PSScriptRoot\..\python\n4_screen.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$selected = (Get-Content -Raw "$root\n4-grid\screening.json" | ConvertFrom-Json).selected
$publicFeatures = @('at_norm_pair', 'at_pair_histogram', 'at_correlations', 'at_projections')
$ciphertextFeatures = @('hist_u', 'hist_v', 'extreme_symbols', 'entropy_1024', 'decompressed_norms')
foreach ($preset in $selected) {
    $directory = "$root\n4-grid\$preset"
    & "$PSScriptRoot\..\build\toy-mlkem.exe" --preset $preset --sample-keys 128 `
        --seed 20260913 --output "$directory\final-public"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & "$PSScriptRoot\..\build\toy-mlkem.exe" --preset $preset --sample-keys 128 `
        --seed 20260913 --scalable-only --output "$directory\final-ciphertext"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    foreach ($feature in $publicFeatures) {
        python "$PSScriptRoot\..\python\analyze.py" "$directory\final-public" --feature $feature
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    foreach ($feature in $ciphertextFeatures) {
        python "$PSScriptRoot\..\python\analyze.py" "$directory\final-ciphertext" --feature $feature
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    python "$PSScriptRoot\..\python\analyze.py" "$directory\final-ciphertext" `
        --feature joint_uv_histogram --summary-only
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    python "$PSScriptRoot\..\python\predicate_transfer.py" evaluate --model $model `
        --target $directory --output "$directory\e0-transfer.json"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    python "$PSScriptRoot\..\python\sampled_key_ci.py" "$directory\final-public"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    python "$PSScriptRoot\..\python\compress_result.py" `
        "$directory\final-ciphertext\joint_uv_histogram.csv" --remove-source
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

python "$PSScriptRoot\..\python\dimension_report.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
