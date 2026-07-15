param(
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$workRoot = Join-Path $projectRoot "work\portable-build"
$outputRoot = Join-Path $projectRoot "outputs"
$portableDir = Join-Path $outputRoot "Conference Recorder"
$archivePath = Join-Path $outputRoot "Conference-Recorder-Portable.zip"
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
    $requiredDirectories = @(
        (Join-Path $portableDir "_runtime"),
        (Join-Path $portableDir "tools")
    )
    foreach ($directory in $requiredDirectories) {
        if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
            throw "Portable package is incomplete. Missing directory: $directory"
        }
    }

    $required = @(
        (Join-Path $portableDir "Conference Recorder.exe"),
        (Join-Path $portableDir "tools\ffmpeg.exe"),
        (Join-Path $portableDir "tools\chrome-audio-capture.exe"),
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
$nativeRoot = Join-Path $workRoot "native"
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

New-Item -ItemType Directory -Force -Path $nativeRoot | Out-Null
$chromeAudioHelper = Join-Path $nativeRoot "chrome-audio-capture.exe"
Write-Host "Building the Chrome process-loopback helper..."
& powershell -NoProfile -ExecutionPolicy Bypass `
    -File (Join-Path $projectRoot "scripts\build-chrome-audio.ps1") `
    -OutputPath $chromeAudioHelper
if ($LASTEXITCODE -ne 0) {
    throw "Chrome audio helper build failed with exit code $LASTEXITCODE."
}

Write-Host "Building the portable Windows executable..."
& $venvPython -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --contents-directory "_runtime" `
    --windowed `
    --noupx `
    --name "Conference Recorder" `
    --paths (Join-Path $projectRoot "src") `
    --distpath $distDir `
    --workpath $buildDir `
    --specpath $specDir `
    (Join-Path $projectRoot "scripts\launcher.py")
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

$bundleDir = Join-Path $distDir "Conference Recorder"
if (-not (Test-Path -LiteralPath $bundleDir -PathType Container)) {
    throw "PyInstaller bundle not found: $bundleDir"
}

Remove-ProjectItem -Path $portableDir
New-Item -ItemType Directory -Force -Path $portableDir | Out-Null
Get-ChildItem -LiteralPath $bundleDir -Force | Copy-Item -Destination $portableDir -Recurse -Force
New-Item -ItemType Directory -Force -Path (Join-Path $portableDir "tools") | Out-Null
Copy-Item -LiteralPath $ffmpegExe.FullName -Destination (Join-Path $portableDir "tools\ffmpeg.exe")
Copy-Item -LiteralPath $chromeAudioHelper -Destination (Join-Path $portableDir "tools\chrome-audio-capture.exe")
Copy-Item -LiteralPath $licensePath -Destination (Join-Path $portableDir "FFMPEG-LICENSE.txt")
Copy-Item -LiteralPath (Join-Path $projectRoot "docs\portable-readme.txt") -Destination (Join-Path $portableDir "LLEGEIX-ME.txt")

$notice = @"
Conference Recorder includes an FFmpeg executable.

Windows build source: $ffmpegUrl
FFmpeg project: https://ffmpeg.org/
Downloaded archive SHA-256: $ffmpegHash
License text: FFMPEG-LICENSE.txt

FFmpeg is a separate program and is not part of the Conference Recorder source code.
"@
Set-Content -LiteralPath (Join-Path $portableDir "FFMPEG-NOTICE.txt") -Value $notice -Encoding UTF8

Assert-PortableLayout
& (Join-Path $portableDir "tools\chrome-audio-capture.exe") --self-test
if ($LASTEXITCODE -ne 0) {
    throw "Chrome audio helper self-test failed with exit code $LASTEXITCODE."
}
$appSelfTest = Start-Process `
    -FilePath (Join-Path $portableDir "Conference Recorder.exe") `
    -ArgumentList "--self-test" `
    -PassThru `
    -Wait `
    -WindowStyle Hidden
if ($appSelfTest.ExitCode -ne 0) {
    throw "Conference Recorder self-test failed with exit code $($appSelfTest.ExitCode)."
}
Remove-ProjectItem -Path $archivePath
Compress-Archive -LiteralPath $portableDir -DestinationPath $archivePath -CompressionLevel Optimal
if (-not (Test-Path -LiteralPath $archivePath -PathType Leaf)) {
    throw "The portable archive was not created."
}

Write-Host "Portable application created: $archivePath"
Write-Host "FFmpeg archive SHA-256: $ffmpegHash"
