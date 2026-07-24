# Troubleshooting

## Symptom → Solution

| Symptom | Likely Cause | Solution |
|---|---|---|
| `Error: YouTube may require authentication. Try --browser chrome` | No cookies provided for YouTube | Add `--browser chrome` (or firefox, edge). Close browser first |
| `Download failed: HTTP Error 403` | YouTube blocking unauthenticated request | Use `--browser chrome` flag |
| Only 360p available on YouTube | Old yt-dlp version | Update: `uv add "yt-dlp>=2026.7"` |
| `ffmpeg` not found / not recognized | FFmpeg not installed or not in PATH | Install: `winget install Gyan.FFmpeg`, then restart terminal |
| `Note: no GPU encoder detected, using CPU` | No compatible GPU or FFmpeg without GPU support | Normal fallback. CPU encoding is slower but works. Install FFmpeg with full features if GPU desired |
| `Error: unrecognized platform` | URL is from an unsupported site | Only Twitch, Kick, and YouTube are supported |
| `Error: --end must be greater than --start` | start >= end in time args | Ensure start is before end. Check time format |
| `Warning: this appears to be a live stream` | URL points to a live stream, not a VOD | Live streams may fail. Wait for the stream to end and become a VOD |
| `Download failed: HTTP Error 429` | Rate limiting | Wait a few minutes before retrying. Reduce number of concurrent downloads |
| File created but is 0 bytes or corrupt | Download interrupted or format issue | Retry with `--no-gpu` or different quality |
| `Error: no video formats found` | URL is invalid or video is private/deleted | Verify the URL is correct and the video is publicly accessible |
| Browser cookie error | Browser is open while trying to access cookies | **Close the browser completely** before running with `--browser` |

## Quick Checks

### Is FFmpeg installed?
```powershell
ffmpeg -version
```

### Is yt-dlp up to date?
```powershell
uv run python -c "import yt_dlp; print(yt_dlp.version.__version__)"
```
Expected: `2026.7` or later.

### What GPU encoders are available?
```powershell
ffmpeg -encoders | Select-String "h264"
```
Look for: `h264_nvenc`, `h264_amf`, `h264_qsv`, `h264_vaapi`.

### Test with a known-good YouTube video
```powershell
uv run python download_vod.py --url "https://www.youtube.com/watch?v=sVTy_wmn5SU" --browser chrome --quiet
```

## Common Mistakes

1. **Missing quotes on YouTube URLs with `&`** → PowerShell interprets `&` as a command separator
2. **Browser left open** → Cookie files are locked; close browser completely
3. **Running `python` directly** → Must use `uv run python` for the virtual environment
4. **Assuming GPU works on any system** → GPU encoding is auto-detected; CPU fallback is normal