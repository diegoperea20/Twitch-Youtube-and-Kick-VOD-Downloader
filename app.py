"""
Twitch, Kick & YouTube VOD Downloader with Streamlit
YouTube: uses browser cookies (Chrome/Firefox) for authentication.
Fallback: pytubefix if yt-dlp fails.
"""

import streamlit as st
import yt_dlp
import os
import re
import subprocess
import shutil
import threading
import tempfile

# Silent installation of pytubefix if not available
try:
    from pytubefix import YouTube as PyTube
    PYTUBEFIX_AVAILABLE = True
except ImportError:
    PYTUBEFIX_AVAILABLE = False

st.set_page_config(
    page_title="Twitch, Kick & YouTube VOD Downloader",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .stApp { background-color: #0e0e10; }
    .main-container { background-color: #1f1f23; border-radius: 8px; padding: 24px; margin-bottom: 16px; }
    .vod-title { color: #efeff1; font-size: 18px; font-weight: 600; margin-bottom: 16px; }
    .live-badge { color: #ff4444; font-size: 14px; }
    .section-label { color: #adadb8; font-size: 12px; font-weight: 600; margin-bottom: 6px; }
    .platform-badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 700; margin-bottom: 12px; }
    .platform-twitch  { background-color: #9146ff; color: white; }
    .platform-kick    { background-color: #53fc19; color: #111; }
    .platform-youtube { background-color: #ff0000; color: white; }
    .platform-other   { background-color: #404040; color: white; }
    .stTextInput > div > div > input { background-color: #18181b !important; border: 1px solid #303032 !important; color: #efeff1 !important; border-radius: 6px !important; }
    .stSelectbox > div > div > div { background-color: #18181b !important; border: 1px solid #303032 !important; color: #efeff1 !important; border-radius: 6px !important; }
    .stSlider > div > div > div > div { background-color: #9146ff !important; }
    .stSlider > div > div > div { height: 8px !important; }
    .stSlider > div > div > div > div[data-baseweb="slider"] > div { height: 8px !important; border-radius: 4px !important; }
    .stSlider > div > div > div > div[data-testid="stThumbValue"], [data-baseweb="slider"] [role="slider"] { width: 22px !important; height: 22px !important; background-color: #9146ff !important; border: 3px solid #efeff1 !important; border-radius: 50% !important; box-shadow: 0 0 8px rgba(145,70,255,0.6) !important; top: -7px !important; }
    .stButton > button { background-color: #9146ff !important; color: white !important; border: none !important; border-radius: 6px !important; padding: 10px 24px !important; font-weight: 600 !important; }
    .stButton > button:hover { background-color: #772ce8 !important; }
    .secondary-section { background-color: #1f1f23; border-radius: 8px; padding: 24px; text-align: center; }
    .secondary-title { color: #efeff1; font-size: 20px; font-weight: 600; margin-bottom: 20px; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

BROWSERS = ["chrome", "firefox", "edge", "brave", "chromium", "opera", "vivaldi", "safari"]


# ══════════════════════════════════════════════════════════════════
# UTILITIES
# ══════════════════════════════════════════════════════════════════

def detect_platform(url):
    u = url.lower()
    if "twitch.tv" in u:   return "twitch"
    if "kick.com" in u:    return "kick"
    if "youtube.com" in u or "youtu.be" in u: return "youtube"
    return "other"

def platform_badge_html(platform):
    labels = {"twitch": "Twitch", "kick": "Kick", "youtube": "YouTube", "other": "Video"}
    return (f'<span class="platform-badge platform-{platform}">'
            f'{labels.get(platform, "Video")}</span>')

def format_duration(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def parse_time_to_seconds(time_str):
    parts = time_str.strip().split(":")
    if len(parts) == 3:
        h, m, s = map(int, parts); return h * 3600 + m * 60 + s
    if len(parts) == 2:
        m, s = map(int, parts); return m * 60 + s
    return int(parts[0])

def _run_with_timeout(fn, timeout=45):
    container = {'result': None, 'error': None}
    def _worker():
        try:
            container['result'] = fn()
        except Exception as e:
            container['error'] = str(e)
    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=timeout)
    if t.is_alive():
        return None, 'timeout'
    return container['result'], container['error']


# ══════════════════════════════════════════════════════════════════
# FORMAT PARSING
# ══════════════════════════════════════════════════════════════════

def _parse_formats_yt_dlp(info, platform):
    """
    For YouTube: accepts video-only streams (DASH) and combines them with best audio.
    This allows offering 1080p, 1440p, 4K in addition to progressive (max 720p).
    For Twitch/Kick: only streams with video (may have embedded audio).
    """
    if platform == 'youtube':
        return _youtube_all_qualities(info)

    # Twitch / Kick / others
    formats = []
    for f in info.get('formats', []):
        has_video = f.get('vcodec', 'none') != 'none'
        height = f.get('height')
        if not (has_video and height):
            continue
        fps = f.get('fps', 30) or 30
        quality = f"{height}p{int(fps) if int(fps) != 30 else ''}"
        filesize = f.get('filesize') or f.get('filesize_approx', 0)
        formats.append({
            'format_id': f.get('format_id', ''),
            'quality': quality,
            'height': height,
            'fps': fps,
            'filesize': filesize,
            'display': f"{quality} ~ {filesize/(1024**3):.2f} GB" if filesize else quality,
            'source': 'ytdlp',
        })
    seen, unique = set(), []
    for f in sorted(formats, key=lambda x: (x['height'], x['fps']), reverse=True):
        key = (f['height'], f['fps'])
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def _youtube_all_qualities(info):
    """
    Builds the quality list for YouTube.
    Codec priority: H.264/AVC (native Windows) > VP9 > AV1.
    If only AV1/VP9 for certain quality, marks needs_transcode=True
    so that download re-encodes to H.264 with ffmpeg.
    """
    # Best audio m4a (compatible with mp4/Windows without transcoding)
    best_audio_mp4, best_abr_mp4 = None, 0
    best_audio_any, best_abr_any = None, 0
    for f in info.get('formats', []):
        if f.get('vcodec', 'none') != 'none': continue
        if f.get('acodec', 'none') == 'none': continue
        abr = f.get('abr', 0) or f.get('tbr', 0) or 0
        ext = f.get('ext', '')
        if ext in ('m4a', 'mp4') and abr >= best_abr_mp4:
            best_abr_mp4, best_audio_mp4 = abr, f['format_id']
        if abr >= best_abr_any:
            best_abr_any, best_audio_any = abr, f['format_id']
    best_audio = best_audio_mp4 or best_audio_any

    def _codec_priority(vcodec, ext):
        """Higher number = better for Windows compatibility (native H.264)."""
        vc = (vcodec or '').lower()
        if 'avc' in vc or 'h264' in vc:    return 3   # H.264 — native playback Win11
        if ext == 'mp4':                    return 2   # mp4 without avc (can be AV1 in mp4)
        if 'vp9' in vc or 'vp09' in vc:    return 1   # VP9 webm — not native but decodeable
        return 0                                        # AV1, AV01, others

    # Collect the BEST stream for each (height, fps)
    video_streams = {}
    for f in info.get('formats', []):
        if f.get('vcodec', 'none') == 'none': continue
        h = f.get('height')
        if not h: continue
        fps = int(f.get('fps', 30) or 30)
        key = (h, fps)
        vcodec = f.get('vcodec', '')
        ext    = f.get('ext', '')
        prio   = _codec_priority(vcodec, ext)
        filesize = f.get('filesize') or f.get('filesize_approx', 0) or 0
        existing = video_streams.get(key)
        if not existing or prio > existing['priority']:
            video_streams[key] = {
                'format_id': f['format_id'],
                'filesize': filesize,
                'priority': prio,
                'vcodec': vcodec,
                'needs_transcode': prio < 3,  # True if NOT native H.264
            }

    result = []
    for (h, fps), vdata in video_streams.items():
        fmt_id = f"{vdata['format_id']}+{best_audio}" if best_audio else vdata['format_id']
        quality = f"{h}p{fps if fps != 30 else ''}"
        filesize = vdata['filesize']
        needs_tc = vdata['needs_transcode']
        # Show warning in label if needs transcoding
        label_suffix = " [H.264 transcode]" if needs_tc else ""
        result.append({
            'format_id': fmt_id,
            'quality': quality,
            'height': h,
            'fps': fps,
            'filesize': filesize,
            'display': (f"{quality}{label_suffix} ~ {filesize/(1024**3):.2f} GB"
                        if filesize else f"{quality}{label_suffix}"),
            'source': 'ytdlp',
            'needs_transcode': needs_tc,
            'vcodec': vdata['vcodec'],
        })

    seen, unique = set(), []
    for f in sorted(result, key=lambda x: (x['height'], x['fps']), reverse=True):
        key = (f['height'], f['fps'])
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def _youtube_merged_formats(info):
    # Alias maintained for compatibility, delegates to new function
    return _youtube_all_qualities(info)


# ══════════════════════════════════════════════════════════════════
# GET VIDEO INFO
# ══════════════════════════════════════════════════════════════════

def _get_info_ytdlp(url, platform, browser=None):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'socket_timeout': 20,
        'retries': 3,
        'fragment_retries': 3,
        'noprogress': True,
    }
    if browser:
        opts['cookies_from_browser'] = browser

    def _extract():
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    info, err = _run_with_timeout(_extract, timeout=45)
    if err or not info:
        return None, err or "No response"

    formats = _parse_formats_yt_dlp(info, platform)
    if not formats:
        return None, "No video formats found"

    duration = info.get('duration', 0)
    return {
        'title': info.get('title', 'Unknown Title'),
        'uploader': info.get('uploader', info.get('channel', 'Unknown')),
        'duration': duration,
        'duration_formatted': format_duration(duration),
        'thumbnail': info.get('thumbnail', ''),
        'formats': formats,
        'is_live': info.get('is_live', False),
        'platform': platform,
    }, None


def _get_info_pytubefix(url):
    """
    Gets YouTube info with pytubefix.
    Includes adaptive streams (video-only) marked for merge with ffmpeg,
    in addition to progressive (max 720p).
    """
    if not PYTUBEFIX_AVAILABLE:
        return None, "pytubefix not installed"
    try:
        yt = PyTube(url, use_oauth=False, allow_oauth_cache=False)
        formats = []
        seen_heights = set()

        # 1. Adaptive video-only streams (1080p, 1440p, 4K) — need merge with audio
        # Prefer mp4 over webm
        adaptive_video = (
            yt.streams.filter(adaptive=True, file_extension='mp4', only_video=True)
            .order_by('resolution').desc()
        )
        # Best adaptive audio for the merge
        best_audio_stream = (
            yt.streams.filter(adaptive=True, file_extension='mp4', only_audio=True)
            .order_by('abr').desc().first()
        )
        best_audio_itag = best_audio_stream.itag if best_audio_stream else None

        for s in adaptive_video:
            if not s.resolution:
                continue
            height = int(s.resolution.replace('p', ''))
            fps = int(s.fps) if s.fps else 30
            key = (height, fps)
            if key in seen_heights:
                continue
            seen_heights.add(key)
            quality = f"{height}p{fps if fps != 30 else ''}"
            filesize = s.filesize or 0
            # format_id is a tuple (video_itag, audio_itag) for the downloader
            fmt_id = f"adaptive:{s.itag}:{best_audio_itag}"
            formats.append({
                'format_id': fmt_id,
                'quality': quality,
                'height': height,
                'fps': fps,
                'filesize': filesize,
                'display': f"{quality} ~ {filesize/(1024**3):.2f} GB" if filesize else quality,
                'source': 'pytubefix',
            })

        # 2. Progressive streams (video+audio, max 720p) — no merge needed
        for s in yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc():
            if not s.resolution:
                continue
            height = int(s.resolution.replace('p', ''))
            fps = int(s.fps) if s.fps else 30
            key = (height, fps)
            if key in seen_heights:
                continue  # we already have this quality from adaptive (better quality)
            seen_heights.add(key)
            quality = f"{height}p{fps if fps != 30 else ''}"
            filesize = s.filesize or 0
            formats.append({
                'format_id': str(s.itag),
                'quality': quality,
                'height': height,
                'fps': fps,
                'filesize': filesize,
                'display': f"{quality} ~ {filesize/(1024**3):.2f} GB" if filesize else quality,
                'source': 'pytubefix',
            })

        if not formats:
            return None, "pytubefix: no available stream found"

        # Sort from highest to lowest quality
        formats.sort(key=lambda x: (x['height'], x['fps']), reverse=True)

        duration = yt.length or 0
        return {
            'title': yt.title or 'Unknown',
            'uploader': yt.author or 'Unknown',
            'duration': duration,
            'duration_formatted': format_duration(duration),
            'thumbnail': yt.thumbnail_url or '',
            'formats': formats,
            'is_live': False,
            'platform': 'youtube',
        }, None
    except Exception as e:
        return None, str(e)


def get_video_info(url, yt_browser=None):
    platform = detect_platform(url)

    # Twitch / Kick / others - direct yt-dlp without cookies
    if platform != 'youtube':
        result, err = _get_info_ytdlp(url, platform, browser=None)
        if err == 'timeout':
            st.error("⏱️ Timeout: could not connect in 45 s.")
            return None
        if err or not result:
            st.error(f"Error getting info: {err}")
            return None
        return result

    # YouTube - Attempt 1: yt-dlp with cookies from selected browser
    ytdlp_err = None
    if yt_browser:
        result, ytdlp_err = _get_info_ytdlp(url, 'youtube', browser=yt_browser)
        if result:
            return result

    # YouTube - Attempt 2: yt-dlp without cookies (sometimes works for public videos)
    if not yt_browser:
        result, ytdlp_err = _get_info_ytdlp(url, 'youtube', browser=None)
        if result:
            return result

    # YouTube - Attempt 3: pytubefix
    result, pyfix_err = _get_info_pytubefix(url)
    if result:
        st.info("ℹ️ Using pytubefix (qualities limited to 720p progressive).")
        return result

    # Total failure - show error with clear instructions
    st.error(
        "❌ Could not get YouTube video information.\n\n"
        f"**yt-dlp Error:** {ytdlp_err}\n\n"
        f"**pytubefix Error:** {pyfix_err}\n\n"
        "**Solutions:**\n"
        "1. Open the **⚙️ YouTube Settings** panel above and select your browser.\n"
        "2. Make sure you have YouTube open and logged in in that browser.\n"
        "3. Close the browser completely before trying (releases the cookie lock).\n"
        "4. Install pytubefix if you don't have it: `pip install pytubefix`"
    )
    return None


# ══════════════════════════════════════════════════════════════════
# DOWNLOAD
# ══════════════════════════════════════════════════════════════════

def check_gpu_encoder():
    encoders = []
    try:
        r = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True, timeout=5)
        out = r.stdout
        if 'h264_nvenc' in out: encoders.append(('NVIDIA NVENC', 'h264_nvenc'))
        if 'h264_amf'   in out: encoders.append(('AMD AMF',      'h264_amf'))
        if 'h264_vaapi' in out: encoders.append(('Intel VAAPI',  'h264_vaapi'))
        if 'h264_qsv'   in out: encoders.append(('Intel QuickSync', 'h264_qsv'))
    except Exception:
        pass
    return encoders



def _ffmpeg_video_encoder_args(use_gpu, gpu_encoder):
    """
    Returns ffmpeg arguments for H.264 video encoder.
    Uses GPU if available and enabled, CPU (libx264) as fallback.
    """
    if use_gpu and gpu_encoder:
        # NVENC doesn't support -crf, uses -rc vbr -cq instead
        if 'nvenc' in gpu_encoder:
            return ['-c:v', gpu_encoder, '-rc', 'vbr', '-cq', '22', '-preset', 'p4']
        # AMF / QSV / VAAPI
        return ['-c:v', gpu_encoder, '-quality', 'speed', '-qp', '22']
    return ['-c:v', 'libx264', '-preset', 'fast', '-crf', '22']

def _ffmpeg_trim_args(start_time, end_time):
    """
    Generates trim arguments for ffmpeg with -ss BEFORE -i (input seeking).
    This avoids initial black video because ffmpeg jumps directly to the correct
    keyframe without decoding from the beginning of the file.
    """
    args = []
    if start_time > 0:
        args += ['-ss', str(start_time)]
    if end_time > 0:
        args += ['-to', str(end_time)]
    return args


def _download_ytdlp(url, format_id, start_time, end_time, output_path,
                    platform, use_gpu, gpu_encoder, stop_event, progress_placeholder,
                    yt_browser=None, needs_transcode=False):
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_file = os.path.join(tmpdir, "temp_download.%(ext)s")

        def progress_hook(d):
            if stop_event and stop_event.is_set():
                raise Exception("Download cancelled by user")
            if d['status'] == 'downloading' and progress_placeholder:
                progress_placeholder.info(
                    f"⬇️ Downloading... {d.get('_percent_str','0%')} | "
                    f"Speed: {d.get('_speed_str','N/A')} | ETA: {d.get('_eta_str','N/A')}"
                )

        ydl_opts = {
            'format': format_id,
            'outtmpl': temp_file,
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [progress_hook],
        }
        if platform == 'youtube':
            if yt_browser:
                ydl_opts['cookies_from_browser'] = yt_browser
            # NOTE: We DON'T use download_sections/force_keyframes_at_cuts for YouTube.
            # This method re-encodes keyframes with libx264 and leaves wrong timestamps
            # (black video for the first seconds). Instead we download complete
            # and trim with ffmpeg in the post-processing step.
        else:
            if start_time > 0 or end_time > 0:
                ydl_opts['external_downloader'] = 'ffmpeg'
                ydl_opts['external_downloader_args'] = {
                    'ffmpeg_i': ['-ss', str(start_time), '-to', str(end_time)]
                }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            if stop_event and stop_event.is_set():
                return False

            downloaded_file = next(
                (os.path.join(tmpdir, f) for f in os.listdir(tmpdir)
                 if f.startswith("temp_download")), None
            )
            if not downloaded_file:
                st.error("Downloaded file not found.")
                return False

            # Detect if downloaded file has AV1/VP9 that Windows can't play natively
            # needs_transcode passed as parameter; may be overridden by ffprobe below

            # Probe actual codec of downloaded file (more reliable than format metadata)
            try:
                probe = subprocess.run(
                    ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                     '-show_entries', 'stream=codec_name',
                     '-of', 'default=noprint_wrappers=1:nokey=1', downloaded_file],
                    capture_output=True, text=True, timeout=10
                )
                detected_codec = probe.stdout.strip().lower()
                if detected_codec in ('av1', 'av01', 'vp9', 'vp09'):
                    needs_transcode = True
            except Exception:
                pass  # if ffprobe fails, use the metadata flag

            has_time_range = (start_time > 0 or end_time > 0) and platform == 'youtube'

            if use_gpu and gpu_encoder:
                if progress_placeholder:
                    progress_placeholder.info(f"🎬 Encoding with GPU ({gpu_encoder})...")
                encoded = os.path.join(tmpdir, "encoded.mp4")
                vc_args = _ffmpeg_video_encoder_args(use_gpu, gpu_encoder)
                trim_args = _ffmpeg_trim_args(start_time, end_time) if has_time_range else []
                subprocess.run(
                    ['ffmpeg', *trim_args, '-i', downloaded_file,
                     *vc_args,
                     '-c:a', 'aac', '-b:a', '192k',
                     '-avoid_negative_ts', 'make_zero',
                     '-movflags', '+faststart',
                     '-y', encoded],
                    check=True, capture_output=True
                )
                shutil.move(encoded, output_path)
            elif needs_transcode:
                encoder_label = gpu_encoder if (use_gpu and gpu_encoder) else 'libx264 (CPU)'
                if progress_placeholder:
                    progress_placeholder.info(f"🔄 Converting to H.264 with {encoder_label}...")
                encoded = os.path.join(tmpdir, "encoded.mp4")
                vc_args = _ffmpeg_video_encoder_args(use_gpu, gpu_encoder)
                trim_args = _ffmpeg_trim_args(start_time, end_time) if has_time_range else []
                subprocess.run(
                    ['ffmpeg', *trim_args, '-i', downloaded_file,
                     *vc_args,
                     '-c:a', 'aac', '-b:a', '192k',
                     '-avoid_negative_ts', 'make_zero',
                     '-movflags', '+faststart',
                     '-y', encoded],
                    check=True, capture_output=True
                )
                shutil.move(encoded, output_path)
            elif has_time_range:
                # No transcode needed but still need precise trim
                if progress_placeholder:
                    progress_placeholder.info("✂️ Trimming segment...")
                trimmed = os.path.join(tmpdir, "trimmed.mp4")
                trim_args = _ffmpeg_trim_args(start_time, end_time)
                subprocess.run(
                    ['ffmpeg', *trim_args, '-i', downloaded_file,
                     '-c', 'copy',
                     '-avoid_negative_ts', 'make_zero',
                     '-movflags', '+faststart',
                     '-y', trimmed],
                    check=True, capture_output=True
                )
                shutil.move(trimmed, output_path)
            else:
                shutil.move(downloaded_file, output_path)
            return True
        except Exception as e:
            if "cancelled" in str(e).lower():
                return None
            st.error(f"Download error: {e}")
            return False


def _download_pytubefix(url, format_id, start_time, end_time, output_path,
                        stop_event, progress_placeholder,
                        needs_transcode=False, use_gpu=False, gpu_encoder=None):
    """
    Downloads with pytubefix.
    - format_id "adaptive:videoItag:audioItag" -> downloads video+audio separately and merges with ffmpeg
    - numeric format_id -> direct progressive stream
    """
    if not PYTUBEFIX_AVAILABLE:
        st.error("pytubefix not installed: pip install pytubefix")
        return False
    try:
        yt = PyTube(url)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Detect if it's adaptive format that requires merge
            if str(format_id).startswith('adaptive:'):
                _, video_itag_str, audio_itag_str = str(format_id).split(':')
                video_itag = int(video_itag_str)
                audio_itag = int(audio_itag_str) if audio_itag_str != 'None' else None

                video_stream = yt.streams.get_by_itag(video_itag)
                audio_stream = yt.streams.get_by_itag(audio_itag) if audio_itag else None

                if not video_stream:
                    st.error("pytubefix: video stream not found.")
                    return False

                if progress_placeholder:
                    progress_placeholder.info("⬇️ Downloading video (pytubefix)...")
                video_stream.download(output_path=tmpdir, filename="video_only.mp4")

                if stop_event and stop_event.is_set():
                    return None

                video_file = os.path.join(tmpdir, "video_only.mp4")
                final_input_video = video_file

                if audio_stream:
                    if progress_placeholder:
                        progress_placeholder.info("⬇️ Downloading audio (pytubefix)...")
                    audio_stream.download(output_path=tmpdir, filename="audio_only.mp4")
                    audio_file = os.path.join(tmpdir, "audio_only.mp4")

                    if stop_event and stop_event.is_set():
                        return None

                    # Merge video + audio with ffmpeg
                    # If stream is AV1/VP9, re-encode to H.264 for Windows
                    if progress_placeholder:
                        progress_placeholder.info("🔀 Merging and converting to H.264...")
                    merged = os.path.join(tmpdir, "merged.mp4")
                    # Probe codec of downloaded video
                    _needs_tc = needs_transcode
                    try:
                        probe = subprocess.run(
                            ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                             '-show_entries', 'stream=codec_name',
                             '-of', 'default=noprint_wrappers=1:nokey=1', video_file],
                            capture_output=True, text=True, timeout=10
                        )
                        detected = probe.stdout.strip().lower()
                        if detected in ('av1', 'av01', 'vp9', 'vp09'):
                            _needs_tc = True
                    except Exception:
                        pass
                    if _needs_tc:
                        encoder_label = gpu_encoder if (use_gpu and gpu_encoder) else 'libx264 (CPU)'
                        if progress_placeholder:
                            progress_placeholder.info(f"🔄 Converting to H.264 with {encoder_label}...")
                        vc_args = [*_ffmpeg_video_encoder_args(use_gpu, gpu_encoder),
                                   '-movflags', '+faststart']
                    else:
                        vc_args = ['-c:v', 'copy']
                    subprocess.run(
                        ['ffmpeg', '-i', video_file, '-i', audio_file,
                         *vc_args, '-c:a', 'aac', '-b:a', '192k', '-y', merged],
                        check=True, capture_output=True
                    )
                    final_input_video = merged

            else:
                # Progressive stream (video+audio in one)
                itag = int(format_id)
                stream = yt.streams.get_by_itag(itag)
                if not stream:
                    stream = (yt.streams.filter(progressive=True, file_extension='mp4')
                              .order_by('resolution').desc().first())
                if not stream:
                    st.error("pytubefix: no available stream found.")
                    return False
                if progress_placeholder:
                    progress_placeholder.info("⬇️ Downloading with pytubefix...")
                stream.download(output_path=tmpdir, filename="video.mp4")
                if stop_event and stop_event.is_set():
                    return None
                final_input_video = os.path.join(tmpdir, "video.mp4")

            # Time trim if range was specified
            # -ss BEFORE -i = precise input seeking (no initial black video)
            # -avoid_negative_ts make_zero resets timestamps at clip start
            if start_time > 0 or end_time > 0:
                if progress_placeholder:
                    progress_placeholder.info("✂️ Trimming segment with ffmpeg...")
                trim_args = _ffmpeg_trim_args(start_time, end_time)
                subprocess.run(
                    ['ffmpeg', *trim_args, '-i', final_input_video,
                     '-c', 'copy',
                     '-avoid_negative_ts', 'make_zero',
                     '-movflags', '+faststart',
                     '-y', output_path],
                    check=True, capture_output=True
                )
            else:
                shutil.move(final_input_video, output_path)

        return True
    except Exception as e:
        if "cancelled" in str(e).lower():
            return None
        st.error(f"pytubefix error: {e}")
        return False


def download_vod(url, format_id, start_time, end_time, output_path,
                 use_gpu=False, gpu_encoder=None,
                 stop_event=None, progress_placeholder=None,
                 platform='other', source='ytdlp', yt_browser=None,
                 needs_transcode=False):
    if source == 'pytubefix':
        return _download_pytubefix(url, format_id, start_time, end_time,
                                   output_path, stop_event, progress_placeholder,
                                   needs_transcode=needs_transcode,
                                   use_gpu=use_gpu, gpu_encoder=gpu_encoder)
    return _download_ytdlp(url, format_id, start_time, end_time, output_path,
                           platform, use_gpu, gpu_encoder,
                           stop_event, progress_placeholder, yt_browser,
                           needs_transcode=needs_transcode)


# ══════════════════════════════════════════════════════════════════
# MAIN UI
# ══════════════════════════════════════════════════════════════════

def main():
    defaults = {
        'video_info': None, 'current_url': "", 'download_complete': False,
        'downloading': False, 'stop_event': None, 'url_input_key': 0,
        'bottom_url': '', 'previous_new_url': '', 'yt_browser': None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    st.markdown(
        "<h1 style='color:#efeff1;text-align:center;margin-bottom:30px;'>"
        "🎬 Twitch, Kick & YouTube VOD Downloader</h1>",
        unsafe_allow_html=True
    )

    # YouTube Settings
    with st.expander("⚙️ YouTube Settings — open here if you have problems with YouTube"):
        st.markdown(
            "<p style='color:#adadb8;font-size:13px;'>"
            "YouTube blocks downloads without authentication. Select the browser "
            "where you have YouTube open with logged in session. "
            "<strong>Close the browser before trying</strong> to release the cookies.</p>",
            unsafe_allow_html=True
        )
        browser_options = ["None (try without cookies)"] + BROWSERS
        sel_browser_label = st.selectbox(
            "Browser for YouTube cookies",
            options=browser_options, index=0, key="browser_selector"
        )
        st.session_state.yt_browser = (
            None if sel_browser_label == "None (try without cookies)"
            else sel_browser_label
        )
        if PYTUBEFIX_AVAILABLE:
            st.success("✅ pytubefix available as automatic fallback.")
        else:
            st.warning("⚠️ pytubefix not installed. Fallback disabled. Run: pip install pytubefix")

    # URL Input
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    url_key = f"main_url_input_{st.session_state.url_input_key}"
    url = st.text_input(
        "URL", value=st.session_state.current_url,
        placeholder="https://www.twitch.tv/videos/...  |  https://kick.com/video/...  |  https://youtube.com/watch?v=...",
        label_visibility="collapsed", key=url_key,
    )
    if url != st.session_state.current_url:
        st.session_state.current_url = url

    if st.button("🔍 Process Video", use_container_width=True) and url:
        with st.spinner("Extracting video information..."):
            st.session_state.video_info = get_video_info(url, yt_browser=st.session_state.yt_browser)
            st.session_state.download_complete = False
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Video Info
    if st.session_state.video_info:
        info = st.session_state.video_info
        platform = info.get('platform', 'other')

        st.markdown('<div class="main-container">', unsafe_allow_html=True)
        live_badge = "🔴" if info['is_live'] else ""
        st.markdown(platform_badge_html(platform), unsafe_allow_html=True)
        st.markdown(
            f'<div class="vod-title">{info["title"]} <span class="live-badge">{live_badge}</span></div>',
            unsafe_allow_html=True
        )
        st.markdown(
            f"<p style='color:#adadb8;margin-bottom:16px;'>Duration: {info['duration_formatted']} | Channel: {info['uploader']}</p>",
            unsafe_allow_html=True
        )

        st.markdown('<div class="section-label">Quality</div>', unsafe_allow_html=True)
        if info['formats']:
            fmt_opts = {f['display']: f for f in info['formats']}
            sel_quality = st.selectbox("Quality", options=list(fmt_opts.keys()), label_visibility="collapsed")
            sel_format = fmt_opts[sel_quality]
        else:
            sel_format = {'format_id': 'best', 'quality': 'Best quality', 'source': 'ytdlp'}

        st.markdown('<div class="section-label">Time Range</div>', unsafe_allow_html=True)
        duration = info['duration']
        time_range = st.slider(
            "Range", min_value=0, max_value=max(int(duration), 1),
            value=(0, max(int(duration), 1)), format="%d s", label_visibility="collapsed"
        )
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="section-label">Start</div>', unsafe_allow_html=True)
            start_input = st.text_input("Start", value=format_duration(time_range[0]), label_visibility="collapsed")
        with c2:
            st.markdown('<div class="section-label">End</div>', unsafe_allow_html=True)
            end_input = st.text_input("End", value=format_duration(time_range[1]), label_visibility="collapsed")
        try:
            start_sec = parse_time_to_seconds(start_input)
            end_sec   = parse_time_to_seconds(end_input)
        except Exception:
            start_sec, end_sec = time_range

        gpu_encoders = check_gpu_encoder()
        use_gpu, sel_encoder = False, None
        if gpu_encoders:
            st.markdown("---")
            st.markdown('<div class="section-label">GPU Acceleration (Optional)</div>', unsafe_allow_html=True)
            use_gpu = st.checkbox("Enable GPU acceleration", value=False)
            if use_gpu:
                names = [e[0] for e in gpu_encoders]
                sel_gpu = st.selectbox("GPU Encoder", options=names, label_visibility="collapsed")
                sel_encoder = next(e[1] for e in gpu_encoders if e[0] == sel_gpu)
                st.info(f"Using {sel_gpu}")

        st.markdown("<br>", unsafe_allow_html=True)

        if st.session_state.downloading:
            _, sc, _ = st.columns([1, 2, 1])
            with sc:
                if st.button("🛑 Stop Download", use_container_width=True, type="secondary"):
                    if st.session_state.stop_event:
                        st.session_state.stop_event.set()
                    st.session_state.downloading = False
                    st.warning("Download cancelled"); st.rerun()

            prog = st.empty()

            if end_sec <= start_sec:
                st.error("End time must be greater than start time.")
                st.session_state.downloading = False
            else:
                safe_title = re.sub(r'[<>:"/\\|?*]', '', info['title'])[:50]
                out_name = f"{safe_title}_{format_duration(start_sec).replace(':','-')}_{format_duration(end_sec).replace(':','-')}.mp4"

                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                    tmp_path = tmp.name
                st.session_state.stop_event = threading.Event()

                ok = download_vod(
                    st.session_state.current_url,
                    sel_format['format_id'], start_sec, end_sec, tmp_path,
                    use_gpu, sel_encoder,
                    stop_event=st.session_state.stop_event,
                    progress_placeholder=prog,
                    platform=platform,
                    source=sel_format.get('source', 'ytdlp'),
                    yt_browser=st.session_state.yt_browser,
                    needs_transcode=sel_format.get('needs_transcode', False),
                )
                st.session_state.downloading = False
                st.session_state.stop_event = None

                if ok is True:
                    prog.empty(); st.success("✅ Download complete!")
                    with open(tmp_path, "rb") as f: video_bytes = f.read()
                    st.download_button("📥 Save Video", data=video_bytes,
                                       file_name=out_name, mime="video/mp4",
                                       use_container_width=True)
                    try: os.unlink(tmp_path)
                    except: pass
                elif ok is None:
                    prog.empty(); st.warning("⚠️ Download cancelled")
                    try: os.unlink(tmp_path)
                    except: pass
                else:
                    prog.empty(); st.error("❌ Download failed")
                    try: os.unlink(tmp_path)
                    except: pass
        else:
            _, dc, _ = st.columns([1, 2, 1])
            with dc:
                if st.button("⬇️ Download", use_container_width=True):
                    st.session_state.downloading = True; st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # Bottom section
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="secondary-section">', unsafe_allow_html=True)
    st.markdown('<div class="secondary-title">Download another video</div>', unsafe_allow_html=True)
    ci, cb = st.columns([4, 1])
    with ci:
        new_url = st.text_input("New URL", placeholder="Twitch, Kick or YouTube URL…",
                                label_visibility="collapsed", key="new_url_input")
        if new_url != st.session_state.get('bottom_url', ''):
            st.session_state.bottom_url = new_url
        if new_url and new_url != st.session_state.get('previous_new_url', ''):
            st.session_state.previous_new_url = new_url
            st.session_state.video_info = None
            st.session_state.url_input_key += 1
            st.session_state.current_url = new_url
            st.rerun()
    with cb:
        if st.button("Download", use_container_width=True, key="dl_another"):
            u2 = st.session_state.get('bottom_url', '')
            if u2:
                st.session_state.current_url = u2
                st.session_state.video_info = None
                st.session_state.bottom_url = ''
                if 'new_url_input' in st.session_state: del st.session_state['new_url_input']
                with st.spinner("Extracting information..."):
                    st.session_state.video_info = get_video_info(u2, yt_browser=st.session_state.yt_browser)
                st.rerun()
            else:
                st.error("Enter a valid URL.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
        "<div style='text-align:center;margin-top:3rem;padding:1rem;"
        "color:#999;font-size:0.9rem;border-top:1px solid #303032;'>"
        "<p>Created by <strong>Diego Ivan Perea Montealegre</strong></p></div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()