"""
Instagram Reels posting automation
"""

import asyncio
import time
import random
from typing import Dict, Any, Optional, List
from pathlib import Path

from loguru import logger

try:
    from instagrapi import Client
    from instagrapi.exceptions import LoginRequired, ChallengeRequired, TwoFactorRequired
    INSTAGRAPI_AVAILABLE = True
except ImportError:
    INSTAGRAPI_AVAILABLE = False
    logger.warning("⚠️ Instagrapi not available. Install with: pip install instagrapi")

from ..utils.config import Config


class InstagramReelsPoster:
    """Manages Instagram Reels posting using instagrapi"""
    
    def __init__(self, config: Config):
        """Initialize Instagram Reels poster"""
        self.config = config
        self.instagram_config = config.get_platform_config('instagram')
        
        self.client = None
        self.is_logged_in = False
        
        # User credentials
        self.username = self.instagram_config.get('username', '')
        self.password = self.instagram_config.get('password', '')
        
        # Session file for persistent login
        self.session_file = Path(f"instagram_session_{self.username}.json")
        
        if INSTAGRAPI_AVAILABLE:
            self._initialize_client()
        else:
            logger.error("❌ Instagram automation not available - install instagrapi")
    
    def _initialize_client(self):
        """Initialize Instagram client"""
        try:
            self.client = Client()
            
            # Configure client settings
            self.client.delay_range = [2, 5]  # Random delay between requests
            
            # Try to load existing session
            if self.session_file.exists():
                try:
                    self.client.load_settings(str(self.session_file))
                    logger.info("📱 Loaded Instagram session from file")
                except Exception as e:
                    logger.warning(f"⚠️ Could not load Instagram session: {e}")
            
            logger.success("✅ Instagram client initialized")
            
        except Exception as e:
            logger.error(f"❌ Error initializing Instagram client: {e}")
            self.client = None
    
    async def _login(self) -> bool:
        """Login to Instagram"""
        if not self.client:
            return False
        
        try:
            logger.info("🔐 Logging into Instagram...")
            
            # Check if already logged in
            try:
                user_id = self.client.user_id_from_username(self.username)
                if user_id:
                    self.is_logged_in = True
                    logger.info("✅ Already logged in to Instagram")
                    return True
            except Exception:
                pass
            
            # Attempt login
            self.is_logged_in = self.client.login(self.username, self.password)
            
            if self.is_logged_in:
                # Save session
                self.client.dump_settings(str(self.session_file))
                logger.success("✅ Instagram login successful")
                return True
            else:
                logger.error("❌ Instagram login failed")
                return False
                
        except TwoFactorRequired:
            logger.error("❌ Two-factor authentication required for Instagram")
            # You would need to implement 2FA handling here
            return False
            
        except ChallengeRequired:
            logger.error("❌ Instagram challenge required (suspicious activity)")
            # You would need to implement challenge handling here
            return False
            
        except Exception as e:
            logger.error(f"❌ Error logging into Instagram: {e}")
            return False
    
    async def post_video(self, video_path: str, title: str, description: str, 
                        hashtags: list, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Post video to Instagram Reels
        
        Args:
            video_path: Path to video file
            title: Video title (used in caption)
            description: Video description
            hashtags: List of hashtags
            metadata: Additional metadata
            
        Returns:
            Dictionary with upload result
        """
        if not INSTAGRAPI_AVAILABLE:
            return {
                "success": False,
                "error": "Instagrapi not available"
            }
        
        try:
            logger.info(f"📤 Uploading to Instagram Reels: {title}")
            
            # Ensure we're logged in
            if not self.is_logged_in:
                login_success = await self._login()
                if not login_success:
                    return {
                        "success": False,
                        "error": "Failed to login to Instagram"
                    }
            
            # Prepare caption
            caption = await self._prepare_caption(title, description, hashtags)
            
            # Upload as Reel
            reel = self.client.clip_upload(
                Path(video_path),
                caption=caption,
                extra_data={
                    "custom_accessibility_caption": title,
                    "disable_comments": False,
                }
            )
            
            if reel:
                reel_url = f"https://www.instagram.com/reel/{reel.code}/"
                logger.success(f"✅ Instagram Reel uploaded: {reel_url}")
                
                return {
                    "success": True,
                    "post_id": reel.id,
                    "post_url": reel_url,
                    "message": "Successfully posted to Instagram Reels"
                }
            else:
                return {
                    "success": False,
                    "error": "Upload failed - no response from Instagram"
                }
                
        except Exception as e:
            logger.error(f"❌ Error posting to Instagram Reels: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _prepare_caption(self, title: str, description: str, hashtags: list) -> str:
        """Prepare Instagram Reels caption"""
        caption_parts = []
        
        # Add title
        if title:
            caption_parts.append(title)
        
        # Add description
        if description and description != title:
            caption_parts.append(description)
        
        # Add hashtags
        if hashtags:
            # Instagram works well with 5-10 hashtags for Reels
            hashtag_text = ' '.join(hashtags[:20])  # Instagram allows up to 30 hashtags
            caption_parts.append(hashtag_text)
        
        caption = '\n\n'.join(caption_parts)
        
        # Instagram caption limit is 2200 characters
        if len(caption) > 2200:
            caption = caption[:2197] + "..."
        
        return caption
    
    async def test_connection(self) -> bool:
        """Test Instagram connection"""
        try:
            if not self.username or not self.password:
                logger.error("❌ Instagram credentials not configured")
                return False
            
            login_success = await self._login()
            
            if login_success:
                # Try to get account info
                user_info = self.client.account_info()
                if user_info:
                    logger.success(f"✅ Instagram connection test successful - User: {user_info.username}")
                    return True
                else:
                    logger.error("❌ Cannot get Instagram account info")
                    return False
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ Instagram connection test failed: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Instagram account statistics"""
        try:
            if not self.is_logged_in:
                await self._login()
            
            # Get account info
            user_info = self.client.account_info()
            
            if user_info:
                return {
                    "username": user_info.username,
                    "full_name": user_info.full_name,
                    "follower_count": user_info.follower_count,
                    "following_count": user_info.following_count,
                    "media_count": user_info.media_count,
                    "biography": user_info.biography[:100] + "..." if len(user_info.biography) > 100 else user_info.biography,
                    "is_verified": user_info.is_verified,
                    "is_business": user_info.is_business,
                    "last_updated": time.time()
                }
            else:
                return {"error": "Could not get account info"}
                
        except Exception as e:
            logger.error(f"❌ Error getting Instagram stats: {e}")
            return {"error": str(e)}
    
    async def get_recent_reels(self, max_count: int = 10) -> list:
        """Get recent Reels from account"""
        try:
            if not self.is_logged_in:
                await self._login()
            
            # Get user ID
            user_id = self.client.user_id_from_username(self.username)
            
            # Get recent clips/reels
            reels = self.client.user_clips(user_id, amount=max_count)
            
            reel_data = []
            for reel in reels:
                reel_data.append({
                    "id": reel.id,
                    "code": reel.code,
                    "url": f"https://www.instagram.com/reel/{reel.code}/",
                    "caption": reel.caption_text[:100] + "..." if len(reel.caption_text) > 100 else reel.caption_text,
                    "like_count": reel.like_count,
                    "comment_count": reel.comment_count,
                    "play_count": reel.play_count if hasattr(reel, 'play_count') else 0,
                    "taken_at": reel.taken_at.isoformat() if reel.taken_at else None
                })
            
            return reel_data
            
        except Exception as e:
            logger.error(f"❌ Error getting recent Instagram Reels: {e}")
            return []
    
    async def get_reel_insights(self, reel_id: str) -> Dict[str, Any]:
        """Get insights for a specific Reel (requires business account)"""
        try:
            if not self.is_logged_in:
                await self._login()
            
            # Get media insights (only works for business accounts)
            try:
                insights = self.client.insights_media(reel_id)
                return {
                    "reach": insights.get('reach', 0),
                    "impressions": insights.get('impressions', 0),
                    "likes": insights.get('likes', 0),
                    "comments": insights.get('comments', 0),
                    "shares": insights.get('shares', 0),
                    "saves": insights.get('saves', 0)
                }
            except Exception as e:
                logger.warning(f"⚠️ Could not get Reel insights (may require business account): {e}")
                return {"error": "Insights not available"}
                
        except Exception as e:
            logger.error(f"❌ Error getting Reel insights: {e}")
            return {"error": str(e)}
    
    async def schedule_story_promotion(self, reel_id: str, delay_hours: int = 1) -> bool:
        """Schedule promotion of Reel to Stories"""
        try:
            if not self.is_logged_in:
                await self._login()
            
            # Add to story after delay (simple implementation)
            await asyncio.sleep(delay_hours * 3600)
            
            # Get reel media
            reel_media = self.client.media_info(reel_id)
            
            # Share to story
            story = self.client.video_story_share(
                video_url=reel_media.video_url,
                caption="Check out my latest Reel! 🔥"
            )
            
            if story:
                logger.success("✅ Reel promoted to Instagram Story")
                return True
            else:
                logger.error("❌ Failed to promote Reel to Story")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error promoting Reel to Story: {e}")
            return False
    
    def logout(self):
        """Logout and clean up session"""
        try:
            if self.client and self.is_logged_in:
                self.client.logout()
                self.is_logged_in = False
                
                # Remove session file
                if self.session_file.exists():
                    self.session_file.unlink()
                
                logger.info("👋 Logged out of Instagram")
                
        except Exception as e:
            logger.warning(f"⚠️ Error during Instagram logout: {e}")
    
    def __del__(self):
        """Cleanup on object deletion"""
        self.logout()
