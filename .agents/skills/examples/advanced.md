# Advanced Usage Examples

## GPU Acceleration Control

GPU is auto-detected and enabled by default. To disable it:

```powershell
uv run python download_vod.py --url https://www.twitch.tv/videos/123456789 --no-gpu
```

To explicitly see GPU detection output (omit `--quiet`):

```powershell
uv run python download_vod.py --url https://www.twitch.tv/videos/123456789
# Output will show: "GPU acceleration: NVIDIA NVENC" or "Note: no GPU encoder detected, using CPU"
```

Supported GPU encoders: `h264_nvenc` (NVIDIA), `h264_amf` (AMD), `h264_vaapi` / `h264_qsv` (Intel).

## Scripting — Capture Output Path

All progress goes to **stderr**. Only the final `Saved: <path>` goes to **stdout**.

```powershell
# Capture the saved file path
$path = uv run python download_vod.py --url <URL> --quiet 2>$null
echo "Downloaded to: $path"

# Use the path in further commands
if ($path) {
    & "C:\Program Files\VideoLAN\VLC\vlc.exe" $path
}
```

## Upload to YouTube Shorts Format

Trim a 15-60 second segment for YouTube Shorts (vertical 1080x1920):

```powershell
uv run python download_vod.py --url "https://www.twitch.tv/videos/123456789" --start 00:10:00 --end 00:10:30 --output D:\clips\shorts_source.mp4
# Then use ffmpeg to crop to 9:16:
# ffmpeg -i D:\clips\shorts_source.mp4 -vf "crop=ih*9/16:ih" -c:a copy D:\clips\shorts_final.mp4
```

## File Exists — Automatic Deduplication

If the output file already exists, the tool appends `_1`, `_2`, etc.:

```powershell
# First run creates: My_Video_00-05-00_00-10-00.mp4
# Second run creates: My_Video_00-05-00_00-10-00_1.mp4
uv run python download_vod.py --url <URL> --start 00:05:00 --end 00:10:00
uv run python download_vod.py --url <URL> --start 00:05:00 --end 00:10:00
```

## Quality Fallback

If the requested quality is not available, the highest available is used:

```powershell
# If 4k is unavailable, falls back to highest (e.g. 1080p60)
uv run python download_vod.py --url <URL> --quality 4k
# Output: "Quality '4k' not available. Using highest: 1080p60"
```

## Mixed Platform Notes

- **Twitch/Kick**: Trimming is done server-side via yt-dlp's external_downloader
- **YouTube**: Trimming is done post-download via ffmpeg (may need transcode)
- **YouTube non-H.264**: If source is VP9/AV1, ffmpeg transcodes to H.264 automatically