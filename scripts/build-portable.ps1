param(
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$workRoot = Join-Path $projectRoot "work\portable-build"
$outputRoot = Join-Path $projectRoot "outputs"
$portableDir = Join-Path $outputRoot "Grabador de conferencias"
$archivePath = Join-Path $outputRoot "Grabador-de-conferencias-Portable.zip"
$ffmpegUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
$ffmpegLicenseUrl = "https://raw.githubusercontent.com/FFmpeg/FFmpeg/n8.1.2/COPYING.GPLv3"
$pyInstallerVersion = "6.21.0"

function Assert-ProjectPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $prefix = $projectRoot.TrimEnd("\") + "\"
    if (-not $fullPath.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Se ha rechazado una ruta fuera del proyecto: $fullPath"
    }
}

function Remove-ProjectItem {
    param([Parameter(Mandatory = $true)][string]$Path)
    Assert-ProjectPath -Path $Path
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
}

function Assert-PortableLayout {
    $requiredDirectories = @(
        (Join-Path $portableDir "_runtime"),
        (Join-Path $portableDir "tools")
    )
    foreach ($directory in $requiredDirectories) {
        if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
            throw "El paquete portable está incompleto. Falta la carpeta: $directory"
        }
    }

    $required = @(
        (Join-Path $portableDir "Grabador de conferencias.exe"),
        (Join-Path $portableDir "_runtime\bizneo_recorder\assets\browser_capture.html"),
        (Join-Path $portableDir "tools\ffmpeg.exe"),
        (Join-Path $portableDir "tools\chrome-audio-capture.exe"),
        (Join-Path $portableDir "FFMPEG-LICENSE.txt"),
        (Join-Path $portableDir "FFMPEG-NOTICE.txt"),
        (Join-Path $portableDir "LEEME.txt")
    )
    foreach ($item in $required) {
        if (-not (Test-Path -LiteralPath $item -PathType Leaf)) {
            throw "El paquete portable está incompleto. Falta: $item"
        }
    }
}

function Invoke-Download {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][string]$Destination
    )
    & curl.exe --fail --location --silent --show-error --ssl-revoke-best-effort --output $Destination $Uri
    if ($LASTEXITCODE -ne 0) {
        Remove-ProjectItem -Path $Destination
        throw ("La descarga falló con el código {0}: {1}" -f $LASTEXITCODE, $Uri)
    }
    if (-not (Test-Path -LiteralPath $Destination -PathType Leaf) -or (Get-Item -LiteralPath $Destination).Length -eq 0) {
        throw "La descarga produjo un archivo vacío: $Uri"
    }
}

if ($ValidateOnly) {
    Assert-PortableLayout
    Write-Host "La estructura del paquete portable está completa."
    exit 0
}

New-Item -ItemType Directory -Force -Path $workRoot, $outputRoot | Out-Null
$downloadDir = Join-Path $workRoot "downloads"
$extractDir = Join-Path $workRoot "ffmpeg"
$pyInstallerRoot = Join-Path $workRoot "pyinstaller"
$nativeRoot = Join-Path $workRoot "native"
$venvDir = Join-Path $workRoot "build-venv"
New-Item -ItemType Directory -Force -Path $downloadDir | Out-Null

$ffmpegArchive = Join-Path $downloadDir "ffmpeg-release-essentials.zip"
if (
    -not (Test-Path -LiteralPath $ffmpegArchive -PathType Leaf) -or
    (Get-Item -LiteralPath $ffmpegArchive).Length -eq 0
) {
    Write-Host "Descargando la compilación de FFmpeg enlazada por ffmpeg.org..."
    Invoke-Download -Uri $ffmpegUrl -Destination $ffmpegArchive
}
$ffmpegHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $ffmpegArchive).Hash

Remove-ProjectItem -Path $extractDir
New-Item -ItemType Directory -Force -Path $extractDir | Out-Null
Expand-Archive -LiteralPath $ffmpegArchive -DestinationPath $extractDir -Force
$ffmpegExe = Get-ChildItem -LiteralPath $extractDir -Recurse -Filter "ffmpeg.exe" -File | Select-Object -First 1
if ($null -eq $ffmpegExe) {
    throw "El archivo descargado de FFmpeg no contiene ffmpeg.exe."
}

$licensePath = Join-Path $downloadDir "FFMPEG-LICENSE.txt"
if (-not (Test-Path -LiteralPath $licensePath -PathType Leaf)) {
    Invoke-Download -Uri $ffmpegLicenseUrl -Destination $licensePath
}

$venvPython = Join-Path $venvDir "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    python -m venv $venvDir
}
& $venvPython -m pip install --disable-pip-version-check --quiet "pyinstaller==$pyInstallerVersion"

Remove-ProjectItem -Path $pyInstallerRoot
New-Item -ItemType Directory -Force -Path $pyInstallerRoot | Out-Null
$distDir = Join-Path $pyInstallerRoot "dist"
$buildDir = Join-Path $pyInstallerRoot "build"
$specDir = Join-Path $pyInstallerRoot "spec"
New-Item -ItemType Directory -Force -Path $distDir, $buildDir, $specDir | Out-Null

New-Item -ItemType Directory -Force -Path $nativeRoot | Out-Null
$chromeAudioHelper = Join-Path $nativeRoot "chrome-audio-capture.exe"
Write-Host "Compilando el capturador de audio de Chrome por proceso..."
& powershell -NoProfile -ExecutionPolicy Bypass `
    -File (Join-Path $projectRoot "scripts\build-chrome-audio.ps1") `
    -OutputPath $chromeAudioHelper
if ($LASTEXITCODE -ne 0) {
    throw "La compilación del capturador de Chrome falló con el código $LASTEXITCODE."
}

Write-Host "Construyendo el ejecutable portable para Windows..."
& $venvPython -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --contents-directory "_runtime" `
    --windowed `
    --noupx `
    --name "Grabador de conferencias" `
    --paths (Join-Path $projectRoot "src") `
    --add-data "$projectRoot\src\bizneo_recorder\assets;bizneo_recorder\assets" `
    --distpath $distDir `
    --workpath $buildDir `
    --specpath $specDir `
    (Join-Path $projectRoot "scripts\launcher.py")
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller falló con el código $LASTEXITCODE."
}

$bundleDir = Join-Path $distDir "Grabador de conferencias"
if (-not (Test-Path -LiteralPath $bundleDir -PathType Container)) {
    throw "No se encontró el paquete de PyInstaller: $bundleDir"
}

Remove-ProjectItem -Path $portableDir
New-Item -ItemType Directory -Force -Path $portableDir | Out-Null
Get-ChildItem -LiteralPath $bundleDir -Force | Copy-Item -Destination $portableDir -Recurse -Force
New-Item -ItemType Directory -Force -Path (Join-Path $portableDir "tools") | Out-Null
Copy-Item -LiteralPath $ffmpegExe.FullName -Destination (Join-Path $portableDir "tools\ffmpeg.exe")
Copy-Item -LiteralPath $chromeAudioHelper -Destination (Join-Path $portableDir "tools\chrome-audio-capture.exe")
Copy-Item -LiteralPath $licensePath -Destination (Join-Path $portableDir "FFMPEG-LICENSE.txt")
Copy-Item -LiteralPath (Join-Path $projectRoot "docs\portable-readme.txt") -Destination (Join-Path $portableDir "LEEME.txt")

$notice = @"
Grabador de conferencias incluye un ejecutable de FFmpeg.

Fuente de la compilación para Windows: $ffmpegUrl
Proyecto FFmpeg: https://ffmpeg.org/
SHA-256 del archivo descargado: $ffmpegHash
Texto de la licencia: FFMPEG-LICENSE.txt

FFmpeg es un programa independiente y no forma parte del código fuente del Grabador de conferencias.
"@
Set-Content -LiteralPath (Join-Path $portableDir "FFMPEG-NOTICE.txt") -Value $notice -Encoding UTF8

Assert-PortableLayout
& (Join-Path $portableDir "tools\chrome-audio-capture.exe") --self-test
if ($LASTEXITCODE -ne 0) {
    throw "El autodiagnóstico del capturador de Chrome falló con el código $LASTEXITCODE."
}
$appSelfTest = Start-Process `
    -FilePath (Join-Path $portableDir "Grabador de conferencias.exe") `
    -ArgumentList "--self-test" `
    -PassThru `
    -Wait `
    -WindowStyle Hidden
if ($appSelfTest.ExitCode -ne 0) {
    throw "El autodiagnóstico del Grabador de conferencias falló con el código $($appSelfTest.ExitCode)."
}
Remove-ProjectItem -Path $archivePath
Compress-Archive -LiteralPath $portableDir -DestinationPath $archivePath -CompressionLevel Optimal
if (-not (Test-Path -LiteralPath $archivePath -PathType Leaf)) {
    throw "No se creó el archivo ZIP portable."
}

Write-Host "Aplicación portable creada: $archivePath"
Write-Host "SHA-256 del archivo de FFmpeg: $ffmpegHash"
