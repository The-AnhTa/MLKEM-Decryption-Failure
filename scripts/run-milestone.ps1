$ErrorActionPreference = 'Stop'
& "$PSScriptRoot\build.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$root = "$PSScriptRoot\..\results"
& "$PSScriptRoot\..\build\toy-mlkem.exe" --preset e1a --frozen-public --output "$root\e1a\public"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& "$PSScriptRoot\..\build\toy-mlkem.exe" --preset e1a --ciphertext-dp --scalable-only `
    --output "$root\e1a\ciphertext"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$public = @('t_norm2', 't_histogram', 't_autocorrelation', 'at_norm_pair',
            'at_pair_histogram', 'at_correlations', 'at_projections')
$ciphertext = @('hist_u', 'hist_v', 'extreme_symbols', 'entropy_1024',
                'decompressed_norms', 'joint_uv_histogram')
foreach ($feature in $public) {
    python "$PSScriptRoot\..\python\analyze.py" "$root\e1a\public" --feature $feature
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
foreach ($feature in $ciphertext) {
    python "$PSScriptRoot\..\python\analyze.py" "$root\e1a\ciphertext" --feature $feature
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

foreach ($preset in @('e2', 'e3', 'e4', 'e5')) {
    & "$PSScriptRoot\..\build\toy-mlkem.exe" --preset $preset --support-bound `
        --output "$root\$preset\certificate"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
python "$PSScriptRoot\..\python\milestone_report.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
