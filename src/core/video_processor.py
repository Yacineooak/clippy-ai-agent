"""
Video processing module for downloading, transcribing, and clipping videos
"""

import os
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import tempfile
import hashlib

import yt_dlp
import whisper
import ffmpeg
from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip
import cv2
import numpy as np
from loguru import logger

from ..utils.config import Config

# Configure ImageMagick for MoviePy
from moviepy.config import change_settings
try:
    # Try to find ImageMagick installation
    magick_path = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
    if os.path.exists(magick_path):
        change_settings({"IMAGEMAGICK_BINARY": magick_path})
        logger.info(f"✅ ImageMagick configured: {magick_path}")
    else:
        logger.warning("⚠️ ImageMagick not found, text overlays may not work")
except Exception as e:
    logger.warning(f"⚠️ Failed to configure ImageMagick: {e}")


class VideoProcessor:
    """Handles video download, transcription, and clip generation"""
    
    def __init__(self, config: Config):
        """Initialize video processor with configuration"""
        self.config = config
        self.video_config = config.get_video_config()
        self.ai_config = config.get_ai_config()
        
        # Set up FFmpeg path if specified
        ffmpeg_path = self.video_config.get('ffmpeg_path')
        if ffmpeg_path and os.path.exists(ffmpeg_path):
            os.environ['PATH'] = os.path.dirname(os.path.abspath(ffmpeg_path)) + os.pathsep + os.environ.get('PATH', '')
            logger.info(f"✅ Using custom FFmpeg: {ffmpeg_path}")
        else:
            logger.info("Using system FFmpeg")
        
        # Initialize Whisper model
        whisper_model = self.ai_config.get("whisper", {}).get("model", "base")
        try:
            self.whisper_model = whisper.load_model(whisper_model)
            logger.info(f"✅ Whisper model '{whisper_model}' loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load Whisper model: {e}")
            self.whisper_model = None
        
        # Ensure directories exist
        self.download_path = Path(self.video_config.get("download_path", "./downloads"))
        self.output_path = Path(self.video_config.get("output_path", "./output"))
        self.temp_path = Path(self.video_config.get("temp_path", "./temp"))
        
        for path in [self.download_path, self.output_path, self.temp_path]:
            path.mkdir(parents=True, exist_ok=True)
    
    def _is_url(self, input_source: str) -> bool:
        """Check if input is a URL"""
        try:
            result = urlparse(input_source)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _generate_video_id(self, input_source: str) -> str:
        """Generate unique ID for video"""
        return hashlib.md5(input_source.encode()).hexdigest()[:12]
    
    async def download_video(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Download video from URL using yt-dlp
        
        Args:
            url: Video URL to download
            
        Returns:
            Dictionary with video metadata and file path
        """
        try:
            logger.info(f"📥 Downloading video from: {url}")
            
            video_id = self._generate_video_id(url)
            output_template = str(self.download_path / f"{video_id}.%(ext)s")
            
            ydl_opts = {
                'format': 'best[height<=1080]',
                'outtmpl': output_template,
                'writeinfojson': True,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'ignoreerrors': True,
                'no_warnings': True,
            }
            
            # Add quality restrictions
            max_duration = self.video_config.get("max_duration_seconds", 3600)
            ydl_opts['match_filter'] = lambda info_dict: None if info_dict.get('duration', 0) <= max_duration else "Video too long"
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info first
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    logger.error("❌ Failed to extract video information")
                    return None
                
                # Check duration
                duration = info.get('duration', 0)
                if duration > max_duration:
                    logger.error(f"❌ Video too long: {duration}s > {max_duration}s")
                    return None
                
                # Download the video
                ydl.download([url])
                
                # Find downloaded video file
                video_file = None
                for ext in ['mp4', 'mkv', 'webm', 'avi']:
                    potential_file = self.download_path / f"{video_id}.{ext}"
                    if potential_file.exists():
                        video_file = potential_file
                        break
                
                if not video_file or not video_file.exists():
                    logger.error("❌ Downloaded video file not found")
                    return None
                
                logger.success(f"✅ Video downloaded: {video_file}")
                
                return {
                    'file_path': str(video_file),
                    'video_id': video_id,
                    'title': info.get('title', 'Unknown'),
                    'duration': duration,
                    'uploader': info.get('uploader', 'Unknown'),
                    'description': info.get('description', ''),
                    'upload_date': info.get('upload_date', ''),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'comment_count': info.get('comment_count', 0),
                    'url': url
                }
                
        except Exception as e:
            logger.error(f"❌ Error downloading video: {e}")
            return None
    
    async def transcribe_video(self, video_path: str) -> Optional[Dict[str, Any]]:
        """
        Transcribe video using Whisper
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary with transcript and segments
        """
        if not self.whisper_model:
            logger.error("❌ Whisper model not loaded")
            return None
        
        try:
            logger.info(f"🎙️ Transcribing video: {video_path}")
            
            # Extract audio first for better performance
            audio_file = self.temp_path / f"audio_{Path(video_path).stem}.wav"
            
            # Use ffmpeg to extract audio
            (
                ffmpeg
                .input(video_path)
                .output(str(audio_file), acodec='pcm_s16le', ac=1, ar='16k')
                .overwrite_output()
                .run(quiet=True, capture_stdout=True)
            )
            
            # Transcribe audio
            whisper_config = self.ai_config.get("whisper", {})
            language = whisper_config.get("language")
            if language == "auto":
                language = None
            
            result = self.whisper_model.transcribe(
                str(audio_file),
                language=language,
                word_timestamps=True,
                verbose=False
            )
            
            # Clean up audio file
            audio_file.unlink(missing_ok=True)
            
            # Process segments for better structure
            segments = []
            for segment in result.get('segments', []):
                segments.append({
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': segment['text'].strip(),
                    'words': segment.get('words', [])
                })
            
            logger.success(f"✅ Transcription complete: {len(segments)} segments")
            
            return {
                'text': result['text'],
                'language': result.get('language', 'unknown'),
                'segments': segments,
                'duration': segments[-1]['end'] if segments else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error transcribing video: {e}")
            return None
    
    async def process_input(self, input_source: str) -> Optional[Dict[str, Any]]:
        """
        Process input source (URL or file) and return video data with transcript
        
        Args:
            input_source: YouTube URL or local file path
            
        Returns:
            Complete video data with transcript
        """
        try:
            if self._is_url(input_source):
                # Download from URL
                video_data = await self.download_video(input_source)
                if not video_data:
                    return None
                video_path = video_data['file_path']
            else:
                # Use local file
                video_path = input_source
                if not os.path.exists(video_path):
                    logger.error(f"❌ Video file not found: {video_path}")
                    return None
                
                # Create basic metadata for local files
                video_id = self._generate_video_id(video_path)
                video_data = {
                    'file_path': video_path,
                    'video_id': video_id,
                    'title': Path(video_path).stem,
                    'duration': 0,  # Will be updated after processing
                    'uploader': 'Local',
                    'description': '',
                    'upload_date': '',
                    'view_count': 0,
                    'like_count': 0,
                    'comment_count': 0,
                    'url': input_source
                }
            
            # Get video info using moviepy
            try:
                with VideoFileClip(video_path) as clip:
                    video_data['duration'] = clip.duration
                    video_data['fps'] = clip.fps
                    video_data['resolution'] = f"{clip.w}x{clip.h}"
            except Exception as e:
                logger.warning(f"⚠️ Could not get video info: {e}")
            
            # Transcribe the video
            transcript = await self.transcribe_video(video_path)
            if not transcript:
                logger.error("❌ Failed to transcribe video")
                return None
            
            video_data['transcript'] = transcript
            video_data['metadata'] = {
                'file_size': os.path.getsize(video_path),
                'format': Path(video_path).suffix[1:],
                'processed_at': asyncio.get_event_loop().time()
            }
            
            logger.success(f"✅ Video processing complete: {video_data['title']}")
            return video_data
            
        except Exception as e:
            logger.error(f"❌ Error processing input: {e}")
            return None
    
    async def create_clip(self, video_data: Dict[str, Any], highlight: Dict[str, Any], title_override: str = None) -> Optional[Dict[str, Any]]:
        """
        Create a short clip from video based on highlight data
        
        Args:
            video_data: Original video data
            highlight: Highlight information with timestamps
            title_override: Optional title override
            
        Returns:
            Clip data with file paths and metadata
        """
        try:
            start_time = highlight['start_time']
            end_time = highlight['end_time']
            clip_title = title_override or highlight.get('title', 'Untitled Clip')
            
            logger.info(f"🎞️ Creating clip: {clip_title} ({start_time:.1f}s - {end_time:.1f}s)")
            
            # Generate clip filename
            clip_id = f"{video_data['video_id']}_{int(start_time)}_{int(end_time)}"
            output_file = self.output_path / f"{clip_id}.mp4"
            
            # Load video
            with VideoFileClip(video_data['file_path']) as video:
                # Extract clip segment
                clip = video.subclip(start_time, end_time)
                
                # Resize to vertical format (9:16)
                target_resolution = self.video_config.get("resolution", "1080x1920")
                width, height = map(int, target_resolution.split('x'))
                
                # Crop to vertical aspect ratio
                original_width, original_height = clip.w, clip.h
                target_aspect = width / height
                original_aspect = original_width / original_height
                
                if original_aspect > target_aspect:
                    # Video is wider than target - crop sides
                    new_width = int(original_height * target_aspect)
                    x_center = original_width // 2
                    x1 = x_center - new_width // 2
                    clip = clip.crop(x1=x1, x2=x1 + new_width)
                else:
                    # Video is taller than target - crop top/bottom
                    new_height = int(original_width / target_aspect)
                    y_center = original_height // 2
                    y1 = y_center - new_height // 2
                    clip = clip.crop(y1=y1, y2=y1 + new_height)
                
                # Resize to exact target resolution
                clip = clip.resize((width, height))
                
                # Add captions if enabled
                if self.config.get("captions.enabled", True):
                    clip = await self._add_captions(clip, highlight)
                
                # Add title overlay if needed
                if self.config.get("captions.show_title", True):
                    clip = await self._add_title_overlay(clip, clip_title)
                
                # Set output parameters
                fps = self.video_config.get("fps", 30)
                bitrate = self.video_config.get("bitrate", "2M")
                
                # Write the video file
                try:
                    clip.write_videofile(
                        str(output_file),
                        fps=fps,
                        bitrate=bitrate,
                        audio_bitrate=self.video_config.get("audio_bitrate", "128k"),
                        temp_audiofile=str(self.temp_path / f"temp_audio_{clip_id}.m4a"),
                        remove_temp=True,
                        verbose=False,
                        logger=None,
                        codec='libx264',
                        audio_codec='aac'
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Failed with temp audio file, trying without: {e}")
                    # Fallback without temp audio file
                    clip.write_videofile(
                        str(output_file),
                        fps=fps,
                        bitrate=bitrate,
                        audio_bitrate=self.video_config.get("audio_bitrate", "128k"),
                        verbose=False,
                        logger=None,
                        codec='libx264',
                        audio_codec='aac'
                    )
            
            # Generate metadata
            clip_data = {
                'clip_id': clip_id,
                'file_path': str(output_file),
                'title': clip_title,
                'description': highlight.get('description', ''),
                'hashtags': highlight.get('hashtags', []),
                'start_time': start_time,
                'end_time': end_time,
                'duration': end_time - start_time,
                'emotion': highlight.get('emotion', 'neutral'),
                'engagement_score': highlight.get('engagement_score', 0.0),
                'source_video': video_data['video_id'],
                'resolution': target_resolution,
                'file_size': output_file.stat().st_size if output_file.exists() else 0,
                'created_at': asyncio.get_event_loop().time()
            }
            
            logger.success(f"✅ Clip created: {output_file}")
            return clip_data
            
        except Exception as e:
            logger.error(f"❌ Error creating clip: {e}")
            return None
    
    async def _add_captions(self, clip, highlight: Dict[str, Any]):
        """Add captions to video clip"""
        try:
            caption_config = self.config.get_caption_config()
            
            # Get caption text from highlight
            caption_text = highlight.get('text', '').strip()
            if not caption_text:
                return clip
            
            # Split into manageable chunks
            words = caption_text.split()
            chunks = []
            current_chunk = []
            
            for word in words:
                current_chunk.append(word)
                if len(' '.join(current_chunk)) > 40:  # Max characters per line
                    chunks.append(' '.join(current_chunk[:-1]))
                    current_chunk = [word]
            
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            
            # Create text clips
            text_clips = []
            chunk_duration = clip.duration / len(chunks) if chunks else clip.duration
            
            for i, chunk in enumerate(chunks):
                text_clip = TextClip(
                    chunk,
                    fontsize=caption_config.get("font_size", 48),
                    color=caption_config.get("text_color", "white"),
                    stroke_color=caption_config.get("stroke_color", "black"),
                    stroke_width=caption_config.get("stroke_width", 3),
                    font=caption_config.get("font_family", "Arial-Bold"),
                    method='caption',
                    size=(int(clip.w * 0.8), None)
                ).set_duration(chunk_duration).set_start(i * chunk_duration)
                
                # Position captions
                position = caption_config.get("position", "bottom")
                if position == "bottom":
                    text_clip = text_clip.set_position(('center', clip.h - 150))
                elif position == "top":
                    text_clip = text_clip.set_position(('center', 50))
                else:  # center
                    text_clip = text_clip.set_position('center')
                
                text_clips.append(text_clip)
            
            # Composite video with captions
            return CompositeVideoClip([clip] + text_clips)
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to add captions: {e}")
            return clip
    
    async def _add_title_overlay(self, clip, title: str):
        """Add title overlay to video"""
        try:
            # Create title text clip
            title_clip = TextClip(
                title,
                fontsize=36,
                color='white',
                stroke_color='black',
                stroke_width=2,
                font='Arial-Bold'
            ).set_duration(3).set_position(('center', 30))  # Show for first 3 seconds
            
            return CompositeVideoClip([clip, title_clip])
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to add title overlay: {e}")
            return clip
