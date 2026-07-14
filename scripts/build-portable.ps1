param(
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$workRoot = Join-Path $projectRoot "work\portable-build"
$outputRoot = Join-Path $projectRoot "outputs"
$portableDir = Join-Path $outputRoot "Bizneo Recorder"
$archivePath = Join-Path $outputRoot "Bizneo-Recorder-Portable.zip"
$ffmpegUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
$ffmpegLicenseUrl = "https://raw.githubusercontent.com/FFmpeg/FFmpeg/n8.1.2/COPYING.GPLv3"
$pyInstallerVersion = "6.21.0"

function Assert-ProjectPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $prefix = $projectRoot.TrimEnd("\") + "\"
    if (-not $fullPath.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to modify a path outside the project: $fullPath"
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
    $required = @(
        (Join-Path $portableDir "Bizneo Recorder.exe"),
        (Join-Path $portableDir "tools\ffmpeg.exe"),
        (Join-Path $portableDir "FFMPEG-LICENSE.txt"),
        (Join-Path $portableDir "FFMPEG-NOTICE.txt"),
        (Join-Path $portableDir "LLEGEIX-ME.txt")
    )
    foreach ($item in $required) {
        if (-not (Test-Path -LiteralPath $item -PathType Leaf)) {
            throw "Portable package is incomplete. Missing: $item"
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
        throw ("Download failed with exit code {0}: {1}" -f $LASTEXITCODE, $Uri)
    }
    if (-not (Test-Path -LiteralPath $Destination -PathType Leaf) -or (Get-Item -LiteralPath $Destination).Length -eq 0) {
        throw "Download produced an empty file: $Uri"
    }
}

if ($ValidateOnly) {
    Assert-PortableLayout
    Write-Host "Portable package layout is complete."
    exit 0
}

New-Item -ItemType Directory -Force -Path $workRoot, $outputRoot | Out-Null
$downloadDir = Join-Path $workRoot "downloads"
$extractDir = Join-Path $workRoot "ffmpeg"
$pyInstallerRoot = Join-Path $workRoot "pyinstaller"
$venvDir = Join-Path $workRoot "build-venv"
New-Item -ItemType Directory -Force -Path $downloadDir | Out-Null

$ffmpegArchive = Join-Path $downloadDir "ffmpeg-release-essentials.zip"
if (
    -not (Test-Path -LiteralPath $ffmpegArchive -PathType Leaf) -or
    (Get-Item -LiteralPath $ffmpegArchive).Length -eq 0
) {
    Write-Host "Downloading FFmpeg from the Windows build linked by ffmpeg.org..."
    Invoke-Download -Uri $ffmpegUrl -Destination $ffmpegArchive
}
$ffmpegHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $ffmpegArchive).Hash

Remove-ProjectItem -Path $extractDir
New-Item -ItemType Directory -Force -Path $extractDir | Out-Null
Expand-Archive -LiteralPath $ffmpegArchive -DestinationPath $extractDir -Force
$ffmpegExe = Get-ChildItem -LiteralPath $extractDir -Recurse -Filter "ffmpeg.exe" -File | Select-Object -First 1
if ($null -eq $ffmpegExe) {
    throw "The downloaded FFmpeg archive does not contain ffmpeg.exe."
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

Write-Host "Building the portable Windows executable..."
& $venvPython -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --noupx `
    --name "Bizneo Recorder" `
    --paths (Join-Path $projectRoot "src") `
    --distpath $distDir `
    --workpath $buildDir `
    --specpath $specDir `
    (Join-Path $projectRoot "scripts\launcher.py")
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

Remove-ProjectItem -Path $portableDir
New-Item -ItemType Directory -Force -Path (Join-Path $portableDir "tools") | Out-Null
Copy-Item -LiteralPath (Join-Path $distDir "Bizneo Recorder.exe") -Destination $portableDir
Copy-Item -LiteralPath $ffmpegExe.FullName -Destination (Join-Path $portableDir "tools\ffmpeg.exe")
Copy-Item -LiteralPath $licensePath -Destination (Join-Path $portableDir "FFMPEG-LICENSE.txt")
Copy-Item -LiteralPath (Join-Path $projectRoot "docs\portable-readme.txt") -Destination (Join-Path $portableDir "LLEGEIX-ME.txt")

$notice = @"
Bizneo Recorder includes an FFmpeg executable.

Windows build source: $ffmpegUrl
FFmpeg project: https://ffmpeg.org/
Downloaded archive SHA-256: $ffmpegHash
License text: FFMPEG-LICENSE.txt

FFmpeg is a separate program and is not part of the Bizneo Recorder source code.
"@
Set-Content -LiteralPath (Join-Path $portableDir "FFMPEG-NOTICE.txt") -Value $notice -Encoding UTF8

Assert-PortableLayout
Remove-ProjectItem -Path $archivePath
Compress-Archive -LiteralPath $portableDir -DestinationPath $archivePath -CompressionLevel Optimal
if (-not (Test-Path -LiteralPath $archivePath -PathType Leaf)) {
    throw "The portable archive was not created."
}

Write-Host "Portable application created: $archivePath"
Write-Host "FFmpeg archive SHA-256: $ffmpegHash"
