"""
Clippy - Autonomous Video Repurposing AI Agent
Main entry point for the application
"""

import asyncio
import sys
import os
from pathlib import Path
from loguru import logger

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.video_processor import VideoProcessor
from src.core.content_analyzer import ContentAnalyzer
from src.core.platform_manager import PlatformManager
from src.utils.config import Config
from src.utils.scheduler import ClippyScheduler


class ClippyAgent:
    """Main Clippy AI Agent orchestrating the entire video repurposing workflow"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize Clippy with configuration"""
        self.config = Config(config_path)
        self.setup_logging()
        
        # Initialize core components
        self.video_processor = VideoProcessor(self.config)
        self.content_analyzer = ContentAnalyzer(self.config)
        self.platform_manager = PlatformManager(self.config)
        self.scheduler = ClippyScheduler(self.config)
        
        logger.info("🎬 Clippy AI Agent initialized successfully!")
    
    def setup_logging(self):
        """Configure logging based on config settings"""
        log_config = self.config.get("logging", {})
        
        # Remove default logger
        logger.remove()
        
        # Add console logger with colors if enabled
        if log_config.get("console_colors", True):
            logger.add(
                sys.stderr,
                level=log_config.get("level", "INFO"),
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
                colorize=True
            )
        else:
            logger.add(sys.stderr, level=log_config.get("level", "INFO"))
        
        # Add file logger if specified
        if log_file := log_config.get("file"):
            logger.add(
                log_file,
                level=log_config.get("level", "INFO"),
                rotation=f"{log_config.get('max_size_mb', 50)} MB",
                retention=log_config.get('backup_count', 5),
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
            )
    
    async def process_video(self, input_source: str, title: str = None) -> list:
        """
        Process a single video through the complete pipeline
        
        Args:
            input_source: YouTube URL or local file path
            title: Optional title override
            
        Returns:
            List of generated clips with metadata
        """
        try:
            logger.info(f"🎯 Starting video processing: {input_source}")
            
            # Step 1: Download and transcribe video
            logger.info("📥 Step 1: Video intake and transcription")
            video_data = await self.video_processor.process_input(input_source)
            
            if not video_data:
                logger.error("❌ Failed to process video input")
                return []
            
            # Step 2: Analyze content and detect highlights
            logger.info("🧠 Step 2: Content analysis and highlight detection")
            highlights = await self.content_analyzer.find_highlights(
                video_data["transcript"],
                video_data["metadata"]
            )
            
            if not highlights:
                logger.warning("⚠️ No highlights found in video")
                return []
            
            logger.info(f"✨ Found {len(highlights)} potential clips")
            
            # Step 3: Generate clips
            logger.info("🎞️ Step 3: Video clipping and editing")
            clips = []
            
            for i, highlight in enumerate(highlights, 1):
                logger.info(f"🔄 Processing clip {i}/{len(highlights)}")
                
                clip_data = await self.video_processor.create_clip(
                    video_data,
                    highlight,
                    title_override=title
                )
                
                if clip_data:
                    clips.append(clip_data)
                    logger.success(f"✅ Clip {i} created successfully")
                else:
                    logger.warning(f"⚠️ Failed to create clip {i}")
            
            # Step 4: Platform posting
            if clips and self.config.get("platforms", {}).get("auto_post", True):
                logger.info("📱 Step 4: Platform-specific posting")
                posting_results = await self.platform_manager.post_clips(clips)
                
                # Step 5: Cleanup files after successful posting
                if self.config.get("cleanup", {}).get("enabled", True):
                    await self._cleanup_files(video_data, clips, posting_results)
            
            logger.success(f"🎉 Video processing complete! Generated {len(clips)} clips")
            return clips
            
        except Exception as e:
            logger.error(f"❌ Error processing video: {str(e)}")
            return []
    
    async def batch_process(self, input_list: list) -> dict:
        """
        Process multiple videos in batch
        
        Args:
            input_list: List of video sources (URLs or file paths)
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"🚀 Starting batch processing of {len(input_list)} videos")
        
        results = {
            "total_videos": len(input_list),
            "successful": 0,
            "failed": 0,
            "total_clips": 0,
            "clips": []
        }
        
        for i, video_source in enumerate(input_list, 1):
            logger.info(f"📹 Processing video {i}/{len(input_list)}: {video_source}")
            
            clips = await self.process_video(video_source)
            
            if clips:
                results["successful"] += 1
                results["total_clips"] += len(clips)
                results["clips"].extend(clips)
            else:
                results["failed"] += 1
        
        logger.info(f"📊 Batch processing complete: {results['successful']}/{results['total_videos']} successful")
        return results
    
    async def _cleanup_files(self, video_data: dict, clips: list, posting_results: dict):
        """
        Clean up source video and generated clips after successful posting
        
        Args:
            video_data: Original video information
            clips: List of generated clip data
            posting_results: Results from platform posting
        """
        try:
            cleanup_config = self.config.get("cleanup", {})
            
            # Check if cleanup is enabled
            if not cleanup_config.get("enabled", True):
                return
            
            # Determine cleanup strategy
            cleanup_strategy = cleanup_config.get("strategy", "after_successful_posts")
            
            should_cleanup = False
            
            if cleanup_strategy == "always":
                should_cleanup = True
                logger.info("🧹 Cleanup strategy: Always delete files")
            elif cleanup_strategy == "after_successful_posts":
                # Check if at least one platform posted successfully
                successful_posts = posting_results.get("successful", 0) if posting_results else 0
                should_cleanup = successful_posts > 0
                logger.info(f"🧹 Cleanup strategy: Delete after successful posts ({successful_posts} successful)")
            elif cleanup_strategy == "after_all_posts":
                # Only cleanup if all platforms posted successfully
                total_expected = len(clips) * len(self.platform_manager.get_active_platforms())
                successful_posts = posting_results.get("successful", 0) if posting_results else 0
                should_cleanup = successful_posts == total_expected
                logger.info(f"🧹 Cleanup strategy: Delete only if all posts successful ({successful_posts}/{total_expected})")
            
            if not should_cleanup:
                logger.info("🧹 Cleanup skipped - conditions not met")
                return
            
            files_deleted = 0
            space_freed = 0
            
            # Delete source video file
            if cleanup_config.get("delete_source", True):
                source_path = Path(video_data.get("file_path", ""))
                if source_path.exists():
                    file_size = source_path.stat().st_size
                    source_path.unlink()
                    files_deleted += 1
                    space_freed += file_size
                    logger.info(f"🗑️ Deleted source video: {source_path.name} ({file_size / 1024 / 1024:.1f}MB)")
                
                # Also delete metadata file if exists
                info_path = source_path.with_suffix('.info.json')
                if info_path.exists():
                    info_path.unlink()
                    files_deleted += 1
                    logger.info(f"🗑️ Deleted metadata: {info_path.name}")
            
            # Delete generated clips
            if cleanup_config.get("delete_clips", True):
                for clip in clips:
                    clip_path = Path(clip.get("file_path", ""))
                    if clip_path.exists():
                        file_size = clip_path.stat().st_size
                        clip_path.unlink()
                        files_deleted += 1
                        space_freed += file_size
                        logger.info(f"🗑️ Deleted clip: {clip_path.name} ({file_size / 1024 / 1024:.1f}MB)")
            
            # Clean up temporary files
            if cleanup_config.get("delete_temp", True):
                temp_pattern = f"*{video_data.get('video_id', 'unknown')}*"
                temp_path = Path(self.config.get("video", {}).get("temp_path", "./temp"))
                
                if temp_path.exists():
                    for temp_file in temp_path.glob(temp_pattern):
                        if temp_file.is_file():
                            file_size = temp_file.stat().st_size
                            temp_file.unlink()
                            files_deleted += 1
                            space_freed += file_size
                            logger.info(f"🗑️ Deleted temp file: {temp_file.name}")
            
            logger.success(f"🧹 Cleanup complete: {files_deleted} files deleted, {space_freed / 1024 / 1024:.1f}MB freed")
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")
    
    def start_scheduler(self):
        """Start the automated scheduling system"""
        logger.info("⏰ Starting Clippy scheduler")
        self.scheduler.start()
    
    def stop_scheduler(self):
        """Stop the automated scheduling system"""
        logger.info("⏹️ Stopping Clippy scheduler")
        self.scheduler.stop()


async def main():
    """Main function for CLI usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clippy - Autonomous Video Repurposing AI Agent")
    parser.add_argument("--config", default="config.yaml", help="Configuration file path")
    parser.add_argument("--input", help="Video URL or file path to process")
    parser.add_argument("--batch", help="File containing list of videos to process")
    parser.add_argument("--scheduler", action="store_true", help="Start scheduler mode")
    parser.add_argument("--title", help="Override video title")
    
    args = parser.parse_args()
    
    # Initialize Clippy
    clippy = ClippyAgent(args.config)
    
    try:
        if args.scheduler:
            # Scheduler mode
            logger.info("🔄 Starting in scheduler mode...")
            clippy.start_scheduler()
            
            # Keep running until interrupted
            try:
                while True:
                    await asyncio.sleep(60)
            except KeyboardInterrupt:
                logger.info("👋 Shutdown requested")
                clippy.stop_scheduler()
                
        elif args.batch:
            # Batch processing mode
            if not os.path.exists(args.batch):
                logger.error(f"❌ Batch file not found: {args.batch}")
                return
            
            with open(args.batch, 'r') as f:
                video_list = [line.strip() for line in f if line.strip()]
            
            results = await clippy.batch_process(video_list)
            logger.info(f"📊 Batch Results: {results}")
            
        elif args.input:
            # Single video processing
            clips = await clippy.process_video(args.input, args.title)
            logger.info(f"✨ Generated {len(clips)} clips")
            
        else:
            # Interactive mode
            logger.info("🎬 Welcome to Clippy! Enter a YouTube URL or video file path:")
            
            while True:
                try:
                    user_input = input("\n🎯 Video source (or 'quit' to exit): ").strip()
                    
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        break
                    
                    if user_input:
                        clips = await clippy.process_video(user_input)
                        logger.info(f"✨ Generated {len(clips)} clips")
                    
                except KeyboardInterrupt:
                    break
            
            logger.info("👋 Thanks for using Clippy!")
    
    except Exception as e:
        logger.error(f"❌ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # Ensure required directories exist
    for directory in ["downloads", "output", "temp", "logs", "models"]:
        Path(directory).mkdir(exist_ok=True)
    
    # Run the main function
    asyncio.run(main())
