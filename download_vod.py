#!/usr/bin/env python3
"""
download_vod.py — CLI tool for downloading Twitch, Kick & YouTube VODs.

Usage:
    uv run python download_vod.py --url <URL> [options]

Examples:
    uv run python download_vod.py --url https://www.twitch.tv/videos/123456789
    uv run python download_vod.py --url "https://youtube.com/watch?v=xxxx&list=...&start_radio=1" --quality 1080p --start 00:05:00 --end 00:10:00
    uv run python download_vod.py --url https://kick.com/video/xxx --output D:\\videos --no-gpu
    uv run python download_vod.py --url "https://youtube.com/watch?v=xxxx" --browser chrome

PowerShell note: URLs containing '&' MUST be quoted with double quotes (") because
'&' is a special character in PowerShell.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

import yt_dlp


# ══════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════

BROWSERS = ["chrome", "firefox", "edge", "brave", "chromium", "opera", "vivaldi", "safari"]


# ══════════════════════════════════════════════════════════════════
# UTILITIES
# ══════════════════════════════════════════════════════════════════

def detect_platform(url):
    u = url.lower()
    if "twitch.tv" in u:
        return "twitch"
    if "kick.com" in u:
        return "kick"
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    return "other"


def format_duration(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def parse_time_to_seconds(time_str):
    parts = time_str.strip().split(":")
    if len(parts) == 3:
        h, m, s = map(int, parts)
        return h * 3600 + m * 60 + s
    if len(parts) == 2:
        m, s = map(int, parts)
        return m * 60 + s
    return int(parts[0])


def sanitize_filename(name):
    sanitized = re.sub(r'[<>:"/\\|?*]', '', name).strip()
    return sanitized[:80] if sanitized else "video"


def check_gpu_encoder():
    encoders = []
    try:
        r = subprocess.run(
            ["ffmpeg", "-encoders"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        out = r.stdout
        if "h264_nvenc" in out:
            encoders.append(("NVIDIA NVENC", "h264_nvenc"))
        if "h264_amf" in out:
            encoders.append(("AMD AMF", "h264_amf"))
        if "h264_vaapi" in out:
            encoders.append(("Intel VAAPI", "h264_vaapi"))
        if "h264_qsv" in out:
            encoders.append(("Intel QuickSync", "h264_qsv"))
    except Exception:
        pass
    return encoders


def ffmpeg_video_encoder_args(use_gpu, gpu_encoder):
    if use_gpu and gpu_encoder:
        if "nvenc" in gpu_encoder:
            return ["-c:v", gpu_encoder, "-rc", "vbr", "-cq", "22", "-preset", "p4"]
        return ["-c:v", gpu_encoder, "-quality", "speed", "-qp", "22"]
    return ["-c:v", "libx264", "-preset", "fast", "-crf", "22"]


def ffmpeg_trim_args(start_time, end_time):
    args = []
    if start_time > 0:
        args += ["-ss", str(start_time)]
    if end_time > 0:
        args += ["-to", str(end_time)]
    return args


# ══════════════════════════════════════════════════════════════════
# FORMAT PARSING
# ══════════════════════════════════════════════════════════════════

def parse_formats(info, platform):
    if platform == "youtube":
        return _youtube_all_qualities(info)

    formats = []
    for f in info.get("formats", []):
        has_video = f.get("vcodec", "none") != "none"
        height = f.get("height")
        if not (has_video and height):
            continue
        fps = f.get("fps", 30) or 30
        quality = f"{height}p{int(fps) if int(fps) != 30 else ''}"
        filesize = f.get("filesize") or f.get("filesize_approx", 0)
        formats.append({
            "format_id": f.get("format_id", ""),
            "quality": quality,
            "height": height,
            "fps": fps,
            "filesize": filesize,
            "display": f"{quality} ~ {filesize / (1024 ** 3):.2f} GB" if filesize else quality,
            "source": "ytdlp",
        })
    seen = set()
    unique = []
    for f in sorted(formats, key=lambda x: (x["height"], x["fps"]), reverse=True):
        key = (f["height"], f["fps"])
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def _youtube_all_qualities(info):
    def codec_priority(vcodec, ext):
        vc = (vcodec or "").lower()
        if "avc" in vc or "h264" in vc:
            return 3
        if ext == "mp4":
            return 2
        if "vp9" in vc or "vp09" in vc:
            return 1
        return 0

    video_streams = {}
    for f in info.get("formats", []):
        if f.get("vcodec", "none") == "none":
            continue
        h = f.get("height")
        if not h:
            continue
        fps = int(f.get("fps", 30) or 30)
        key = (h, fps)
        vcodec = f.get("vcodec", "")
        ext = f.get("ext", "")
        prio = codec_priority(vcodec, ext)
        filesize = f.get("filesize") or f.get("filesize_approx", 0) or 0
        existing = video_streams.get(key)
        if not existing or prio > existing["priority"]:
            video_streams[key] = {
                "format_id": f["format_id"],
                "filesize": filesize,
                "priority": prio,
                "vcodec": vcodec,
                "needs_transcode": prio < 3,
            }

    result = []
    for (h, fps), vdata in video_streams.items():
        fmt_id = f"bestvideo[height<={h}]+bestaudio/best[height<={h}]"
        quality = f"{h}p{fps if fps != 30 else ''}"
        filesize = vdata["filesize"]
        needs_tc = vdata["needs_transcode"]
        label_suffix = " [H.264 transcode]" if needs_tc else ""
        display = (
            f"{quality}{label_suffix} ~ {filesize / (1024 ** 3):.2f} GB"
            if filesize
            else f"{quality}{label_suffix}"
        )
        result.append({
            "format_id": fmt_id,
            "quality": quality,
            "height": h,
            "fps": fps,
            "filesize": filesize,
            "display": display,
            "source": "ytdlp",
            "needs_transcode": needs_tc,
            "vcodec": vdata["vcodec"],
        })

    seen = set()
    unique = []
    for f in sorted(result, key=lambda x: (x["height"], x["fps"]), reverse=True):
        key = (f["height"], f["fps"])
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


# ══════════════════════════════════════════════════════════════════
# VIDEO INFO
# ══════════════════════════════════════════════════════════════════

def get_video_info(url, browser=None):
    platform = detect_platform(url)

    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "socket_timeout": 20,
        "retries": 3,
        "fragment_retries": 3,
        "noprogress": True,
        "noplaylist": True,
    }
    if browser:
        opts["cookies_from_browser"] = browser

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            raw = ydl.extract_info(url, download=False)
    except Exception as e:
        msg = str(e)
        if not browser and platform == "youtube":
            msg += "\nTip: YouTube may require authentication. Try --browser chrome"
        return None, msg

    if not raw:
        return None, "No response from server"

    formats = parse_formats(raw, platform)
    if not formats:
        return None, "No video formats found"

    duration = raw.get("duration", 0)
    return {
        "title": raw.get("title", "Unknown Title"),
        "uploader": raw.get("uploader", raw.get("channel", "Unknown")),
        "duration": duration,
        "duration_formatted": format_duration(duration),
        "thumbnail": raw.get("thumbnail", ""),
        "formats": formats,
        "is_live": raw.get("is_live", False),
        "platform": platform,
    }, None


# ══════════════════════════════════════════════════════════════════
# DOWNLOAD
# ══════════════════════════════════════════════════════════════════

def download_video(
    url,
    format_id,
    start_time,
    end_time,
    output_path,
    platform,
    use_gpu,
    gpu_encoder,
    browser=None,
    needs_transcode=False,
    quiet=False,
):
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_file = os.path.join(tmpdir, "temp_download.%(ext)s")

        def progress_hook(d):
            if d["status"] == "downloading" and not quiet:
                pct = d.get("_percent_str", "0%").strip()
                speed = d.get("_speed_str", "N/A").strip()
                eta = d.get("_eta_str", "N/A").strip()
                print(f"\rDownloading... {pct} | Speed: {speed} | ETA: {eta}", end="", file=sys.stderr)
            elif d["status"] == "finished" and not quiet:
                print(file=sys.stderr)

        if not quiet:
            print(f"Using format: {format_id}", file=sys.stderr)
            print("Downloading video...", file=sys.stderr)

        ydl_opts = {
            "format": format_id,
            "outtmpl": temp_file,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
            "progress_hooks": [progress_hook],
            "noplaylist": True,
        }
        if browser:
            ydl_opts["cookies_from_browser"] = browser

        is_youtube = platform == "youtube"

        if not is_youtube and (start_time > 0 or end_time > 0):
            ydl_opts["external_downloader"] = "ffmpeg"
            ydl_opts["external_downloader_args"] = {
                "ffmpeg_i": ["-ss", str(start_time), "-to", str(end_time)]
            }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            print(f"Download failed: {e}", file=sys.stderr)
            return False

        downloaded_file = next(
            (os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.startswith("temp_download")),
            None,
        )
        if not downloaded_file:
            print("Error: downloaded file not found.", file=sys.stderr)
            return False

        try:
            probe = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=codec_name",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    downloaded_file,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            detected = probe.stdout.strip().lower()
            if detected in ("av1", "av01", "vp9", "vp09"):
                needs_transcode = True
        except Exception:
            pass

        has_time_range = (start_time > 0 or end_time > 0) and is_youtube

        def _transcode(trim, vc_args, label):
            if not quiet:
                print(f"{label}...", file=sys.stderr)
            out = os.path.join(tmpdir, "processed.mp4")
            t_args = ffmpeg_trim_args(start_time, end_time) if trim else []
            subprocess.run(
                [
                    "ffmpeg",
                    *t_args,
                    "-i",
                    downloaded_file,
                    *vc_args,
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-avoid_negative_ts",
                    "make_zero",
                    "-movflags",
                    "+faststart",
                    "-y",
                    out,
                ],
                check=True,
                capture_output=quiet,
            )
            shutil.move(out, output_path)

        if use_gpu and gpu_encoder:
            _transcode(
                has_time_range,
                ffmpeg_video_encoder_args(use_gpu, gpu_encoder),
                f"Encoding with GPU ({gpu_encoder})",
            )
        elif needs_transcode:
            label = gpu_encoder if (use_gpu and gpu_encoder) else "libx264 (CPU)"
            _transcode(
                has_time_range,
                ffmpeg_video_encoder_args(use_gpu, gpu_encoder),
                f"Converting to H.264 with {label}",
            )
        elif has_time_range:
            if not quiet:
                print("Trimming segment...", file=sys.stderr)
            trimmed = os.path.join(tmpdir, "trimmed.mp4")
            subprocess.run(
                [
                    "ffmpeg",
                    *ffmpeg_trim_args(start_time, end_time),
                    "-i",
                    downloaded_file,
                    "-c",
                    "copy",
                    "-avoid_negative_ts",
                    "make_zero",
                    "-movflags",
                    "+faststart",
                    "-y",
                    trimmed,
                ],
                check=True,
                capture_output=quiet,
            )
            shutil.move(trimmed, output_path)
        else:
            shutil.move(downloaded_file, output_path)

        return True


# ══════════════════════════════════════════════════════════════════
# FORMAT SELECTION
# ══════════════════════════════════════════════════════════════════

def find_format(formats, quality_str):
    if not quality_str or quality_str == "best":
        return formats[0] if formats else None

    q = quality_str.lower().rstrip("p")

    for f in formats:
        if f["quality"].lower() == quality_str.lower():
            return f

    if q.isdigit():
        target_h = int(q)
        matches = [f for f in formats if f["height"] == target_h]
        if matches:
            return matches[0]

    for f in formats:
        if q in f["quality"].lower():
            return f

    return None


def resolve_output_path(output_arg, title, start_sec, end_sec):
    safe = sanitize_filename(title)
    start_str = format_duration(start_sec).replace(":", "-")
    end_str = format_duration(end_sec).replace(":", "-")
    default_name = f"{safe}_{start_str}_{end_str}.mp4"

    if output_arg.lower().endswith(".mp4"):
        return output_arg

    out_dir = output_arg or "."
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, default_name)


# ══════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════

def build_parser():
    parser = argparse.ArgumentParser(
        description="Download Twitch, Kick & YouTube VODs from the command line.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s --url https://www.twitch.tv/videos/123456789
  %(prog)s --url "https://youtube.com/watch?v=xxxx&list=...&start_radio=1" --quality 1080p --start 00:05:00 --end 00:10:00
  %(prog)s --url https://kick.com/video/xxx --output D:\\videos --no-gpu
  %(prog)s --url "https://youtube.com/watch?v=xxxx" --browser chrome

PowerShell: URLs with & must be quoted ("url") because & is a special character.""",
    )
    parser.add_argument("--url", required=True, help="Video URL (Twitch, Kick, or YouTube)")
    parser.add_argument(
        "--quality",
        default="best",
        help="Video quality (e.g. 1080p60, 720p). Default: highest available",
    )
    parser.add_argument(
        "--start",
        default="0",
        help="Start time in seconds or HH:MM:SS. Default: 0",
    )
    parser.add_argument(
        "--end",
        default="0",
        help="End time in seconds or HH:MM:SS. Default: 0 (full video)",
    )
    parser.add_argument("--gpu", action="store_true", default=True, help=argparse.SUPPRESS)
    parser.add_argument("--no-gpu", action="store_false", dest="gpu", help="Disable GPU acceleration")
    parser.add_argument(
        "--output",
        "-o",
        default=".",
        help="Output path (file.mp4 or directory). Default: current directory",
    )
    parser.add_argument(
        "--browser",
        choices=BROWSERS,
        help="Browser for YouTube cookies (chrome, firefox, edge, brave, etc.)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress progress output (errors still shown)",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    platform = detect_platform(args.url)
    if platform == "other":
        print("Error: unrecognized platform. Supported: Twitch, Kick, YouTube.", file=sys.stderr)
        sys.exit(1)

    try:
        start_sec = parse_time_to_seconds(args.start)
        end_sec = parse_time_to_seconds(args.end)
    except ValueError as e:
        print(f"Error: invalid time format: {e}", file=sys.stderr)
        sys.exit(1)

    if end_sec > 0 and start_sec >= end_sec:
        print("Error: --end must be greater than --start.", file=sys.stderr)
        sys.exit(1)

    gpu_encoders = check_gpu_encoder()
    use_gpu = args.gpu and len(gpu_encoders) > 0
    gpu_encoder = gpu_encoders[0][1] if use_gpu else None
    if args.gpu and not gpu_encoders and not args.quiet:
        print("Note: no GPU encoder detected, using CPU (libx264).", file=sys.stderr)
    elif use_gpu and not args.quiet:
        print(f"GPU acceleration: {gpu_encoders[0][0]}", file=sys.stderr)

    if not args.quiet:
        print("Fetching video information...", file=sys.stderr)

    info, error = get_video_info(args.url, args.browser)
    if not info:
        print(f"Error: {error}" if error else "Error: could not get video info.", file=sys.stderr)
        sys.exit(1)

    if info.get("is_live") and not args.quiet:
        print("Warning: this appears to be a live stream. Download may fail.", file=sys.stderr)

    duration = info["duration"]
    if end_sec == 0 or end_sec > duration:
        end_sec = duration
    if start_sec >= end_sec:
        print(
            f"Error: --start ({format_duration(start_sec)}) must be before --end ({format_duration(end_sec)}). "
            f"Video duration is {format_duration(duration)}.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.quiet:
        print(f"Title:    {info['title']}", file=sys.stderr)
        print(f"Duration: {info['duration_formatted']}", file=sys.stderr)
        print(f"Platform: {info['platform']}", file=sys.stderr)

    selected = find_format(info["formats"], args.quality)
    if not selected:
        selected = info["formats"][0]
        if not args.quiet:
            print(
                f"Quality '{args.quality}' not available. Using highest: {selected['quality']}",
                file=sys.stderr,
            )
    elif args.quality != "best" and not args.quiet:
        print(f"Selected quality: {selected['quality']}", file=sys.stderr)

    output_path = resolve_output_path(args.output, info["title"], start_sec, end_sec)
    if os.path.exists(output_path):
        base, ext = os.path.splitext(output_path)
        counter = 1
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        output_path = f"{base}_{counter}{ext}"
        if not args.quiet:
            print(f"File exists, using: {os.path.basename(output_path)}", file=sys.stderr)

    if not args.quiet:
        print(f"Output:   {output_path}", file=sys.stderr)

    success = download_video(
        args.url,
        selected["format_id"],
        start_sec,
        end_sec,
        output_path,
        info["platform"],
        use_gpu,
        gpu_encoder,
        browser=args.browser,
        needs_transcode=selected.get("needs_transcode", False),
        quiet=args.quiet,
    )

    if success:
        print(f"Saved: {output_path}")
    else:
        print("Download failed.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
