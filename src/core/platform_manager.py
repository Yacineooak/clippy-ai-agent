"""
Platform management module for coordinating posts across multiple social media platforms
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from loguru import logger

from ..platforms.youtube_shorts import YouTubeShortsManager
from ..platforms.tiktok_poster import TikTokPoster
from ..platforms.instagram_reels import InstagramReelsPoster
from ..utils.config import Config


class PlatformManager:
    """Manages posting and coordination across multiple social media platforms"""
    
    def __init__(self, config: Config):
        """Initialize platform manager with configuration"""
        self.config = config
        self.platforms = {}
        
        # Initialize enabled platforms
        self._initialize_platforms()
        
        # Posting queue and scheduler
        self.posting_queue = []
        self.posting_in_progress = False
    
    def _initialize_platforms(self):
        """Initialize platform handlers based on configuration"""
        try:
            # YouTube Shorts
            if self.config.is_platform_enabled('youtube'):
                try:
                    self.platforms['youtube'] = YouTubeShortsManager(self.config)
                    logger.info("✅ YouTube Shorts platform initialized")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize YouTube Shorts: {e}")
            
            # TikTok
            if self.config.is_platform_enabled('tiktok'):
                try:
                    self.platforms['tiktok'] = TikTokPoster(self.config)
                    logger.info("✅ TikTok platform initialized")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize TikTok: {e}")
            
            # Instagram Reels
            if self.config.is_platform_enabled('instagram'):
                try:
                    self.platforms['instagram'] = InstagramReelsPoster(self.config)
                    logger.info("✅ Instagram Reels platform initialized")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize Instagram Reels: {e}")
            
            if not self.platforms:
                logger.warning("⚠️ No platforms enabled or successfully initialized")
            else:
                logger.info(f"🚀 Platform manager initialized with {len(self.platforms)} platforms")
                
        except Exception as e:
            logger.error(f"❌ Error initializing platforms: {e}")
    
    def get_active_platforms(self) -> List[str]:
        """
        Get list of active platform names
        
        Returns:
            List of platform names that are enabled and initialized
        """
        return list(self.platforms.keys())
    
    async def post_clips(self, clips: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Post clips to all enabled platforms
        
        Args:
            clips: List of clip data dictionaries
            
        Returns:
            Dictionary with posting results
        """
        try:
            logger.info(f"📱 Starting multi-platform posting for {len(clips)} clips")
            
            if not self.platforms:
                logger.warning("⚠️ No platforms available for posting")
                return {"success": False, "message": "No platforms enabled"}
            
            results = {
                "total_clips": len(clips),
                "successful_posts": 0,
                "failed_posts": 0,
                "platform_results": {},
                "post_details": []
            }
            
            # Check if we should schedule posts or post immediately
            scheduler_config = self.config.get_scheduler_config()
            if scheduler_config.get("enabled", True):
                # Schedule posts for optimal times
                await self._schedule_posts(clips)
                results["message"] = "Posts scheduled for optimal times"
            else:
                # Post immediately
                for clip in clips:
                    clip_results = await self._post_clip_to_platforms(clip)
                    results["post_details"].append(clip_results)
                    
                    # Update counters
                    for platform, result in clip_results["platforms"].items():
                        if result["success"]:
                            results["successful_posts"] += 1
                        else:
                            results["failed_posts"] += 1
                
                results["message"] = "Posts completed immediately"
            
            # Calculate platform-specific results
            for platform_name in self.platforms.keys():
                platform_posts = [
                    detail["platforms"].get(platform_name, {}) 
                    for detail in results["post_details"]
                ]
                successful = sum(1 for post in platform_posts if post.get("success", False))
                
                results["platform_results"][platform_name] = {
                    "total": len(platform_posts),
                    "successful": successful,
                    "failed": len(platform_posts) - successful
                }
            
            logger.success(f"📊 Multi-platform posting complete: {results['successful_posts']} successful, {results['failed_posts']} failed")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in multi-platform posting: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "total_clips": len(clips),
                "successful_posts": 0,
                "failed_posts": len(clips),
                "platform_results": {},
                "post_details": []
            }
    
    async def _post_clip_to_platforms(self, clip: Dict[str, Any]) -> Dict[str, Any]:
        """Post a single clip to all platforms"""
        logger.info(f"📤 Posting clip: {clip['title']}")
        
        clip_results = {
            "clip_id": clip["clip_id"],
            "clip_title": clip["title"],
            "platforms": {}
        }
        
        # Post to each platform concurrently
        platform_tasks = []
        
        for platform_name, platform_handler in self.platforms.items():
            task = self._post_to_single_platform(platform_name, platform_handler, clip)
            platform_tasks.append(task)
        
        # Wait for all platforms to complete
        platform_results = await asyncio.gather(*platform_tasks, return_exceptions=True)
        
        # Process results
        for i, (platform_name, _) in enumerate(self.platforms.items()):
            result = platform_results[i]
            
            if isinstance(result, Exception):
                clip_results["platforms"][platform_name] = {
                    "success": False,
                    "error": str(result),
                    "posted_at": None,
                    "post_id": None
                }
            else:
                clip_results["platforms"][platform_name] = result
        
        return clip_results
    
    async def _post_to_single_platform(self, platform_name: str, platform_handler, clip: Dict[str, Any]) -> Dict[str, Any]:
        """Post to a single platform with error handling"""
        try:
            logger.info(f"📲 Posting to {platform_name}: {clip['title']}")
            
            # Prepare platform-specific metadata
            post_data = await self._prepare_post_data(platform_name, clip)
            
            # Post to platform
            result = await platform_handler.post_video(
                video_path=clip["file_path"],
                title=post_data["title"],
                description=post_data["description"],
                hashtags=post_data["hashtags"],
                metadata=post_data.get("metadata", {})
            )
            
            if result.get("success", False):
                logger.success(f"✅ Successfully posted to {platform_name}")
                return {
                    "success": True,
                    "post_id": result.get("post_id"),
                    "post_url": result.get("post_url"),
                    "posted_at": datetime.now().isoformat(),
                    "message": result.get("message", "Posted successfully")
                }
            else:
                logger.error(f"❌ Failed to post to {platform_name}: {result.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "posted_at": None,
                    "post_id": None
                }
        
        except Exception as e:
            logger.error(f"❌ Exception posting to {platform_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "posted_at": None,
                "post_id": None
            }
    
    async def _prepare_post_data(self, platform_name: str, clip: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare platform-specific post data"""
        base_title = clip["title"]
        base_description = clip.get("description", "")
        base_hashtags = clip.get("hashtags", [])
        
        # Get platform-specific hashtags
        hashtag_config = self.config.get_hashtag_config()
        platform_hashtags = hashtag_config.get(platform_name, [])
        
        # Combine hashtags
        all_hashtags = list(set(base_hashtags + platform_hashtags))
        
        # Platform-specific adaptations
        if platform_name == "youtube":
            # YouTube Shorts specific formatting
            title = base_title[:100]  # YouTube title limit
            description = f"{base_description}\n\n{' '.join(all_hashtags[:15])}"  # Include hashtags in description
            
        elif platform_name == "tiktok":
            # TikTok specific formatting
            title = f"{base_title} {' '.join(all_hashtags[:10])}"[:150]  # TikTok caption limit
            description = base_description
            
        elif platform_name == "instagram":
            # Instagram Reels specific formatting
            title = f"{base_title}\n\n{base_description}\n\n{' '.join(all_hashtags[:20])}"[:2200]  # Instagram caption limit
            description = ""  # Instagram uses caption for everything
            
        else:
            # Default formatting
            title = base_title
            description = base_description
        
        return {
            "title": title,
            "description": description,
            "hashtags": all_hashtags,
            "metadata": {
                "emotion": clip.get("emotion", "neutral"),
                "engagement_score": clip.get("engagement_score", 0.0),
                "source_video": clip.get("source_video", ""),
                "clip_duration": clip.get("duration", 0)
            }
        }
    
    async def _schedule_posts(self, clips: List[Dict[str, Any]]):
        """Schedule posts for optimal times"""
        try:
            scheduler_config = self.config.get_scheduler_config()
            posting_times = scheduler_config.get("posting_times", {})
            max_posts_per_day = scheduler_config.get("max_posts_per_day", 5)
            min_interval_hours = scheduler_config.get("min_interval_hours", 2)
            
            # Calculate posting schedule
            now = datetime.now()
            scheduled_posts = []
            
            # Distribute clips across optimal times
            total_clips = len(clips)
            clips_per_day = min(max_posts_per_day, total_clips)
            
            current_date = now.date()
            clip_index = 0
            
            while clip_index < total_clips:
                # Get optimal times for current date
                daily_clips = min(clips_per_day, total_clips - clip_index)
                
                for platform_name in self.platforms.keys():
                    platform_times = posting_times.get(platform_name, ["12:00"])
                    
                    # Distribute clips across available time slots
                    time_slots = platform_times[:daily_clips]
                    
                    for i, time_str in enumerate(time_slots):
                        if clip_index >= total_clips:
                            break
                        
                        # Parse time
                        hour, minute = map(int, time_str.split(':'))
                        scheduled_time = datetime.combine(current_date, datetime.min.time().replace(hour=hour, minute=minute))
                        
                        # Ensure future scheduling
                        if scheduled_time <= now:
                            scheduled_time += timedelta(days=1)
                        
                        # Add to queue
                        scheduled_posts.append({
                            "clip": clips[clip_index],
                            "platform": platform_name,
                            "scheduled_time": scheduled_time
                        })
                        
                        if platform_name == list(self.platforms.keys())[-1]:  # Last platform for this clip
                            clip_index += 1
                
                current_date += timedelta(days=1)
            
            # Add to posting queue
            self.posting_queue.extend(scheduled_posts)
            
            logger.info(f"📅 Scheduled {len(scheduled_posts)} posts across {len(clips)} clips")
            
        except Exception as e:
            logger.error(f"❌ Error scheduling posts: {e}")
    
    async def process_scheduled_posts(self):
        """Process scheduled posts (called by scheduler)"""
        if self.posting_in_progress:
            return
        
        try:
            self.posting_in_progress = True
            now = datetime.now()
            
            # Find posts ready to be published
            ready_posts = [
                post for post in self.posting_queue 
                if post["scheduled_time"] <= now
            ]
            
            if not ready_posts:
                return
            
            logger.info(f"📬 Processing {len(ready_posts)} scheduled posts")
            
            # Group by clip to avoid duplicate processing
            processed_clips = set()
            
            for post in ready_posts:
                clip = post["clip"]
                platform = post["platform"]
                
                if clip["clip_id"] not in processed_clips:
                    # Post to all platforms for this clip
                    result = await self._post_clip_to_platforms(clip)
                    processed_clips.add(clip["clip_id"])
                    
                    logger.info(f"📤 Processed scheduled post: {clip['title']}")
                
                # Remove from queue
                self.posting_queue.remove(post)
            
        except Exception as e:
            logger.error(f"❌ Error processing scheduled posts: {e}")
        finally:
            self.posting_in_progress = False
    
    async def get_posting_stats(self) -> Dict[str, Any]:
        """Get posting statistics across platforms"""
        try:
            stats = {
                "platforms": {},
                "total_posts": 0,
                "scheduled_posts": len(self.posting_queue),
                "last_updated": datetime.now().isoformat()
            }
            
            # Get stats from each platform
            for platform_name, platform_handler in self.platforms.items():
                if hasattr(platform_handler, 'get_stats'):
                    platform_stats = await platform_handler.get_stats()
                    stats["platforms"][platform_name] = platform_stats
                    stats["total_posts"] += platform_stats.get("total_posts", 0)
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting posting stats: {e}")
            return {
                "error": str(e),
                "platforms": {},
                "total_posts": 0,
                "scheduled_posts": 0,
                "last_updated": datetime.now().isoformat()
            }
    
    def add_platform(self, platform_name: str, platform_handler):
        """Add a new platform handler"""
        self.platforms[platform_name] = platform_handler
        logger.info(f"➕ Added platform: {platform_name}")
    
    def remove_platform(self, platform_name: str):
        """Remove a platform handler"""
        if platform_name in self.platforms:
            del self.platforms[platform_name]
            logger.info(f"➖ Removed platform: {platform_name}")
    
    async def test_platforms(self) -> Dict[str, Any]:
        """Test connectivity and authentication for all platforms"""
        test_results = {}
        
        for platform_name, platform_handler in self.platforms.items():
            try:
                if hasattr(platform_handler, 'test_connection'):
                    result = await platform_handler.test_connection()
                    test_results[platform_name] = {
                        "status": "success" if result else "failed",
                        "message": "Connection successful" if result else "Connection failed"
                    }
                else:
                    test_results[platform_name] = {
                        "status": "unknown",
                        "message": "Test method not available"
                    }
            except Exception as e:
                test_results[platform_name] = {
                    "status": "error",
                    "message": str(e)
                }
        
        logger.info(f"🧪 Platform test results: {test_results}")
        return test_results
