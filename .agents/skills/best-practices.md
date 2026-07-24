# Best Practices for AI Agents

## 1. Always Quote YouTube URLs

PowerShell treats `&` as a command separator. YouTube URLs often contain `&list=...`, `&t=...`, `&start_radio=1`.

```powershell
# CORRECT — always use double quotes for YouTube URLs
uv run python download_vod.py --url "https://youtube.com/watch?v=xxxx&list=yyyy"

# INCORRECT — will fail or behave unexpectedly
uv run python download_vod.py --url https://youtube.com/watch?v=xxxx&list=yyyy
```

## 2. Use `--browser` for YouTube

- **Always** include `--browser` when the user asks for a YouTube download
- If the user doesn't specify a browser, use `chrome` (most common)
- Tell the user to **close their browser completely** before running

## 3. Platform Detection Logic

| URL Contains | Platform | Requires `--browser`? | Notes |
|---|---|---|---|
| `twitch.tv` | Twitch | No | Works without auth |
| `kick.com` | Kick | No | Works without auth |
| `youtube.com` or `youtu.be` | YouTube | Yes | Most videos need cookies for HD |
| anything else | Unsupported | — | Error: unrecognized platform |

## 4. Quality Selection Strategy

- If user says "best quality" or doesn't specify → omit `--quality` (defaults to `best`)
- If user specifies a height (e.g. "1080p") → use `--quality 1080p`
- If user specifies with FPS (e.g. "1080p60") → use `--quality 1080p60`
- If the requested quality is unavailable → tool auto-falls back to highest

## 5. Time Format

Both formats work:
- Seconds: `--start 300` → 5 minutes
- HH:MM:SS: `--start 00:05:00` → 5 minutes

## 6. Output Path Conventions

- Omit `--output` → saves to current directory as `{Title}_{Start}_{End}.mp4`
- Directory path: `--output D:\videos` → creates file inside directory
- File path: `--output D:\videos\clip.mp4` → exact filename
- If file exists → auto-appends `_1`, `_2` etc.

## 7. Error Recovery

| Error | Action |
|---|---|
| `YouTube may require authentication` | Retry with `--browser chrome` |
| `HTTP Error 403` | Retry with `--browser chrome` |
| `no GPU encoder detected` | Falls back to CPU automatically. Inform user |
| `ffmpeg not found` | Install FFmpeg: `winget install Gyan.FFmpeg` |
| `Only 360p available` | Update yt-dlp: `uv add "yt-dlp>=2026.7"` |
| `unrecognized platform` | Supported: Twitch, Kick, YouTube only |

## 8. GPU Default Behavior

- GPU is **auto-detected** and **enabled** by default
- Only use `--no-gpu` if the user explicitly asks to disable GPU
- GPU detection is silent unless GPU is found or user runs without `--quiet`

## 9. Always Use `uv run python`

Every command must use `uv run python` to execute within the project's virtual environment:

```powershell
uv run python download_vod.py --url <URL> [options]
```

Do **not** use `python download_vod.py` directly or any other interpreter.

## 10. Scripting Pattern

When the user wants to use the downloaded file path in another command:

```powershell
$path = uv run python download_vod.py --url <URL> --quiet 2>$null
```