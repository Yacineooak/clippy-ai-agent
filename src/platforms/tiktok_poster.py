"""
TikTok posting automation using browser automation
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import random

from loguru import logger

try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("⚠️ Playwright not available. Install with: pip install playwright")

from ..utils.config import Config


class TikTokPoster:
    """Automates TikTok posting using browser automation"""
    
    def __init__(self, config: Config):
        """Initialize TikTok poster"""
        self.config = config
        self.tiktok_config = config.get_platform_config('tiktok')
        
        self.browser = None
        self.page = None
        self.is_logged_in = False
        
        # TikTok URLs
        self.login_url = "https://www.tiktok.com/login"
        self.upload_url = "https://www.tiktok.com/upload"
        
        # User credentials
        self.username = self.tiktok_config.get('username', '')
        self.password = self.tiktok_config.get('password', '')
        
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("❌ TikTok automation not available - install Playwright")
    
    async def _initialize_browser(self):
        """Initialize browser for automation"""
        if not PLAYWRIGHT_AVAILABLE:
            return False
        
        try:
            playwright = await async_playwright().start()
            
            # Launch browser
            self.browser = await playwright.chromium.launch(
                headless=self.tiktok_config.get('headless', True),
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            # Create context with realistic user agent
            context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            self.page = await context.new_page()
            
            # Add stealth measures
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)
            
            logger.success("✅ TikTok browser initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error initializing TikTok browser: {e}")
            return False
    
    async def _login(self) -> bool:
        """Login to TikTok"""
        try:
            if not self.page:
                await self._initialize_browser()
            
            logger.info("🔐 Logging into TikTok...")
            
            # Navigate to login page
            await self.page.goto(self.login_url, wait_until='networkidle')
            
            # Wait for page to load
            await asyncio.sleep(3)
            
            # Look for username/email login option
            try:
                # Try to find "Use phone / email / username" link
                email_login_button = await self.page.wait_for_selector(
                    'a[href*="login/phone-or-email"]', 
                    timeout=10000
                )
                await email_login_button.click()
                await asyncio.sleep(2)
                
                # Click on "Log in with email or username"
                username_tab = await self.page.wait_for_selector(
                    'div[data-e2e="login-with-username"]',
                    timeout=10000
                )
                await username_tab.click()
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.warning(f"⚠️ Could not find email/username login: {e}")
                # Try alternative selectors
                pass
            
            # Fill username
            username_input = await self.page.wait_for_selector(
                'input[name="username"], input[placeholder*="Email"], input[placeholder*="Username"]',
                timeout=10000
            )
            await username_input.fill(self.username)
            await asyncio.sleep(1)
            
            # Fill password
            password_input = await self.page.wait_for_selector(
                'input[type="password"]',
                timeout=10000
            )
            await password_input.fill(self.password)
            await asyncio.sleep(1)
            
            # Click login button
            login_button = await self.page.wait_for_selector(
                'button[data-e2e="login-button"], button[type="submit"]',
                timeout=10000
            )
            await login_button.click()
            
            # Wait for login to complete
            await asyncio.sleep(5)
            
            # Check if login was successful
            try:
                # Look for upload button or profile indicator
                await self.page.wait_for_selector(
                    '[data-e2e="nav-upload"], [data-e2e="profile-icon"]',
                    timeout=15000
                )
                self.is_logged_in = True
                logger.success("✅ TikTok login successful")
                return True
                
            except Exception:
                # Check for CAPTCHA or error messages
                captcha_present = await self.page.locator('iframe[title*="captcha"]').count() > 0
                if captcha_present:
                    logger.warning("⚠️ CAPTCHA detected - manual intervention required")
                    return False
                
                error_message = await self.page.locator('[data-e2e="login-error"]').text_content()
                if error_message:
                    logger.error(f"❌ Login error: {error_message}")
                
                return False
                
        except Exception as e:
            logger.error(f"❌ Error logging into TikTok: {e}")
            return False
    
    async def post_video(self, video_path: str, title: str, description: str, 
                        hashtags: list, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Post video to TikTok
        
        Args:
            video_path: Path to video file
            title: Video title (used in caption)
            description: Video description
            hashtags: List of hashtags
            metadata: Additional metadata
            
        Returns:
            Dictionary with upload result
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {
                "success": False,
                "error": "Playwright not available"
            }
        
        try:
            logger.info(f"📤 Uploading to TikTok: {title}")
            
            # Ensure we're logged in
            if not self.is_logged_in:
                login_success = await self._login()
                if not login_success:
                    return {
                        "success": False,
                        "error": "Failed to login to TikTok"
                    }
            
            # Navigate to upload page
            await self.page.goto(self.upload_url, wait_until='networkidle')
            await asyncio.sleep(3)
            
            # Upload video file
            upload_success = await self._upload_video_file(video_path)
            if not upload_success:
                return {
                    "success": False,
                    "error": "Failed to upload video file"
                }
            
            # Add caption with title, description, and hashtags
            caption = await self._prepare_caption(title, description, hashtags)
            caption_success = await self._add_caption(caption)
            if not caption_success:
                logger.warning("⚠️ Failed to add caption")
            
            # Configure video settings
            await self._configure_video_settings(metadata)
            
            # Publish video
            publish_success = await self._publish_video()
            if publish_success:
                logger.success("✅ TikTok video published successfully")
                return {
                    "success": True,
                    "post_id": f"tiktok_{int(time.time())}",  # TikTok doesn't return post ID easily
                    "post_url": "https://www.tiktok.com/@" + self.username,
                    "message": "Successfully posted to TikTok"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to publish video"
                }
                
        except Exception as e:
            logger.error(f"❌ Error posting to TikTok: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _upload_video_file(self, video_path: str) -> bool:
        """Upload video file to TikTok"""
        try:
            # Wait for file input
            file_input = await self.page.wait_for_selector(
                'input[type="file"]',
                timeout=10000
            )
            
            # Upload file
            await file_input.set_input_files(video_path)
            
            # Wait for upload to complete
            await asyncio.sleep(5)
            
            # Wait for video processing
            try:
                await self.page.wait_for_selector(
                    '[data-e2e="upload-complete"], .upload-complete, [class*="complete"]',
                    timeout=60000  # Wait up to 1 minute for processing
                )
                logger.info("📹 Video upload and processing complete")
                return True
                
            except Exception:
                # Alternative check - look for caption input which appears after upload
                try:
                    await self.page.wait_for_selector(
                        '[data-e2e="video-caption"], textarea[placeholder*="caption"], textarea[placeholder*="describe"]',
                        timeout=30000
                    )
                    logger.info("📹 Video upload complete (detected caption input)")
                    return True
                except Exception:
                    logger.error("❌ Video upload may have failed or timed out")
                    return False
                
        except Exception as e:
            logger.error(f"❌ Error uploading video file: {e}")
            return False
    
    async def _prepare_caption(self, title: str, description: str, hashtags: list) -> str:
        """Prepare TikTok caption"""
        # Combine title and description
        caption_parts = []
        
        if title:
            caption_parts.append(title)
        
        if description and description != title:
            caption_parts.append(description)
        
        # Add hashtags
        if hashtags:
            hashtag_text = ' '.join(hashtags[:10])  # TikTok works well with 5-10 hashtags
            caption_parts.append(hashtag_text)
        
        caption = '\n\n'.join(caption_parts)
        
        # TikTok caption limit is around 2200 characters
        if len(caption) > 2200:
            caption = caption[:2197] + "..."
        
        return caption
    
    async def _add_caption(self, caption: str) -> bool:
        """Add caption to TikTok video"""
        try:
            # Find caption input
            caption_input = await self.page.wait_for_selector(
                '[data-e2e="video-caption"], textarea[placeholder*="caption"], textarea[placeholder*="describe"]',
                timeout=10000
            )
            
            # Clear existing text and add caption
            await caption_input.click()
            await self.page.keyboard.press('Control+A')
            await caption_input.fill(caption)
            
            await asyncio.sleep(2)
            logger.info("📝 Caption added successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding caption: {e}")
            return False
    
    async def _configure_video_settings(self, metadata: Dict[str, Any] = None):
        """Configure TikTok video settings"""
        try:
            await asyncio.sleep(2)
            
            # Set video to public (default)
            try:
                public_option = await self.page.locator('text="Public"').first
                if await public_option.is_visible():
                    await public_option.click()
            except Exception:
                pass
            
            # Allow comments (default)
            try:
                allow_comments = await self.page.locator('text="Allow comments"').first
                if await allow_comments.is_visible():
                    await allow_comments.click()
            except Exception:
                pass
            
            # Allow duet (default for viral content)
            try:
                allow_duet = await self.page.locator('text="Allow Duet"').first
                if await allow_duet.is_visible():
                    await allow_duet.click()
            except Exception:
                pass
            
            logger.info("⚙️ Video settings configured")
            
        except Exception as e:
            logger.warning(f"⚠️ Error configuring video settings: {e}")
    
    async def _publish_video(self) -> bool:
        """Publish the video"""
        try:
            # Find and click publish button
            publish_button = await self.page.wait_for_selector(
                '[data-e2e="publish-button"], button[type="submit"], button:has-text("Post")',
                timeout=10000
            )
            
            await publish_button.click()
            
            # Wait for publishing to complete
            try:
                # Wait for success message or redirect
                await self.page.wait_for_selector(
                    '[data-e2e="upload-success"], .upload-success, text="Your video is being uploaded"',
                    timeout=30000
                )
                return True
                
            except Exception:
                # Alternative check - wait for URL change
                await asyncio.sleep(10)
                current_url = self.page.url
                if 'upload' not in current_url:
                    return True
                else:
                    return False
                
        except Exception as e:
            logger.error(f"❌ Error publishing video: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Test TikTok connection by attempting login"""
        try:
            if not self.username or not self.password:
                logger.error("❌ TikTok credentials not configured")
                return False
            
            login_success = await self._login()
            
            if login_success:
                # Try to navigate to upload page
                await self.page.goto(self.upload_url, wait_until='networkidle')
                await asyncio.sleep(3)
                
                # Check if upload page is accessible
                upload_elements = await self.page.locator('input[type="file"]').count()
                if upload_elements > 0:
                    logger.success("✅ TikTok connection test successful")
                    return True
                else:
                    logger.error("❌ Cannot access TikTok upload page")
                    return False
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ TikTok connection test failed: {e}")
            return False
        finally:
            # Close browser
            await self._cleanup()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get TikTok account stats"""
        try:
            if not self.is_logged_in:
                await self._login()
            
            # Navigate to profile
            profile_url = f"https://www.tiktok.com/@{self.username}"
            await self.page.goto(profile_url, wait_until='networkidle')
            await asyncio.sleep(3)
            
            # Extract stats
            stats = {}
            
            # Try to get follower count
            try:
                followers_element = await self.page.locator('[data-e2e="followers-count"]').first
                followers_text = await followers_element.text_content()
                stats['followers'] = followers_text
            except Exception:
                stats['followers'] = 'Unknown'
            
            # Try to get following count
            try:
                following_element = await self.page.locator('[data-e2e="following-count"]').first
                following_text = await following_element.text_content()
                stats['following'] = following_text
            except Exception:
                stats['following'] = 'Unknown'
            
            # Try to get likes count
            try:
                likes_element = await self.page.locator('[data-e2e="likes-count"]').first
                likes_text = await likes_element.text_content()
                stats['total_likes'] = likes_text
            except Exception:
                stats['total_likes'] = 'Unknown'
            
            return {
                **stats,
                "last_updated": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting TikTok stats: {e}")
            return {"error": str(e)}
    
    async def _cleanup(self):
        """Clean up browser resources"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            self.page = None
            self.browser = None
            self.is_logged_in = False
            
        except Exception as e:
            logger.warning(f"⚠️ Error during TikTok cleanup: {e}")
    
    def __del__(self):
        """Cleanup on object deletion"""
        if self.browser:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._cleanup())
                else:
                    loop.run_until_complete(self._cleanup())
            except Exception:
                pass
