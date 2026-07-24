# Twitch VOD Download Examples

## Basic Download (Highest Quality, Full Video)

```powershell
uv run python download_vod.py --url https://www.twitch.tv/videos/123456789
```

## With Specific Quality

```powershell
uv run python download_vod.py --url https://www.twitch.tv/videos/123456789 --quality 1080p60
```

## With Time Trim

```powershell
uv run python download_vod.py --url https://www.twitch.tv/videos/123456789 --start 00:05:00 --end 00:30:00
```

## Custom Output Path

```powershell
uv run python download_vod.py --url https://www.twitch.tv/videos/123456789 --output D:\clips\highlights.mp4
```

## All Options Combined

```powershell
uv run python download_vod.py --url https://www.twitch.tv/videos/123456789 --quality 720p --start 00:10:00 --end 00:20:00 --output D:\vods --no-gpu
```

## Quiet Mode (For Scripting)

```powershell
$path = uv run python download_vod.py --url https://www.twitch.tv/videos/123456789 --quiet 2>$null
```

## Notes

- Twitch VODs do **not** require authentication
- Common quality options: `1080p60`, `1080p`, `720p`, `480p`, `360p`
- Clips (e.g. `https://clips.twitch.tv/...`) may also work
- GPU acceleration is auto-detected and enabled by default
- The tool auto-selects the highest available quality if `--quality` is omitted or invalid