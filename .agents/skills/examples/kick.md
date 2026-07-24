# Kick VOD Download Examples

## Basic Download

```powershell
uv run python download_vod.py --url https://kick.com/video/abc123
```

## With Quality and Trim

```powershell
uv run python download_vod.py --url https://kick.com/video/abc123 --quality 1080p --start 00:15:00 --end 00:45:00
```

## Custom Output Directory Without GPU

```powershell
uv run python download_vod.py --url https://kick.com/video/abc123 --output D:\videos --no-gpu
```

## Full Options

```powershell
uv run python download_vod.py --url https://kick.com/video/abc123 --quality 720p --start 00:05:00 --end 00:10:00 --output D:\clips\highlight.mp4 --quiet
```

## Notes

- Kick videos do **not** require authentication
- No `--browser` flag needed
- GPU acceleration is auto-detected and enabled by default
- If the specified quality is unavailable, the highest available is used automatically