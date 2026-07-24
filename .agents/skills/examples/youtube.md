# YouTube Download Examples

## IMPORTANT: YouTube Rules

1. **Most HD videos require `--browser`** for cookie-based authentication
2. **Close the browser completely** before using `--browser` (cookie files are locked while browser runs)
3. **Always double-quote URLs** containing `&` (PowerShell treats `&` as a special character)
4. **Update yt-dlp** if only 360p is available: `uv add "yt-dlp>=2026.7"`

---

## Basic Download (May Fail Without Browser)

```powershell
uv run python download_vod.py --url "https://www.youtube.com/watch?v=xxxx"
```

## With Browser Cookies (Recommended)

```powershell
uv run python download_vod.py --url "https://www.youtube.com/watch?v=xxxx" --browser chrome
```

```powershell
uv run python download_vod.py --url "https://www.youtube.com/watch?v=xxxx" --browser firefox
```

```powershell
uv run python download_vod.py --url "https://www.youtube.com/watch?v=xxxx" --browser edge
```

## With Quality and Time Trim

```powershell
uv run python download_vod.py --url "https://www.youtube.com/watch?v=xxxx" --browser chrome --quality 1080p --start 00:05:00 --end 00:10:00
```

## URL With Extra Parameters (&list, &t, etc.)

PowerShell requires **double quotes** around URLs containing `&`:

```powershell
uv run python download_vod.py --url "https://www.youtube.com/watch?v=xxxx&list=yyyy&start_radio=1" --browser chrome
```

## Custom Output Path

```powershell
uv run python download_vod.py --url "https://www.youtube.com/watch?v=xxxx" --browser chrome --output D:\downloads\tutorial.mp4
```

## Short youtu.be URLs

```powershell
uv run python download_vod.py --url "https://youtu.be/xxxx" --browser chrome
```

## Quiet Mode For Scripting

```powershell
$path = uv run python download_vod.py --url "https://www.youtube.com/watch?v=xxxx" --browser chrome --quiet 2>$null
```

## Notes

- Without `--browser`, YouTube may return **only 360p** or return **HTTP 403**
- Supported browsers: `chrome`, `firefox`, `edge`, `brave`, `chromium`, `opera`, `vivaldi`, `safari`
- The `noplaylist` option is always enabled; playlists will **not** be downloaded
- If an invalid quality is requested, the highest available quality is used automatically