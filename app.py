"""
Twitch & Kick VOD Downloader with Streamlit
Supports GPU acceleration via FFmpeg (NVENC/AMF/VAAPI) when available
"""

import streamlit as st
import yt_dlp
import os
import re
import subprocess
import shutil
from datetime import timedelta
from pathlib import Path
import tempfile

# Page configuration
st.set_page_config(
    page_title="Twitch & Kick VOD Downloader",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for dark theme matching the screenshot
st.markdown("""
<style>
    /* Dark theme styling */
    .stApp {
        background-color: #0e0e10;
    }
    
    .main-container {
        background-color: #1f1f23;
        border-radius: 8px;
        padding: 24px;
        margin-bottom: 16px;
    }
    
    /* Title styling */
    .vod-title {
        color: #efeff1;
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .live-badge {
        color: #ff4444;
        font-size: 14px;
    }
    
    /* Section headers */
    .section-label {
        color: #adadb8;
        font-size: 12px;
        font-weight: 600;
        text-transform: none;
        margin-bottom: 6px;
    }
    
    /* Input fields */
    .stTextInput > div > div > input {
        background-color: #18181b !important;
        border: 1px solid #303032 !important;
        color: #efeff1 !important;
        border-radius: 6px !important;
    }
    
    /* Selectbox */
    .stSelectbox > div > div > div {
        background-color: #18181b !important;
        border: 1px solid #303032 !important;
        color: #efeff1 !important;
        border-radius: 6px !important;
    }
    
    /* Slider */
    .stSlider > div > div > div > div {
        background-color: #9146ff !important;
    }

    /* === SLIDER MÁS GRUESO === */

    /* Barra principal del slider (track) */
    .stSlider > div > div > div {
        height: 8px !important;  /* Grosor de la barra, cambia este valor */
    }

    

    /* Track activo (parte morada/coloreada) */
    .stSlider > div > div > div > div[data-baseweb="slider"] > div {
        height: 8px !important;
        border-radius: 4px !important;
    }

    /* Las bolas/thumbs del slider */
    .stSlider > div > div > div > div[data-testid="stThumbValue"],
    [data-baseweb="slider"] [role="slider"] {
        width: 22px !important;       /* Ancho de la bola */
        height: 22px !important;      /* Alto de la bola */
        background-color: #9146ff !important;
        border: 3px solid #efeff1 !important;
        border-radius: 50% !important;
        box-shadow: 0 0 8px rgba(145, 70, 255, 0.6) !important;
        top: -7px !important;         /* Centra la bola con la barra */
    }

   
    
    /* Download button */
    .stButton > button {
        background-color: #9146ff !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
    }
    
    .stButton > button:hover {
        background-color: #772ce8 !important;
    }
    
    /* Secondary section */
    .secondary-section {
        background-color: #1f1f23;
        border-radius: 8px;
        padding: 24px;
        text-align: center;
    }
    
    .secondary-title {
        color: #efeff1;
        font-size: 20px;
        font-weight: 600;
        margin-bottom: 20px;
    }
    
    /* Ad placeholder */
    .ad-container {
        background-color: #18181b;
        border: 1px solid #303032;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #adadb8;
        font-size: 18px;
        min-height: 200px;
    }
    
    /* Download icon */
    .download-icon {
        margin-right: 6px;
    }
    
    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def format_duration(seconds):
    """Convert seconds to HH:MM:SS format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def parse_time_to_seconds(time_str):
    """Parse HH:MM:SS or MM:SS to seconds"""
    parts = time_str.strip().split(":")
    if len(parts) == 3:
        hours, minutes, seconds = map(int, parts)
        return hours * 3600 + minutes * 60 + seconds
    elif len(parts) == 2:
        minutes, seconds = map(int, parts)
        return minutes * 60 + seconds
    elif len(parts) == 1:
        return int(parts[0])
    return 0


def get_video_info(url):
    """Extract video information using yt-dlp"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Get available formats/qualities
            formats = []
            if 'formats' in info:
                for f in info['formats']:
                    if f.get('vcodec') != 'none' and f.get('height'):
                        quality = f"{f.get('height', 'unknown')}p{f.get('fps', '')}"
                        format_id = f.get('format_id', '')
                        filesize = f.get('filesize') or f.get('filesize_approx', 0)
                        formats.append({
                            'format_id': format_id,
                            'quality': quality,
                            'height': f.get('height'),
                            'fps': f.get('fps', 30),
                            'filesize': filesize,
                            'display': f"{quality} ~ {filesize / (1024**3):.2f} GB" if filesize else quality
                        })
            
            # Remove duplicates and sort by quality
            seen = set()
            unique_formats = []
            for f in sorted(formats, key=lambda x: (x['height'], x['fps']), reverse=True):
                key = (f['height'], f['fps'])
                if key not in seen:
                    seen.add(key)
                    unique_formats.append(f)
            
            duration = info.get('duration', 0)
            
            return {
                'title': info.get('title', 'Unknown Title'),
                'uploader': info.get('uploader', 'Unknown'),
                'duration': duration,
                'duration_formatted': format_duration(duration),
                'thumbnail': info.get('thumbnail', ''),
                'formats': unique_formats,
                'is_live': info.get('is_live', False),
            }
    except Exception as e:
        st.error(f"Error extracting video info: {str(e)}")
        return None


def check_gpu_encoder():
    """Check available GPU encoders"""
    encoders = []
    
    # Check for NVIDIA NVENC
    try:
        result = subprocess.run(
            ['ffmpeg', '-encoders'],
            capture_output=True,
            text=True,
            timeout=5
        )
        output = result.stdout
        
        if 'h264_nvenc' in output:
            encoders.append(('NVIDIA NVENC', 'h264_nvenc'))
        if 'h264_amf' in output:
            encoders.append(('AMD AMF', 'h264_amf'))
        if 'h264_vaapi' in output:
            encoders.append(('Intel VAAPI', 'h264_vaapi'))
        if 'h264_qsv' in output:
            encoders.append(('Intel QuickSync', 'h264_qsv'))
    except:
        pass
    
    return encoders


def download_vod(url, format_id, start_time, end_time, output_path, use_gpu=False, gpu_encoder=None, stop_event=None, progress_placeholder=None):
    """Download VOD segment with optional GPU acceleration for re-encoding and cancellation support"""
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_file = os.path.join(tmpdir, "temp_download.mp4")
        
        # Progress hook for yt-dlp
        def progress_hook(d):
            if stop_event and stop_event.is_set():
                raise Exception("Download cancelled by user")
            
            if d['status'] == 'downloading' and progress_placeholder:
                percent = d.get('_percent_str', '0%')
                speed = d.get('_speed_str', 'N/A')
                eta = d.get('_eta_str', 'N/A')
                progress_placeholder.info(f"⬇️ Downloading... {percent} | Speed: {speed} | ETA: {eta}")
        
        # First, download the full video or segment using yt-dlp
        ydl_opts = {
            'format': format_id,
            'outtmpl': temp_file,
            'quiet': True,
            'no_warnings': True,
            'external_downloader': 'ffmpeg',
            'external_downloader_args': {
                'ffmpeg_i': ['-ss', str(start_time), '-to', str(end_time)]
            } if start_time > 0 or end_time > 0 else {},
            'progress_hooks': [progress_hook],
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Check if cancelled
            if stop_event and stop_event.is_set():
                return False
            
            # If GPU encoding requested and available
            if use_gpu and gpu_encoder:
                if progress_placeholder:
                    progress_placeholder.info("🎬 Encoding with GPU...")
                
                temp_encoded = os.path.join(tmpdir, "temp_encoded.mp4")
                
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-i', temp_file,
                    '-c:v', gpu_encoder,
                    '-preset', 'fast',
                    '-crf', '23',
                    '-c:a', 'copy',
                    '-y',
                    temp_encoded
                ]
                
                subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
                shutil.move(temp_encoded, output_path)
            else:
                # Just copy the file
                shutil.move(temp_file, output_path)
                
            return True
            
        except Exception as e:
            if "cancelled" in str(e).lower():
                return None  # Return None for cancelled
            st.error(f"Download error: {str(e)}")
            return False


def main():
    # Initialize session state
    if 'video_info' not in st.session_state:
        st.session_state.video_info = None
    if 'current_url' not in st.session_state:
        st.session_state.current_url = ""
    if 'download_complete' not in st.session_state:
        st.session_state.download_complete = False
    if 'downloading' not in st.session_state:
        st.session_state.downloading = False
    if 'stop_event' not in st.session_state:
        st.session_state.stop_event = None
    if 'url_input_key' not in st.session_state:
        st.session_state.url_input_key = 0
    
    # App title
    st.markdown("<h1 style='color: #efeff1; text-align: center; margin-bottom: 30px;'>🎬 Twitch & Kick VOD Downloader</h1>", unsafe_allow_html=True)
    
    # Main content area
    col1 = st.container()
    
    with col1:
        st.markdown('<div class="main-container">', unsafe_allow_html=True)
        
        # URL Input section - always visible at top
        # Use dynamic key to force recreation when clearing
        url_input_key = f"main_url_input_{st.session_state.url_input_key}"
        url = st.text_input(
            "Enter Twitch or Kick VOD URL",
            value=st.session_state.current_url,
            placeholder="https://www.twitch.tv/videos/... or https://kick.com/video/...",
            label_visibility="collapsed",
            key=url_input_key
        )
        
        # Update current_url in session state when user types
        if url != st.session_state.current_url:
            st.session_state.current_url = url
        
        # Process button
        if st.button("🔍 Process Video", use_container_width=True) and url:
            with st.spinner("Extracting video information..."):
                st.session_state.video_info = get_video_info(url)
                st.session_state.download_complete = False
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        if st.session_state.video_info:
            info = st.session_state.video_info
            
            st.markdown('<div class="main-container">', unsafe_allow_html=True)
            
            # Title with live indicator
            live_indicator = "🔴" if info['is_live'] else ""
            st.markdown(
                f'<div class="vod-title">{info["title"]} <span class="live-badge">{live_indicator}</span></div>',
                unsafe_allow_html=True
            )
            
            # Duration display
            st.markdown(f"<p style='color: #adadb8; margin-bottom: 16px;'>Duration: {info['duration_formatted']}</p>", unsafe_allow_html=True)
            
            # Quality selection
            st.markdown('<div class="section-label">Quality</div>', unsafe_allow_html=True)
            
            if info['formats']:
                format_options = {f['display']: f for f in info['formats']}
                selected_quality = st.selectbox(
                    "Quality",
                    options=list(format_options.keys()),
                    label_visibility="collapsed"
                )
                selected_format = format_options[selected_quality]
            else:
                selected_format = {'format_id': 'best', 'quality': 'Best Quality'}
            
            # Time range slider
            st.markdown('<div class="section-label">Time Range</div>', unsafe_allow_html=True)
            
            duration = info['duration']
            
            # Slider for time range
            time_range = st.slider(
                "Select time range",
                min_value=0,
                max_value=int(duration),
                value=(0, int(duration)),
                format="%d s",
                label_visibility="collapsed"
            )
            
            # Time input fields
            col_start, col_end = st.columns(2)
            
            with col_start:
                st.markdown('<div class="section-label">Start Time</div>', unsafe_allow_html=True)
                start_input = st.text_input(
                    "Start Time",
                    value=format_duration(time_range[0]),
                    label_visibility="collapsed"
                )
            
            with col_end:
                st.markdown('<div class="section-label">End Time</div>', unsafe_allow_html=True)
                end_input = st.text_input(
                    "End Time",
                    value=format_duration(time_range[1]),
                    label_visibility="collapsed"
                )
            
            # Sync slider with text inputs
            try:
                start_seconds = parse_time_to_seconds(start_input)
                end_seconds = parse_time_to_seconds(end_input)
            except:
                start_seconds = time_range[0]
                end_seconds = time_range[1]
            
            # GPU acceleration option
            gpu_encoders = check_gpu_encoder()
            use_gpu = False
            selected_encoder = None
            
            if gpu_encoders:
                st.markdown("---", unsafe_allow_html=True)
                st.markdown('<div class="section-label">GPU Acceleration (Optional)</div>', unsafe_allow_html=True)
                
                encoder_names = [e[0] for e in gpu_encoders]
                use_gpu = st.checkbox("Enable GPU acceleration for faster processing", value=False)
                
                if use_gpu:
                    selected_gpu = st.selectbox(
                        "Select GPU encoder",
                        options=encoder_names,
                        label_visibility="collapsed"
                    )
                    selected_encoder = next(e[1] for e in gpu_encoders if e[0] == selected_gpu)
                    st.info(f"Using {selected_gpu} for accelerated encoding")
            
            # Download button section
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Handle download process
            if st.session_state.downloading:
                # Show stop button during download
                stop_col1, stop_col2, stop_col3 = st.columns([1, 2, 1])
                with stop_col2:
                    if st.button("🛑 Stop Download", use_container_width=True, type="secondary"):
                        if st.session_state.stop_event:
                            st.session_state.stop_event.set()
                        st.session_state.downloading = False
                        st.warning("Download cancelled")
                        st.rerun()
                
                # Progress placeholder
                progress_placeholder = st.empty()
                
                # Perform download
                if end_seconds <= start_seconds:
                    st.error("End time must be greater than start time!")
                    st.session_state.downloading = False
                else:
                    # Sanitize filename
                    safe_title = re.sub(r'[<>:"/\\|?*]', '', info['title'])[:50]
                    output_filename = f"{safe_title}_{format_duration(start_seconds).replace(':', '-')}_{format_duration(end_seconds).replace(':', '-')}.mp4"
                    
                    # Create temp file for download
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                        temp_output_path = tmp_file.name
                    
                    # Create stop event for this download
                    import threading
                    st.session_state.stop_event = threading.Event()
                    
                    success = download_vod(
                        st.session_state.current_url,
                        selected_format['format_id'],
                        start_seconds,
                        end_seconds,
                        temp_output_path,
                        use_gpu,
                        selected_encoder,
                        stop_event=st.session_state.stop_event,
                        progress_placeholder=progress_placeholder
                    )
                    
                    st.session_state.downloading = False
                    st.session_state.stop_event = None
                    
                    if success is True:
                        progress_placeholder.empty()
                        st.success(f"✅ Download complete!")
                        
                        # Read file for download button
                        with open(temp_output_path, "rb") as f:
                            video_data = f.read()
                        
                        st.download_button(
                            label="📥 Click to Save Video",
                            data=video_data,
                            file_name=output_filename,
                            mime="video/mp4",
                            use_container_width=True
                        )
                        
                        # Cleanup temp file after download
                        try:
                            os.unlink(temp_output_path)
                        except:
                            pass
                    elif success is None:
                        progress_placeholder.empty()
                        st.warning("⚠️ Download was cancelled")
                        # Cleanup temp file
                        try:
                            os.unlink(temp_output_path)
                        except:
                            pass
                    else:
                        progress_placeholder.empty()
                        st.error("❌ Download failed")
                        # Cleanup temp file
                        try:
                            os.unlink(temp_output_path)
                        except:
                            pass
            else:
                # Show start download button
                download_col1, download_col2, download_col3 = st.columns([1, 2, 1])
                with download_col2:
                    if st.button("⬇️ Download", use_container_width=True):
                        st.session_state.downloading = True
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Bottom section - Download Another Video
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="secondary-section">', unsafe_allow_html=True)
    st.markdown('<div class="secondary-title">Download Another Twitch and Kick Video</div>', unsafe_allow_html=True)
    
    col_input, col_button = st.columns([4, 1])
    
    with col_input:
        new_url = st.text_input(
            "Enter a twitch video link",
            placeholder="Enter a twitch video link",
            label_visibility="collapsed",
            key="new_url_input"
        )
        
        # Store new_url in session state as user types
        if new_url != st.session_state.get('bottom_url', ''):
            st.session_state.bottom_url = new_url
        
        # Clear previous video info when user starts typing new URL
        if new_url and new_url != st.session_state.get('previous_new_url', ''):
            st.session_state.previous_new_url = new_url
            if st.session_state.video_info is not None:
                st.session_state.video_info = None
            # Force recreation of top input by changing its key
            st.session_state.url_input_key += 1
            st.session_state.current_url = new_url
            st.rerun()
    
    with col_button:
        if st.button("Download", use_container_width=True, key="download_another"):
            # Use stored URL from session state
            url_to_process = st.session_state.get('bottom_url', '')
            # Debug output
            st.write(f"Debug: bottom_url value = '{url_to_process}'")
            st.write(f"Debug: current_url value = '{st.session_state.current_url}'")
            if url_to_process:
                # Update current_url and process new video
                st.session_state.current_url = url_to_process
                st.session_state.video_info = None
                st.session_state.download_complete = False
                # Clear the bottom input
                if 'new_url_input' in st.session_state:
                    del st.session_state['new_url_input']
                st.session_state.bottom_url = ''
                # Process the new URL immediately
                with st.spinner("Extracting video information..."):
                    st.session_state.video_info = get_video_info(url_to_process)
                st.rerun()
            else:
                st.error("Please enter a valid URL in the input field")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        """
            <div style='text-align: center; margin-top: 3rem; padding: 1rem; color: #999; font-size: 0.9rem; border-top: 1px solid #eee;'>
                <p>Created by <strong>Diego Ivan Perea Montealegre</strong> </p>
            </div>
            """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
