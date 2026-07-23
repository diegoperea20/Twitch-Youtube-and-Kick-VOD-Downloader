---
name: downloadvods
description: >
  Skill for downloading VODs and videos from Twitch, Kick, and YouTube using the
  project's CLI tool (download_vod.py). Handles quality selection, time-range
  trimming, GPU acceleration detection, and YouTube cookie authentication.
---

# downloadvods — VOD Downloader (CLI)

## Description

Downloads videos from **Twitch**, **Kick**, and **YouTube** as H.264 MP4 files using `yt-dlp` and `ffmpeg`. Provides full control over quality, time range, GPU acceleration, and output path.

## When to Use

- User wants to download a VOD/clip from **Twitch**
- User wants to download a video from **Kick**
- User wants to download a **YouTube** video (may require `--browser`)
- User needs a specific segment of a video (trim start/end)
- User wants the highest available quality automatically
- User wants GPU-accelerated encoding for faster processing

## Usage

```powershell
uv run python download_vod.py --url <URL> [options]
```

Always use `uv run python` to execute within the project's virtual environment.

> **PowerShell note:** URLs containing `&` (e.g. YouTube with `&list=...`) **must** be enclosed in double quotes (`"url"`). PowerShell treats unquoted `&` as a special character.

## Parameters

| Argument | Required | Default | Description |
|---|---|---|---|
| `--url` | Yes | — | Video URL (Twitch, Kick, or YouTube) |
| `--quality` | No | `best` | Video quality: `1080p60`, `720p`, `best`. Invalid → best |
| `--start` | No | `0` | Start time in seconds or `HH:MM:SS` |
| `--end` | No | `0` | End time in seconds or `HH:MM:SS` (`0` = full video) |
| `--no-gpu` | No | off | Disable GPU acceleration (auto-detected by default) |
| `--output` / `-o` | No | `.` | Output path: file `.mp4` or directory |
| `--browser` | No | — | Browser for YouTube cookies: `chrome`, `firefox`, `edge`, `brave`, `chromium`, `opera`, `vivaldi`, `safari` |
| `--quiet` / `-q` | No | off | Suppress all progress output (errors still shown) |

## Default Behavior

When called with only `--url`:
- Highest available quality is selected
- Entire video is downloaded
- GPU acceleration is auto-detected and enabled if available
- Output is saved to the current directory as `{title}_{start}_{end}.mp4`

## Examples

### Basic download (all defaults)
```powershell
uv run python download_vod.py --url https://www.twitch.tv/videos/123456789
```

### YouTube with quality and time trim
```powershell
uv run python download_vod.py --url "https://youtube.com/watch?v=xxxx&list=...&start_radio=1" --quality 1080p --start 00:05:00 --end 00:10:00
```

### Specific output path, no GPU
```powershell
uv run python download_vod.py --url https://kick.com/video/xxx --output D:\videos\clip.mp4 --no-gpu
```

### YouTube with browser cookies (required for many videos)
```powershell
uv run python download_vod.py --url "https://youtube.com/watch?v=xxxx" --browser chrome
```

### Capture output path in a variable (quiet mode)
```powershell
$path = uv run python download_vod.py --url <URL> --quiet 2>$null
```

## Platform-Specific Notes

- **Twitch**: Works without authentication for VODs. Clips may also work.
- **Kick**: Works without authentication.
- **YouTube**: Most videos require `--browser` with a browser where YouTube is logged in. Close the browser completely before running to release cookie locks.

## Troubleshooting

| Symptom | Solution |
|---|---|
| "YouTube may require authentication" | Use `--browser chrome` (or firefox, edge) |
| "no GPU encoder detected" | Ensure FFmpeg is installed with GPU support. Falls back to CPU automatically |
| "Download failed: HTTP Error 403" | YouTube blocking — use `--browser` flag |
| `ffmpeg` not found | Install FFmpeg: `winget install Gyan.FFmpeg` |

## Integration

This skill works with the project at `C:\Users\user\Documents\downloadvods`. The CLI is self-contained in `download_vod.py` and does not depend on `app.py`. Modifying one does not affect the other.
