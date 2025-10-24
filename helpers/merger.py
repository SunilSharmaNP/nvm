# bulletproof_merger_enhanced.py - Enhanced with subtitle/audio merging and custom filename support
import asyncio
import os
import time
import json
import logging
import re
import shutil
from typing import List, Optional, Dict, Any
from collections import Counter
from config import config
from helpers.utils import get_video_properties, get_progress_bar, get_time_left
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# --- Progress throttling (unchanged) ---
last_edit_time = {}
EDIT_THROTTLE_SECONDS = 2.0
async def smart_progress_editor(status_message, text: str):
    if not status_message or not hasattr(status_message, 'chat'):
        return
    message_key = f"{status_message.chat.id}_{status_message.id}"
    now = time.time()
    last_time = last_edit_time.get(message_key, 0)
    if (now - last_time) > EDIT_THROTTLE_SECONDS:
        try:
            await status_message.edit_text(text)
            last_edit_time[message_key] = now
        except Exception as e:
            logger.debug(f"Progress update failed: {e}")
async def get_detailed_video_info(file_path: str) -> Optional[Dict[str, Any]]:
    """Get comprehensive video information using ffprobe with normalized parameters"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', file_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"ffprobe failed for {file_path}: {stderr.decode()}")
            return None
            
        data = json.loads(stdout.decode())
        
        video_streams = [s for s in data.get('streams', []) if s.get('codec_type') == 'video']
        audio_streams = [s for s in data.get('streams', []) if s.get('codec_type') == 'audio']
        subtitle_streams = [s for s in data.get('streams', []) if s.get('codec_type') == 'subtitle']
        
        if not video_streams:
            logger.error(f"No video stream found in {file_path}")
            return None
            
        video_stream = video_streams[0]
        audio_stream = audio_streams[0] if audio_streams else None
        
        # Parse frame rate properly with rounding for comparison
        fps_str = video_stream.get('r_frame_rate', '30/1')
        if '/' in fps_str:
            num, den = fps_str.split('/')
            fps = round(float(num) / float(den), 2) if int(den) != 0 else 30.0
        else:
            fps = round(float(fps_str), 2)
            
        # Get normalized codec names for comparison
        video_codec = video_stream.get('codec_name', '').lower()
        audio_codec = audio_stream.get('codec_name', '').lower() if audio_stream else None
        
        # Get pixel format with fallback
        pixel_format = video_stream.get('pix_fmt', 'yuv420p')
        
        # Get sample rate with fallback
        audio_sample_rate = int(audio_stream.get('sample_rate', 48000)) if audio_stream else 48000
        
        # Get container format (critical for compatibility check)
        container = data['format'].get('format_name', '').lower()
        
        return {
            'has_video': True,
            'has_audio': audio_stream is not None,
            'has_subtitles': len(subtitle_streams) > 0,
            'width': int(video_stream['width']),
            'height': int(video_stream['height']),
            'fps': fps,
            'video_codec': video_codec,
            'audio_codec': audio_codec,
            'pixel_format': pixel_format,
            'duration': float(data['format'].get('duration', 0)),
            'bitrate': video_stream.get('bit_rate'),
            'audio_sample_rate': audio_sample_rate,
            'container': container,
            'file_path': file_path,  # Store original path for debugging
            'audio_streams_count': len(audio_streams),
            'subtitle_streams_count': len(subtitle_streams)
        }
        
    except Exception as e:
        logger.error(f"Failed to get video info for {file_path}: {e}")
        return None
def videos_are_identical_for_merge(video_infos: List[Dict[str, Any]]) -> bool:
    """Check if all videos have identical parameters for fast merge"""
    if not video_infos or len(video_infos) < 2:
        return False
    
    reference = video_infos[0]
    
    # Critical parameters that must match for lossless concat
    critical_params = [
        'width', 'height', 'fps', 'video_codec', 
        'audio_codec', 'pixel_format', 'audio_sample_rate'
    ]
    
    for video_info in video_infos[1:]:
        for param in critical_params:
            ref_val = reference.get(param)
            vid_val = video_info.get(param)
            
            # Handle None values (missing audio)
            if ref_val is None and vid_val is None:
                continue
            if ref_val is None or vid_val is None:
                logger.info(f"Parameter mismatch: {param} - {ref_val} vs {vid_val}")
                return False
            
            # Special handling for fps comparison (allow small differences)
            if param == 'fps':
                if abs(ref_val - vid_val) > 0.1:
                    logger.info(f"FPS mismatch: {ref_val} vs {vid_val}")
                    return False
            else:
                if ref_val != vid_val:
                    logger.info(f"Parameter mismatch: {param} - {ref_val} vs {vid_val}")
                    return False
    
    return True
def requires_container_remux(video_infos: List[Dict[str, Any]], target_container: str = 'mkv') -> bool:
    """Check if container remux is needed for compatibility"""
    for info in video_infos:
        container = info.get('container', '')
        # Check for container incompatibility issues
        if container != target_container:
            logger.info(f"Container remux needed: {container} -> {target_container}")
            return True
    return False
async def get_total_duration(video_files: List[str]) -> float:
    """Calculate total duration of all video files for progress calculation"""
    total_duration = 0.0
    for file_path in video_files:
        try:
            cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', 
                   '-of', 'csv=p=0', file_path]
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                duration = float(stdout.decode().strip())
                total_duration += duration
        except:
            pass
    return total_duration
async def track_merge_progress(process, total_duration: float, status_message, merge_type: str):
    """Track ffmpeg merge progress and update status"""
    start_time = time.time()
    last_update = 0
    
    while True:
        try:
            line = await asyncio.wait_for(process.stderr.readline(), timeout=1.0)
            if not line:
                break
                
            line = line.decode().strip()
            
            # Parse time progress from ffmpeg stderr
            time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2}\.\d{2})', line)
            if time_match and total_duration > 0:
                hours, minutes, seconds = time_match.groups()
                current_time = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                
                progress = min(current_time / total_duration, 1.0)
                elapsed = time.time() - start_time
                
                if time.time() - last_update > 2.0:
                    eta = (elapsed / progress - elapsed) if progress > 0.01 else 0
                    
                    progress_text = (
                        f"🎶 **{merge_type} in Progress...**\n"
                        f"➤ {get_progress_bar(progress)} `{progress:.1%}`\n"
                        f"➤ **Time Processed:** `{int(current_time)}s` / `{int(total_duration)}s`\n"
                        f"➤ **Elapsed:** `{int(elapsed)}s`\n"
                        f"➤ **ETA:** `{int(eta)}s remaining`"
                    )
                    
                    await smart_progress_editor(status_message, progress_text)
                    last_update = time.time()
                    
        except asyncio.TimeoutError:
            continue
        except Exception as e:
            logger.debug(f"Progress tracking error: {e}")
            break
async def remux_to_compatible_format(input_path: str, output_path: str, status_message, file_index: int, total_files: int) -> bool:
    """Remux to MKV maintaining all streams"""
    try:
        await smart_progress_editor(status_message, 
            f"📦 **Remuxing video {file_index}/{total_files} for compatibility...**\n"
            f"➤ `{os.path.basename(input_path)}`\n"
            f"➤ **Converting to MKV container (no re-encoding)**"
        )
        
        # Use explicit stream mapping to preserve all streams
        cmd = [
            'ffmpeg', '-hide_banner', '-loglevel', 'info', '-y',
            '-i', input_path,
            
            # Map all streams
            '-map', '0',
            
            # Stream copy (no re-encoding)
            '-c', 'copy',
            
            # MKV container
            '-f', 'matroska',
            
            # Progress reporting
            '-progress', 'pipe:2',
            
            output_path
        ]
        
        logger.info(f"Remux command: {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"Successfully remuxed: {input_path}")
            return True
        else:
            error_output = stderr.decode().strip()
            logger.error(f"Remux failed for {input_path}: {error_output}")
            return False
            
    except Exception as e:
        logger.error(f"Remux error for {input_path}: {e}")
        return False
async def fast_merge_identical_videos(video_files: List[str], user_id: int, status_message, video_infos: List[Dict[str, Any]], output_filename: str = None) -> Optional[str]:
    """Fast merge with container compatibility fixes - outputs MKV"""
    user_download_dir = os.path.join(config.DOWNLOAD_DIR, str(user_id))
    
    # Check if container remux is needed (to MKV)
    needs_remux = requires_container_remux(video_infos, 'mkv')
    
    if needs_remux:
        await status_message.edit_text("📦 **Container compatibility issue detected! Remuxing files...**")
        
        # Remux files to compatible format (MKV)
        remuxed_files = []
        for i, (file_path, info) in enumerate(zip(video_files, video_infos)):
            remuxed_path = os.path.join(user_download_dir, f"remux_{i}_{int(time.time())}.mkv")
            
            success = await remux_to_compatible_format(file_path, remuxed_path, status_message, i+1, len(video_files))
            if not success:
                await status_message.edit_text(f"❌ **Failed to remux video {i+1}!**")
                return None
            remuxed_files.append(remuxed_path)
        
        # Use remuxed files for concat
        video_files = remuxed_files
    
    # Generate output filename
    if output_filename:
        base_name = os.path.splitext(output_filename)[0]  # Remove any existing extension
        output_path = os.path.join(user_download_dir, f"{base_name}.mkv")
    else:
        output_path = os.path.join(user_download_dir, f"Merged_By_SSBots_{int(time.time())}.mkv")
    
    inputs_file = os.path.join(user_download_dir, f"inputs_{int(time.time())}.txt")
    
    try:
        await status_message.edit_text("🚀 **Starting ultra-fast merge...**")
        
        # Get total duration for progress calculation
        total_duration = await get_total_duration(video_files)
        
        # Create inputs file with proper escaping
        with open(inputs_file, 'w', encoding='utf-8') as f:
            for file_path in video_files:
                abs_path = os.path.abspath(file_path)
                formatted_path = abs_path.replace("'", "'\''")
                f.write(f"file '{formatted_path}'\n")
        
        # Enhanced concat command with explicit stream mapping for MKV
        cmd = [
            'ffmpeg', '-hide_banner', '-loglevel', 'info', '-y',
            '-f', 'concat', '-safe', '0', '-i', inputs_file,
            
            # Map all streams
            '-map', '0',
            
            '-c', 'copy',   # Stream copy (no re-encoding)
            '-f', 'matroska',  # Force MKV output
            '-progress', 'pipe:2',
            output_path
        ]
        
        logger.info(f" fast merge command: {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        
        # Start progress tracking
        progress_task = asyncio.create_task(
            track_merge_progress(process, total_duration, status_message, "Fast Merge")
        )
        
        stdout, stderr = await process.communicate()
        progress_task.cancel()
        
        # Cleanup
        try:
            os.remove(inputs_file)
            if needs_remux:
                for remuxed_file in video_files:
                    os.remove(remuxed_file)
        except:
            pass
        
        if process.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            file_size = os.path.getsize(output_path)
            
            # Verify output has both video and audio
            output_info = await get_detailed_video_info(output_path)
            if output_info and output_info['has_video'] and output_info['has_audio']:
                await status_message.edit_text(
                    f"✅ **Fast Merge Completed Successfully!**\n"
                    f"➤ **Output:** `{os.path.basename(output_path)}`\n"
                    f"➤ **Size:** `{file_size / (1024*1024):.1f} MB`\n"
                    f"➤ **Streams:** Video ✅ + Audio ✅\n"
                    f"➤ **Mode:** {'Container-fixed' if needs_remux else 'Ultra-fast'} merge"
                )
                return output_path
            else:
                logger.error("Output verification failed: missing video or audio stream")
                await status_message.edit_text("⚠️ **Fast merge produced incomplete output, falling back to standardization...**")
                return None
        else:
            error_output = stderr.decode().strip()
            logger.error(f"Fast merge failed: {error_output}")
            await status_message.edit_text("⚠️ **Fast merge failed, falling back to standardization...**")
            return None
            
    except Exception as e:
        logger.error(f"Fast merge error: {e}")
        try:
            os.remove(inputs_file)
        except:
            pass
        await status_message.edit_text("⚠️ **Fast merge failed, falling back to standardization...**")
        return None
async def standardize_video_file(input_path: str, output_path: str, target_params: Dict[str, Any]) -> bool:
    """Standardize a video file to target parameters (simplified version without progress)"""
    try:
        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
            '-i', input_path,
            
            # Video processing
            '-vf', f'scale={target_params["width"]}:{target_params["height"]}:force_original_aspect_ratio=decrease,pad={target_params["width"]}:{target_params["height"]}:(ow-iw)/2:(oh-ih)/2,fps={target_params["fps"]},format={target_params["pixel_format"]}',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            
            # Audio processing
            '-c:a', 'aac', '-ar', str(target_params['audio_sample_rate']), '-ac', '2', '-b:a', '128k',
            
            # Stream mapping
            '-map', '0:v:0',
            '-map', '0:a:0',
            
            # MKV container
            '-f', 'matroska',
            
            output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"Successfully standardized: {input_path}")
            return True
        else:
            logger.error(f"Standardization failed for {input_path}: {stderr.decode()}")
            return False
            
    except Exception as e:
        logger.error(f"Standardization error for {input_path}: {e}")
        return False
async def merge_videos(video_files: List[str], user_id: int, status_message, output_filename: str = None) -> Optional[str]:
    """
    OPTIMIZED video merger - tries fast merge first, falls back to standardization
    Outputs MKV format and supports custom filename
    """
    if len(video_files) < 2:
        await status_message.edit_text("❌ Need at least 2 video files to merge!")
        return None
        
    user_download_dir = os.path.join(config.DOWNLOAD_DIR, str(user_id))
    
    # Step 1: Analyze all video files
    await status_message.edit_text("🔍 **Analyzing video compatibility for fast merge...**")
    
    video_infos = []
    for i, file_path in enumerate(video_files):
        info = await get_detailed_video_info(file_path)
        if not info or not info['has_video']:
            await status_message.edit_text(f"❌ **Video file {i+1} is invalid or has no video stream!**")
            return None
        video_infos.append(info)
        logger.info(f"Video {i+1}: {info['width']}x{info['height']}@{info['fps']}fps, {info['video_codec']}/{info['audio_codec']}")
    
    # Step 2: Check if fast merge is possible
    if videos_are_identical_for_merge(video_infos):
        await status_message.edit_text("🎶 **Videos are identical! Using ultra-fast merge...**")
        
        # Try fast merge first
        result = await fast_merge_identical_videos(video_files, user_id, status_message, video_infos, output_filename)
        if result:
            return result
        
        # If fast merge failed, continue to standardization
        logger.info("Fast merge failed, falling back to standardization")
    else:
        # Show what differs
        reference = video_infos[0]
        differences = []
        for i, info in enumerate(video_infos[1:], 1):
            if info['width'] != reference['width'] or info['height'] != reference['height']:
                differences.append(f"Resolution: {reference['width']}x{reference['height']} vs {info['width']}x{info['height']}")
            if abs(info['fps'] - reference['fps']) > 0.1:
                differences.append(f"FPS: {reference['fps']} vs {info['fps']}")
            if info['video_codec'] != reference['video_codec']:
                differences.append(f"Video Codec: {reference['video_codec']} vs {info['video_codec']}")
        
        diff_text = ", ".join(differences[:3])  # Show first 3 differences
        await status_message.edit_text(
            f"🔄 **Videos need standardization due to differences:**\n"
            f"➤ {diff_text}\n"
            f"➤ Standardizing for compatibility..."
        )
    
    # Step 3: Determine target standardization parameters
    widths = [info['width'] for info in video_infos]
    heights = [info['height'] for info in video_infos]
    
    width_counter = Counter(widths)
    height_counter = Counter(heights)
    
    target_width = width_counter.most_common(1)[0][0]
    target_height = height_counter.most_common(1)[0][0]
    
    target_params = {
        'width': target_width,
        'height': target_height,
        'fps': 30.0,
        'pixel_format': 'yuv420p',
        'audio_sample_rate': 48000
    }
    
    await status_message.edit_text(
        f"🔄 **Standardizing videos to common format...**\n"
        f"➤ Resolution: {target_width}x{target_height}\n"
        f"➤ Frame Rate: 30fps\n"
        f"➤ Format: MKV/H.264/AAC"
    )
    
    # Step 4: Standardize all video files
    standardized_files = []
    total_files = len(video_files)
    
    for i, (file_path, info) in enumerate(zip(video_files, video_infos)):
        await status_message.edit_text(
            f"🔄 **Standardizing video {i+1}/{total_files}...**\n"
            f"➤ Processing: `{os.path.basename(file_path)}`"
        )
        
        standardized_path = os.path.join(user_download_dir, f"std_{i}_{int(time.time())}.mkv")
        
        # Check if file needs standardization
        needs_standardization = (
            info['width'] != target_width or 
            info['height'] != target_height or
            abs(info['fps'] - 30.0) > 0.1 or
            info['pixel_format'] != 'yuv420p' or
            info['audio_sample_rate'] != 48000
        )
        
        if needs_standardization:
            success = await standardize_video_file(file_path, standardized_path, target_params)
            if not success:
                await status_message.edit_text(f"❌ **Failed to standardize video {i+1}!**")
                return None
            standardized_files.append(standardized_path)
        else:
            # File is already in perfect format, just copy it
            shutil.copy2(file_path, standardized_path)
            standardized_files.append(standardized_path)
    
    # Step 5: Fast concat on standardized files
    await status_message.edit_text("🚀 **Final merge of standardized videos...**")
    
    # Generate output filename
    if output_filename:
        base_name = os.path.splitext(output_filename)[0]  # Remove any existing extension
        output_path = os.path.join(user_download_dir, f"{base_name}.mkv")
    else:
        output_path = os.path.join(user_download_dir, f"merged_{int(time.time())}.mkv")
    
    inputs_file = os.path.join(user_download_dir, f"final_inputs_{int(time.time())}.txt")
    
    # Create inputs file
    with open(inputs_file, 'w', encoding='utf-8') as f:
        for file_path in standardized_files:
            abs_path = os.path.abspath(file_path)
            formatted_path = abs_path.replace("'", "'\''")
            f.write(f"file '{formatted_path}'\n")
    
    # Execute fast concat (guaranteed to work on standardized files)
    cmd = [
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
        '-f', 'concat', '-safe', '0', '-i', inputs_file,
        '-c', 'copy', '-f', 'matroska', output_path
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    # Cleanup
    try:
        os.remove(inputs_file)
        for std_file in standardized_files:
            os.remove(std_file)
    except:
        pass
    
    if process.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        await status_message.edit_text("✅ **Video merge completed successfully!**")
        return output_path
    else:
        error_output = stderr.decode().strip()
        logger.error(f"Final merge failed: {error_output}")
        await status_message.edit_text("❌ **Final merge failed! Check logs for details.**")
        return None
# --- Subtitle and Audio Merging Functions ---
async def merge_subtitles(video_path: str, subtitle_path: str, user_id: int, status_message) -> Optional[str]:
    """Merge a single subtitle file with video"""
    try:
        user_download_dir = os.path.join(config.DOWNLOAD_DIR, str(user_id))
        output_path = os.path.join(user_download_dir, f"softmuxed_{int(time.time())}.mkv")
        
        await status_message.edit_text("📝 **Merging subtitles...**")
        
        # Get video info to count existing subtitle streams
        video_info = await get_detailed_video_info(video_path)
        if not video_info:
            return None
            
        subtitle_count = video_info.get('subtitle_streams_count', 0)
        
        cmd = [
            'ffmpeg', '-hide_banner', '-y',
            '-i', video_path,
            '-i', subtitle_path,
            '-map', '0:v:0',
            '-map', '0:a:?',
            '-map', '0:s:?',
            '-map', '1:s',
            '-c:v', 'copy',
            '-c:a', 'copy',
            '-c:s', 'srt',
            f'-metadata:s:s:{subtitle_count}', f'title=Track {subtitle_count + 1}',
            output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0 and os.path.exists(output_path):
            # Replace original file with the new one
            os.remove(video_path)
            shutil.move(output_path, video_path)
            return video_path
        else:
            logger.error(f"Subtitle merge failed: {stderr.decode()}")
            return None
            
    except Exception as e:
        logger.error(f"Subtitle merge error: {e}")
        return None
async def merge_multiple_subtitles(video_path: str, subtitle_paths: List[str], user_id: int, status_message) -> Optional[str]:
    """Merge multiple subtitle files with video"""
    try:
        user_download_dir = os.path.join(config.DOWNLOAD_DIR, str(user_id))
        output_path = os.path.join(user_download_dir, f"softmuxed_{int(time.time())}.mkv")
        
        await status_message.edit_text("📝 **Merging multiple subtitles...**")
        
        # Get video info to count existing subtitle streams
        video_info = await get_detailed_video_info(video_path)
        if not video_info:
            return None
            
        subtitle_count = video_info.get('subtitle_streams_count', 0)
        
        # Build command
        cmd = ['ffmpeg', '-hide_banner', '-y', '-i', video_path]
        
        # Add subtitle inputs
        for sub in subtitle_paths:
            cmd.extend(['-i', sub])
        
        # Map streams
        cmd.extend(['-map', '0:v:0', '-map', '0:a:?', '-map', '0:s:?'])
        
        # Map subtitle streams and set metadata
        for i in range(len(subtitle_paths)):
            cmd.extend(['-map', f'{i+1}:s'])
            cmd.extend([f'-metadata:s:s:{subtitle_count + i}', f'title=Track {subtitle_count + i + 1}'])
        
        cmd.extend(['-c:v', 'copy', '-c:a', 'copy', '-c:s', 'srt', output_path])
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0 and os.path.exists(output_path):
            # Replace original file with the new one
            os.remove(video_path)
            shutil.move(output_path, video_path)
            return video_path
        else:
            logger.error(f"Multiple subtitle merge failed: {stderr.decode()}")
            return None
            
    except Exception as e:
        logger.error(f"Multiple subtitle merge error: {e}")
        return None
async def merge_audios(video_path: str, audio_paths: List[str], user_id: int, status_message) -> Optional[str]:
    """Merge multiple audio tracks with video"""
    try:
        user_download_dir = os.path.join(config.DOWNLOAD_DIR, str(user_id))
        output_path = os.path.join(user_download_dir, f"multiaudio_{int(time.time())}.mkv")
        
        await status_message.edit_text("🎵 **Merging audio tracks...**")
        
        # Get video info to count existing audio streams
        video_info = await get_detailed_video_info(video_path)
        if not video_info:
            return None
            
        audio_count = video_info.get('audio_streams_count', 0)
        
        # Build command
        cmd = ['ffmpeg', '-hide_banner', '-y', '-i', video_path]
        
        # Add audio inputs
        for audio in audio_paths:
            cmd.extend(['-i', audio])
        
        # Map video and subtitles
        cmd.extend(['-map', '0:v:0', '-map', '0:s:?'])
        
        # Map original audio streams and set disposition
        for i in range(audio_count):
            cmd.extend(['-map', f'0:a:{i}'])
            cmd.extend([f'-disposition:a:{i}', '0'])
        
        # Map new audio streams and set metadata
        for i in range(len(audio_paths)):
            cmd.extend(['-map', f'{i+1}:a'])
            cmd.extend([f'-metadata:s:a:{audio_count + i}', f'title=Track {audio_count + i + 1}'])
        
        # Set the first new audio track as default if no original audio exists
        if audio_count == 0 and len(audio_paths) > 0:
            cmd.extend(['-disposition:a:0', 'default'])
        
        cmd.extend(['-c:v', 'copy', '-c:a', 'copy', '-c:s', 'copy', output_path])
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0 and os.path.exists(output_path):
            # Replace original file with the new one
            os.remove(video_path)
            shutil.move(output_path, video_path)
            return video_path
        else:
            logger.error(f"Audio merge failed: {stderr.decode()}")
            return None
            
    except Exception as e:
        logger.error(f"Audio merge error: {e}")
        return None

def is_merge_cancelled(user_id: int) -> bool:
    """Check if merge is cancelled for user"""
    return active_merges.get(user_id, {}).get('cancelled', False)

def cancel_merge(user_id: int):
    """Cancel merge operation for user"""
    if user_id in active_merges:
        active_merges[user_id]['cancelled'] = True
        progress = active_merges[user_id].get('progress')
        if progress:
            progress.cancel()
            
# --- Main function with all options ---
async def merge_videos_with_options(
    video_files: List[str], 
    user_id: int, 
    status_message,
    output_filename: str = None,
    subtitle_files: List[str] = None,
    audio_files: List[str] = None
) -> Optional[str]:
    """
    Main function to merge videos with optional subtitle and audio merging
    """
    # First merge the videos
    merged_path = await merge_videos(video_files, user_id, status_message, output_filename)
    
    if merged_path is None:
        return None
    
    # Handle subtitle merging if requested
    if subtitle_files:
        if len(subtitle_files) == 1:
            merged_path = await merge_subtitles(merged_path, subtitle_files[0], user_id, status_message)
        else:
            merged_path = await merge_multiple_subtitles(merged_path, subtitle_files, user_id, status_message)
    
    # Handle audio merging if requested
    if audio_files:
        merged_path = await merge_audios(merged_path, audio_files, user_id, status_message)
    
    return merged_path
