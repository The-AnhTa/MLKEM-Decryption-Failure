$ErrorActionPreference = 'Stop'
$vswhere = 'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe'
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw 'Visual Studio Installer vswhere.exe was not found.'
}
$installation = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $installation) {
    throw 'Visual Studio C++ Build Tools were not found.'
}
$vcvars = Join-Path $installation 'VC\Auxiliary\Build\vcvars64.bat'
$command = 'call "' + $vcvars + '" >nul && cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release && cmake --build build && ctest --test-dir build --output-on-failure'
& cmd.exe /d /s /c $command
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

