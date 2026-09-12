$ErrorActionPreference = 'Stop'
& "$PSScriptRoot\build.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

foreach ($mode in @('none', 'no-compression', 'independent-compression')) {
    & "$PSScriptRoot\..\build\toy-mlkem.exe" --preset e0 --mode $mode --output "$PSScriptRoot\..\results\e0\$mode"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    foreach ($feature in @('pk', 't_norm2', 't_histogram', 't_autocorrelation', 'at_norm_pair',
                            'at_pair_histogram', 'at_correlations', 'at_projections', 'secret_key')) {
        python "$PSScriptRoot\..\python\analyze.py" "$PSScriptRoot\..\results\e0\$mode" --feature $feature
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

python "$PSScriptRoot\..\python\conditional_independence.py" "$PSScriptRoot\..\results\e0\none"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python "$PSScriptRoot\..\python\analyze.py" "$PSScriptRoot\..\results\e0\none" --feature pk `
    --derive-independent-output "$PSScriptRoot\..\results\e0\independent-output"
foreach ($feature in @('pk', 't_norm2', 't_histogram', 't_autocorrelation')) {
    python "$PSScriptRoot\..\python\analyze.py" "$PSScriptRoot\..\results\e0\independent-output" --feature $feature
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& "$PSScriptRoot\..\build\toy-mlkem.exe" --preset e0 --mode none --ciphertext-dp `
    --output "$PSScriptRoot\..\results\e0\ciphertext-none"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
foreach ($feature in @('ciphertext', 'ciphertext_symbols', 'hist_u', 'hist_v', 'extreme_symbols',
                        'entropy_1024', 'decompressed_norms', 'joint_uv_histogram')) {
    python "$PSScriptRoot\..\python\analyze.py" "$PSScriptRoot\..\results\e0\ciphertext-none" --feature $feature
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
python "$PSScriptRoot\..\python\analyze.py" "$PSScriptRoot\..\results\e0\ciphertext-none" `
    --feature pk_ciphertext --summary-only
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python "$PSScriptRoot\..\python\compress_result.py" `
    "$PSScriptRoot\..\results\e0\ciphertext-none\pk_ciphertext.csv" --remove-source
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& "$PSScriptRoot\..\build\toy-mlkem.exe" --preset e0 --mode no-compression --ciphertext-dp `
    --output "$PSScriptRoot\..\results\e0\ciphertext-no-compression"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python "$PSScriptRoot\..\python\analyze.py" "$PSScriptRoot\..\results\e0\ciphertext-no-compression" --feature ciphertext
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python "$PSScriptRoot\..\python\analyze.py" "$PSScriptRoot\..\results\e0\ciphertext-no-compression" `
    --feature pk_ciphertext --summary-only
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Remove-Item -LiteralPath "$PSScriptRoot\..\results\e0\ciphertext-no-compression\pk_ciphertext.csv" -Force

python "$PSScriptRoot\..\python\summarize_matrix.py" "$PSScriptRoot\..\results\e0"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
