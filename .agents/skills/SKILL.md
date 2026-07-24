---
name: downloadvods
description: >
  Skill for downloading VODs and videos from Twitch, Kick, and YouTube using the
  project's CLI tool (download_vod.py). Handles quality selection, time-range
  trimming, GPU acceleration detection, and YouTube cookie authentication.
tools:
  download-vod:
    description: >
      Download a video from Twitch, Kick, or YouTube with default settings
      (highest quality, full duration, GPU auto-detected).
    command: uv run python download_vod.py --url <url>
    arguments:
      url:
        description: "Video URL (Twitch, Kick, or YouTube)"
        required: true
  download-vod-with-options:
    description: >
      Download a video with full control over quality, time range, GPU
      acceleration, output path, and browser cookies for YouTube.
    command: uv run python download_vod.py --url <url> [--quality <quality>] [--start <start>] [--end <end>] [--no-gpu] [--output <output>] [--browser <browser>] [--quiet]
    arguments:
      url:
        description: "Video URL (Twitch, Kick, or YouTube)"
        required: true
      quality:
        description: "Quality: 1080p60, 1080p, 720p, 480p, 360p, or best"
        required: false
      start:
        description: "Start time in seconds or HH:MM:SS"
        required: false
      end:
        description: "End time in seconds or HH:MM:SS (0 = full video)"
        required: false
      no-gpu:
        description: "Disable GPU acceleration (default: auto-detected)"
        type: boolean
        required: false
      output:
        description: "Output file (.mp4) or directory"
        required: false
      browser:
        description: "Browser for YouTube cookies: chrome, firefox, edge, brave, chromium, opera, vivaldi, safari"
        required: false
      quiet:
        description: "Suppress progress output"
        type: boolean
        required: false
  download-vod-youtube:
    description: >
      Download a YouTube video with browser-based cookie authentication.
      Use when user wants YouTube download. Most YouTube videos require
      --browser for HD quality. URL must be quoted if it contains &.
    command: uv run python download_vod.py --url "<url>" --browser <browser> [--quality <quality>] [--start <start>] [--end <end>] [--no-gpu] [--output <output>] [--quiet]
    arguments:
      url:
        description: "YouTube video URL (must be double-quoted if contains &)"
        required: true
      browser:
        description: "Browser with YouTube logged-in session: chrome, firefox, edge, brave"
        required: true
      quality:
        description: "Quality: 1080p, 720p, 480p, or best"
        required: false
      start:
        description: "Start time in seconds or HH:MM:SS"
        required: false
      end:
        description: "End time in seconds or HH:MM:SS"
        required: false
      no-gpu:
        description: "Disable GPU acceleration"
        type: boolean
        required: false
      output:
        description: "Output file (.mp4) or directory"
        required: false
      quiet:
        description: "Suppress progress output"
        type: boolean
        required: false
  download-vod-trim:
    description: >
      Download only a segment of a video by specifying start and end times.
      Extracts clips without manual post-processing.
    command: uv run python download_vod.py --url <url> --start <start> --end <end> [--quality <quality>] [--no-gpu] [--output <output>] [--browser <browser>] [--quiet]
    arguments:
      url:
        description: "Video URL"
        required: true
      start:
        description: "Start time in seconds or HH:MM:SS"
        required: true
      end:
        description: "End time in seconds or HH:MM:SS (must be greater than start)"
        required: true
      quality:
        description: "Quality string"
        required: false
      no-gpu:
        description: "Disable GPU acceleration"
        type: boolean
        required: false
      output:
        description: "Output file (.mp4) or directory"
        required: false
      browser:
        description: "Browser for YouTube cookies"
        required: false
      quiet:
        description: "Suppress progress output"
        type: boolean
        required: false
  download-vod-scripting:
    description: >
      Download a video in quiet mode and capture the output file path into a
      variable. Designed for scripting/automation. All progress goes to stderr;
      only the final saved path goes to stdout.
    command: >
      $path = uv run python download_vod.py --url <url> --quiet 2>$null
    arguments:
      url:
        description: "Video URL"
        required: true
      quality:
        description: "Quality string"
        required: false
      start:
        description: "Start time"
        required: false
      end:
        description: "End time"
        required: false
      no-gpu:
        description: "Disable GPU acceleration"
        type: boolean
        required: false
      output:
        description: "Output file (.mp4) or directory"
        required: false
      browser:
        description: "Browser for YouTube cookies"
        required: false
---

# downloadvods — VOD Downloader CLI

## Overview

Downloads videos from **Twitch**, **Kick**, and **YouTube** as H.264 MP4 files using `yt-dlp` and `ffmpeg`. Supports quality selection, time-range trimming, GPU acceleration, and YouTube cookie-based authentication.

## Quick Reference

| Flag | Required | Default | Description |
|---|---|---|---|
| `--url` | Yes | — | Video URL |
| `--quality` | No | `best` | Quality: `1080p60`, `720p`, `best`. Invalid → best |
| `--start` | No | `0` | Start time (seconds or `HH:MM:SS`) |
| `--end` | No | `0` | End time (seconds or `HH:MM:SS`). `0` = full video |
| `--no-gpu` | No | off | Disable GPU acceleration |
| `--output` / `-o` | No | `.` | Output file `.mp4` or directory |
| `--browser` | No | — | Browser for YouTube cookies |
| `--quiet` / `-q` | No | off | Suppress progress (errors still shown) |

## Resource Files

| File | Purpose |
|---|---|
| `examples/twitch.md` | Twitch-specific download patterns |
| `examples/kick.md` | Kick-specific download patterns |
| `examples/youtube.md` | YouTube download patterns with cookie auth |
| `examples/advanced.md` | GPU control, scripting, edge cases |
| `best-practices.md` | Agent guidelines for quoting, errors, decisions |
| `troubleshooting.md` | Symptom → solution reference |

## Platform Notes

- **Twitch**: Works without authentication for VODs
- **Kick**: Works without authentication
- **YouTube**: Most HD videos require `--browser`. Close the browser completely before running to release cookie locks

## PowerShell Quoting Rule

URLs containing `&` **must** be double-quoted:

```powershell
# CORRECT
uv run python download_vod.py --url "https://youtube.com/watch?v=xxxx&list=yyyy"

# WRONG — & is special in PowerShell
uv run python download_vod.py --url https://youtube.com/watch?v=xxxx&list=yyyy
```