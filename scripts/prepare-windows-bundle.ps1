# Monta o runtime portátil empacotado pelo instalador do Tauri:
# Python embeddable + yt-dlp, FFmpeg e Node.js, além dos scripts em src/.
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Resources = Join-Path $RepoRoot "apps\desktop\src-tauri\resources"
$SrcOut = Join-Path $Resources "src"
$PythonDir = Join-Path $Resources "python"
$BinDir = Join-Path $Resources "bin"
$Cache = Join-Path $env:TEMP "downloader-pro-bundle"

$PythonZipUrl = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip"
$GetPipUrl = "https://bootstrap.pypa.io/get-pip.py"
$FfmpegZipUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
$NodeZipUrl = "https://nodejs.org/dist/v22.14.0/node-v22.14.0-win-x64.zip"

function Get-File($Url, $Destination) {
    Write-Host "Baixando $Url"
    Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing
}

New-Item -ItemType Directory -Force -Path $SrcOut, $PythonDir, $BinDir, $Cache | Out-Null

Write-Host "Copiando scripts Python"
Get-ChildItem (Join-Path $RepoRoot "src") -Filter "*.py" | Copy-Item -Destination $SrcOut -Force

$PythonExe = Join-Path $PythonDir "python.exe"
$Stamp = Join-Path $PythonDir ".bundle-stamp"
$Requirements = Join-Path $RepoRoot "requirements.txt"
$sha = [System.Security.Cryptography.SHA256]::Create()
$ReqHash = [System.BitConverter]::ToString($sha.ComputeHash([System.IO.File]::ReadAllBytes($Requirements))).Replace("-", "")

if (-not (Test-Path $PythonExe)) {
    $zip = Join-Path $Cache "python-embed.zip"
    if (-not (Test-Path $zip)) { Get-File $PythonZipUrl $zip }
    Write-Host "Extraindo Python"
    Expand-Archive -Path $zip -DestinationPath $PythonDir -Force
}

$Pth = Get-ChildItem $PythonDir -Filter "python*._pth" | Select-Object -First 1
if (-not $Pth) { throw "python*._pth não encontrado em $PythonDir" }
$pthLines = @(Get-Content $Pth.FullName | ForEach-Object { $_ -replace '^\s*#\s*import site\s*$', 'import site' })
if ($pthLines -notcontains "Lib\site-packages") { $pthLines += "Lib\site-packages" }
if ($pthLines -notcontains "import site") { $pthLines += "import site" }
Set-Content -Path $Pth.FullName -Value $pthLines -Encoding ascii

$NeedsPip = -not (Test-Path $Stamp) -or ((Get-Content $Stamp -Raw).Trim() -ne $ReqHash)
if ($NeedsPip) {
    $getPip = Join-Path $Cache "get-pip.py"
    if (-not (Test-Path $getPip)) { Get-File $GetPipUrl $getPip }
    Write-Host "Instalando pip e dependências"
    & $PythonExe $getPip
    if ($LASTEXITCODE -ne 0) { throw "get-pip falhou ($LASTEXITCODE)" }
    & $PythonExe -m pip install --upgrade -r $Requirements
    if ($LASTEXITCODE -ne 0) { throw "pip install falhou ($LASTEXITCODE)" }
    Set-Content -Path $Stamp -Value $ReqHash -Encoding ascii
}

$Ffmpeg = Join-Path $BinDir "ffmpeg.exe"
$Ffprobe = Join-Path $BinDir "ffprobe.exe"
if (-not (Test-Path $Ffmpeg) -or -not (Test-Path $Ffprobe)) {
    $zip = Join-Path $Cache "ffmpeg.zip"
    if (-not (Test-Path $zip)) { Get-File $FfmpegZipUrl $zip }
    $extract = Join-Path $Cache "ffmpeg"
    if (Test-Path $extract) { Remove-Item -Recurse -Force $extract }
    Write-Host "Extraindo FFmpeg"
    Expand-Archive -Path $zip -DestinationPath $extract -Force
    Copy-Item (Get-ChildItem $extract -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1).FullName $Ffmpeg -Force
    Copy-Item (Get-ChildItem $extract -Recurse -Filter "ffprobe.exe" | Select-Object -First 1).FullName $Ffprobe -Force
}

$Node = Join-Path $BinDir "node.exe"
if (-not (Test-Path $Node)) {
    $zip = Join-Path $Cache "node.zip"
    if (-not (Test-Path $zip)) { Get-File $NodeZipUrl $zip }
    $extract = Join-Path $Cache "node"
    if (Test-Path $extract) { Remove-Item -Recurse -Force $extract }
    Write-Host "Extraindo Node.js"
    Expand-Archive -Path $zip -DestinationPath $extract -Force
    Copy-Item (Get-ChildItem $extract -Recurse -Filter "node.exe" | Select-Object -First 1).FullName $Node -Force
}

& $PythonExe -c "import yt_dlp; print('yt-dlp', yt_dlp.version.__version__)"
if ($LASTEXITCODE -ne 0) { throw "yt-dlp não importou no Python portátil" }

Write-Host "Runtime portátil pronto em $Resources"
