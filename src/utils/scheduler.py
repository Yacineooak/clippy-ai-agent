"""
Scheduling system for automated video processing and posting
"""

import asyncio
import schedule
from datetime import datetime, timedelta
from typing import Dict, Any, List, Callable
import threading
import json
from pathlib import Path

from loguru import logger

from ..utils.config import Config


class ClippyScheduler:
    """Automated scheduling system for Clippy operations"""
    
    def __init__(self, config: Config):
        """Initialize scheduler with configuration"""
        self.config = config
        self.scheduler_config = config.get_scheduler_config()
        
        self.is_running = False
        self.scheduler_thread = None
        
        # Job queue and history
        self.job_queue = []
        self.job_history = []
        self.max_history = 100
        
        # Callbacks
        self.video_processor = None
        self.platform_manager = None
        
        # Initialize schedule
        self._setup_schedule()
    
    def _setup_schedule(self):
        """Setup scheduled jobs based on configuration"""
        if not self.scheduler_config.get("enabled", True):
            logger.info("⏰ Scheduler disabled in configuration")
            return
        
        try:
            # Clear existing jobs
            schedule.clear()
            
            # Setup posting schedule
            self._setup_posting_schedule()
            
            # Setup maintenance jobs
            self._setup_maintenance_jobs()
            
            # Setup monitoring jobs
            self._setup_monitoring_jobs()
            
            logger.success("✅ Scheduler setup complete")
            
        except Exception as e:
            logger.error(f"❌ Error setting up scheduler: {e}")
    
    def _setup_posting_schedule(self):
        """Setup scheduled posting jobs"""
        try:
            posting_times = self.scheduler_config.get("posting_times", {})
            
            for platform, times in posting_times.items():
                for time_str in times:
                    # Schedule daily posting at optimal times
                    schedule.every().day.at(time_str).do(
                        self._schedule_platform_check, platform
                    ).tag(f"posting_{platform}")
            
            logger.info(f"📅 Scheduled posting for {len(posting_times)} platforms")
            
        except Exception as e:
            logger.error(f"❌ Error setting up posting schedule: {e}")
    
    def _setup_maintenance_jobs(self):
        """Setup maintenance and cleanup jobs"""
        try:
            # Daily cleanup at 3 AM
            schedule.every().day.at("03:00").do(
                self._run_cleanup
            ).tag("maintenance")
            
            # Weekly analytics update on Sundays at 6 AM
            schedule.every().sunday.at("06:00").do(
                self._update_analytics
            ).tag("analytics")
            
            # Monthly model update check (first day of month at 5 AM)
            schedule.every().monday.at("05:00").do(
                self._check_model_updates
            ).tag("model_updates")
            
            logger.info("🧹 Scheduled maintenance jobs")
            
        except Exception as e:
            logger.error(f"❌ Error setting up maintenance jobs: {e}")
    
    def _setup_monitoring_jobs(self):
        """Setup monitoring and health check jobs"""
        try:
            # Health check every 30 minutes
            schedule.every(30).minutes.do(
                self._health_check
            ).tag("monitoring")
            
            # Platform status check every 2 hours
            schedule.every(2).hours.do(
                self._platform_status_check
            ).tag("platform_monitoring")
            
            logger.info("🔍 Scheduled monitoring jobs")
            
        except Exception as e:
            logger.error(f"❌ Error setting up monitoring jobs: {e}")
    
    def start(self):
        """Start the scheduler"""
        if self.is_running:
            logger.warning("⚠️ Scheduler already running")
            return
        
        try:
            self.is_running = True
            
            # Start scheduler in separate thread
            self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.scheduler_thread.start()
            
            logger.success("🚀 Scheduler started")
            
        except Exception as e:
            logger.error(f"❌ Error starting scheduler: {e}")
            self.is_running = False
    
    def stop(self):
        """Stop the scheduler"""
        try:
            self.is_running = False
            
            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=5)
            
            schedule.clear()
            logger.info("⏹️ Scheduler stopped")
            
        except Exception as e:
            logger.error(f"❌ Error stopping scheduler: {e}")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                schedule.run_pending()
                asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Error in scheduler loop: {e}")
                asyncio.sleep(60)  # Wait longer on error
    
    def _schedule_platform_check(self, platform: str):
        """Check if platform needs posting"""
        try:
            logger.info(f"📱 Checking {platform} posting schedule")
            
            if self.platform_manager:
                # This would trigger the platform manager to check for scheduled posts
                asyncio.create_task(self.platform_manager.process_scheduled_posts())
            
        except Exception as e:
            logger.error(f"❌ Error in platform check for {platform}: {e}")
    
    def _run_cleanup(self):
        """Run cleanup tasks"""
        try:
            logger.info("🧹 Running scheduled cleanup")
            
            storage_config = self.config.get_storage_config()
            
            # Clean up old downloads
            self._cleanup_old_files(
                self.config.get_download_path(),
                storage_config.get("keep_originals_days", 7)
            )
            
            # Clean up old clips
            self._cleanup_old_files(
                self.config.get_output_path(),
                storage_config.get("keep_clips_days", 30)
            )
            
            # Clean up temp files
            self._cleanup_old_files(
                self.config.get_temp_path(),
                1  # Keep temp files for 1 day only
            )
            
            # Clean up old logs
            self._cleanup_old_logs(storage_config.get("keep_logs_days", 90))
            
            logger.success("✅ Cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")
    
    def _cleanup_old_files(self, directory: Path, keep_days: int):
        """Clean up files older than specified days"""
        try:
            if not directory.exists():
                return
            
            cutoff_time = datetime.now() - timedelta(days=keep_days)
            deleted_count = 0
            
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"🗑️ Deleted {deleted_count} old files from {directory}")
                
        except Exception as e:
            logger.error(f"❌ Error cleaning up {directory}: {e}")
    
    def _cleanup_old_logs(self, keep_days: int):
        """Clean up old log files"""
        try:
            logs_dir = Path("./logs")
            if not logs_dir.exists():
                return
            
            cutoff_time = datetime.now() - timedelta(days=keep_days)
            deleted_count = 0
            
            for log_file in logs_dir.glob("*.log*"):
                if log_file.is_file():
                    file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if file_time < cutoff_time:
                        log_file.unlink()
                        deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"📝 Deleted {deleted_count} old log files")
                
        except Exception as e:
            logger.error(f"❌ Error cleaning up logs: {e}")
    
    def _update_analytics(self):
        """Update analytics and optimization data"""
        try:
            logger.info("📊 Running weekly analytics update")
            
            # This would update engagement tracking and optimization
            # For now, just log the action
            
            analytics_data = {
                "last_update": datetime.now().isoformat(),
                "job_type": "analytics_update",
                "status": "completed"
            }
            
            self._log_job_completion(analytics_data)
            
        except Exception as e:
            logger.error(f"❌ Error updating analytics: {e}")
    
    def _check_model_updates(self):
        """Check for AI model updates"""
        try:
            logger.info("🤖 Checking for model updates")
            
            # This would check for new versions of Whisper, LLM models, etc.
            # For now, just log the check
            
            update_data = {
                "last_check": datetime.now().isoformat(),
                "job_type": "model_update_check",
                "status": "completed",
                "updates_available": False
            }
            
            self._log_job_completion(update_data)
            
        except Exception as e:
            logger.error(f"❌ Error checking model updates: {e}")
    
    def _health_check(self):
        """Perform system health check"""
        try:
            logger.debug("💓 Running health check")
            
            health_data = {
                "timestamp": datetime.now().isoformat(),
                "job_type": "health_check",
                "status": "healthy",
                "memory_usage": self._get_memory_usage(),
                "disk_usage": self._get_disk_usage()
            }
            
            # Log warnings if resources are low
            if health_data["memory_usage"] > 80:
                logger.warning(f"⚠️ High memory usage: {health_data['memory_usage']}%")
            
            if health_data["disk_usage"] > 90:
                logger.warning(f"⚠️ High disk usage: {health_data['disk_usage']}%")
            
            self._log_job_completion(health_data)
            
        except Exception as e:
            logger.error(f"❌ Error in health check: {e}")
    
    def _platform_status_check(self):
        """Check platform connectivity and status"""
        try:
            logger.info("🔗 Checking platform status")
            
            if self.platform_manager:
                # This would test platform connections
                # status = await self.platform_manager.test_platforms()
                pass
            
            status_data = {
                "timestamp": datetime.now().isoformat(),
                "job_type": "platform_status_check",
                "status": "completed"
            }
            
            self._log_job_completion(status_data)
            
        except Exception as e:
            logger.error(f"❌ Error checking platform status: {e}")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage percentage"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            return 0.0
    
    def _get_disk_usage(self) -> float:
        """Get current disk usage percentage"""
        try:
            import psutil
            return psutil.disk_usage('.').percent
        except ImportError:
            return 0.0
    
    def _log_job_completion(self, job_data: Dict[str, Any]):
        """Log job completion to history"""
        self.job_history.append(job_data)
        
        # Keep history within limits
        if len(self.job_history) > self.max_history:
            self.job_history = self.job_history[-self.max_history:]
    
    def add_job(self, job_func: Callable, schedule_time: str, job_name: str = None):
        """Add a custom job to the scheduler"""
        try:
            schedule.every().day.at(schedule_time).do(job_func).tag(job_name or "custom")
            logger.info(f"➕ Added scheduled job: {job_name} at {schedule_time}")
            
        except Exception as e:
            logger.error(f"❌ Error adding job: {e}")
    
    def remove_job(self, tag: str):
        """Remove jobs with specific tag"""
        try:
            schedule.clear(tag)
            logger.info(f"➖ Removed scheduled jobs with tag: {tag}")
            
        except Exception as e:
            logger.error(f"❌ Error removing job: {e}")
    
    def get_job_status(self) -> Dict[str, Any]:
        """Get scheduler status and job information"""
        try:
            jobs = schedule.jobs
            
            job_info = []
            for job in jobs:
                job_info.append({
                    "function": str(job.job_func),
                    "next_run": str(job.next_run),
                    "interval": str(job.interval),
                    "unit": job.unit,
                    "tags": list(job.tags) if job.tags else []
                })
            
            return {
                "is_running": self.is_running,
                "total_jobs": len(jobs),
                "jobs": job_info,
                "recent_completions": self.job_history[-10:],  # Last 10 completions
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting job status: {e}")
            return {"error": str(e)}
    
    def set_video_processor(self, video_processor):
        """Set video processor reference for scheduled operations"""
        self.video_processor = video_processor
    
    def set_platform_manager(self, platform_manager):
        """Set platform manager reference for scheduled operations"""
        self.platform_manager = platform_manager
    
    def schedule_video_processing(self, video_url: str, process_time: datetime):
        """Schedule a video for processing at specific time"""
        try:
            def process_video():
                if self.video_processor:
                    asyncio.create_task(self.video_processor.process_input(video_url))
            
            # Schedule one-time job
            schedule.every().day.at(process_time.strftime("%H:%M")).do(process_video).tag("scheduled_video")
            
            logger.info(f"📅 Scheduled video processing: {video_url} at {process_time}")
            
        except Exception as e:
            logger.error(f"❌ Error scheduling video processing: {e}")
    
    def get_optimal_posting_time(self, platform: str) -> datetime:
        """Get next optimal posting time for platform"""
        try:
            posting_times = self.scheduler_config.get("posting_times", {}).get(platform, ["12:00"])
            
            now = datetime.now()
            today_times = []
            
            for time_str in posting_times:
                hour, minute = map(int, time_str.split(':'))
                post_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                if post_time > now:
                    today_times.append(post_time)
                else:
                    # Add tomorrow's time
                    tomorrow_time = post_time + timedelta(days=1)
                    today_times.append(tomorrow_time)
            
            return min(today_times) if today_times else now + timedelta(hours=1)
            
        except Exception as e:
            logger.error(f"❌ Error getting optimal posting time: {e}")
            return datetime.now() + timedelta(hours=1)
