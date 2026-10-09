# Сборка веб-панели gkbridge под принтер (armv7 Linux) + бандл в приложение.
# Запуск из папки webpanel:  .\build.ps1
$ErrorActionPreference = "Stop"

$go = (Get-Command go -ErrorAction Stop).Source
$here = $PSScriptRoot
$repoResources = Join-Path $here "..\win\pyqt6\resources"

Push-Location $here
try {
    $env:GOOS = "linux"; $env:GOARCH = "arm"; $env:GOARM = "7"

    & $go vet .
    if ($LASTEXITCODE -ne 0) { throw "go vet failed" }

    & $go build -ldflags="-s -w" -o gkbridge .
    if ($LASTEXITCODE -ne 0) { throw "go build failed" }

    $ver = (Get-Content (Join-Path $here "gkbridge.version") -Raw).Trim()
    $size = [math]::Round((Get-Item (Join-Path $here "gkbridge")).Length / 1MB, 2)
    Write-Host "OK: gkbridge v$ver собран ($size МБ, armv7)" -ForegroundColor Green
    Write-Host "Для выпуска обновления подними gkbridge.version, собери бинарник и закоммить оба файла."
}
finally {
    Pop-Location
}
