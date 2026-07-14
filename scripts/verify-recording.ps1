param(
    [Parameter(Mandatory = $true)][string]$RecordingPath,
    [Parameter(Mandatory = $true)][string]$FFprobePath
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
if ([int]$video.width -ne 1920 -or [int]$video.height -ne 1080) {
    throw "Expected 1920x1080 video; found $($video.width)x$($video.height)."
}
if ($null -eq $audio) { throw "The recording has no audio stream." }
if ($audio.codec_name -ne "aac") { throw "Expected AAC audio; found $($audio.codec_name)." }
if ([double]$probe.format.duration -le 0) { throw "The recording duration is not positive." }

Write-Host "Recording verified: H.264 1920x1080 video, AAC audio, $($probe.format.duration) seconds."

