# Run from extraction_system. Dependencies and models are downloaded independently.
$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $taskRoot
try {
    $taskPython = Join-Path $taskRoot '.cache/hunflair2/runtime/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $taskPython)) {
        uv venv --python 3.11.16 .cache/hunflair2/runtime
        if ($LASTEXITCODE -ne 0) { throw 'Isolated environment creation failed' }
    }
    uv pip install --python $taskPython --no-deps --cache-dir .cache/uv-independent -r provisioning/hunflair2-requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Isolated dependency provisioning failed' }
    & $taskPython provisioning/provision_models.py
    if ($LASTEXITCODE -ne 0) { throw 'Pinned model provisioning failed' }
} finally { Pop-Location }
