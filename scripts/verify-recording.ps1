param(
    [Parameter(Mandatory = $true)][string]$RecordingPath,
    [Parameter(Mandatory = $true)][string]$FFprobePath,
    [int]$ExpectedWidth = 1920,
    [int]$ExpectedHeight = 1080,
    [int]$ExpectedFps = 30
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $RecordingPath -PathType Leaf)) {
    throw "Recording not found: $RecordingPath"
}
if (-not (Test-Path -LiteralPath $FFprobePath -PathType Leaf)) {
    throw "ffprobe not found: $FFprobePath"
}

$json = & $FFprobePath -v error -show_streams -show_format -of json $RecordingPath | Out-String
if ($LASTEXITCODE -ne 0) {
    throw "ffprobe failed with exit code $LASTEXITCODE."
}
$probe = $json | ConvertFrom-Json
$streams = @($probe.streams)
$video = $streams | Where-Object { $_.codec_type -eq "video" } | Select-Object -First 1
$audio = $streams | Where-Object { $_.codec_type -eq "audio" } | Select-Object -First 1

if ($null -eq $video) { throw "The recording has no video stream." }
if ($video.codec_name -ne "h264") { throw "Expected H.264 video; found $($video.codec_name)." }
if ([int]$video.width -ne $ExpectedWidth -or [int]$video.height -ne $ExpectedHeight) {
    throw "Expected ${ExpectedWidth}x${ExpectedHeight} video; found $($video.width)x$($video.height)."
}
if ($null -eq $audio) { throw "The recording has no audio stream." }
if ($audio.codec_name -ne "aac") { throw "Expected AAC audio; found $($audio.codec_name)." }
if ([double]$probe.format.duration -le 0) { throw "The recording duration is not positive." }

$rateParts = [string]$video.avg_frame_rate -split "/"
if ($rateParts.Count -ne 2 -or [double]$rateParts[1] -eq 0) {
    throw "Invalid average frame rate reported by ffprobe: $($video.avg_frame_rate)"
}
$actualFps = [double]$rateParts[0] / [double]$rateParts[1]
if ([Math]::Abs($actualFps - $ExpectedFps) -gt 1.0) {
    throw "Expected approximately $ExpectedFps FPS; found $actualFps FPS."
}

Write-Host "Recording verified: H.264 ${ExpectedWidth}x${ExpectedHeight} at $ExpectedFps FPS, AAC audio, $($probe.format.duration) seconds."

