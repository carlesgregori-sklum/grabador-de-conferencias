param(
    [Parameter(Mandatory = $true)][string]$OutputPath
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$sourcePath = Join-Path $projectRoot "native\chrome_audio_capture\ChromeAudioCapture.cs"
$compiler = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)
$outputDirectory = Split-Path -Parent $resolvedOutput

if (-not (Test-Path -LiteralPath $compiler -PathType Leaf)) {
    throw "The 64-bit .NET Framework C# compiler was not found: $compiler"
}
if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
    throw "Chrome audio helper source was not found: $sourcePath"
}
if (-not $outputDirectory) {
    throw "OutputPath must include a parent directory."
}

New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
& $compiler /nologo /optimize+ /platform:x64 /target:exe "/out:$resolvedOutput" $sourcePath
if ($LASTEXITCODE -ne 0) {
    throw "Chrome audio helper compilation failed with exit code $LASTEXITCODE."
}
if (-not (Test-Path -LiteralPath $resolvedOutput -PathType Leaf)) {
    throw "Chrome audio helper compilation did not create: $resolvedOutput"
}

Write-Host "Chrome audio helper created: $resolvedOutput"
