"""
YouTube Shorts posting and management
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
import pickle
import os
from datetime import datetime, timedelta

from loguru import logger

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    logger.warning("⚠️ Google API libraries not available. Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")

from ..utils.config import Config


class YouTubeShortsManager:
    """Manages YouTube Shorts posting and API interactions"""
    
    # YouTube API scopes - need full access for channel info and uploading
    SCOPES = [
        'https://www.googleapis.com/auth/youtube',
        'https://www.googleapis.com/auth/youtube.upload'
    ]
    
    def __init__(self, config: Config):
        """Initialize YouTube Shorts manager"""
        self.config = config
        self.youtube_config = config.get_platform_config('youtube')
        
        self.youtube_service = None
        self.credentials = None
        self.api_key = self.youtube_config.get('api_key', '')
        
        # Authentication setup
        self.token_file = Path("youtube_token.pickle")
        credentials_file_path = self.youtube_config.get('credentials_file', 'youtube_credentials.json')
        self.credentials_file = Path(credentials_file_path)
        
        if GOOGLE_API_AVAILABLE:
            self._initialize_api()
        else:
            logger.error("❌ YouTube API not available - install required packages")
    
    def _initialize_api(self):
        """Initialize YouTube API service"""
        try:
            # Try OAuth credentials first (for uploading)
            self._setup_credentials()
            
            if self.credentials:
                self.youtube_service = build('youtube', 'v3', credentials=self.credentials)
                logger.success("✅ YouTube API service initialized with OAuth (full access)")
            elif self.api_key:
                # Fallback to API key (read-only)
                self.youtube_service = build('youtube', 'v3', developerKey=self.api_key)
                logger.success("✅ YouTube API service initialized with API key (read-only)")
                logger.warning("⚠️ Upload functionality requires OAuth credentials")
            else:
                logger.error("❌ No YouTube credentials found (API key or OAuth)")
                
        except Exception as e:
            logger.error(f"❌ Error initializing YouTube API: {e}")
    
    def _setup_credentials(self):
        """Setup YouTube API credentials"""
        try:
            # Load existing token
            if self.token_file.exists():
                with open(self.token_file, 'rb') as token:
                    self.credentials = pickle.load(token)
            
            # Check if credentials are valid
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    # Refresh expired credentials
                    self.credentials.refresh(Request())
                    logger.info("🔄 Refreshed YouTube credentials")
                else:
                    # Create new credentials
                    self._create_new_credentials()
            
            # Save credentials
            if self.credentials:
                with open(self.token_file, 'wb') as token:
                    pickle.dump(self.credentials, token)
                    
        except Exception as e:
            logger.error(f"❌ Error setting up YouTube credentials: {e}")
            self.credentials = None
    
    def _create_new_credentials(self):
        """Create new YouTube API credentials"""
        try:
            # Check for credentials file
            if not self.credentials_file.exists():
                logger.error(f"❌ YouTube credentials file not found: {self.credentials_file}")
                logger.info("📋 Please download your OAuth 2.0 credentials from Google Cloud Console:")
                logger.info("   1. Go to https://console.cloud.google.com/")
                logger.info("   2. APIs & Services → Credentials")
                logger.info("   3. Create OAuth 2.0 Client ID (Desktop application)")
                logger.info(f"   4. Download JSON and save as '{self.credentials_file}'")
                return
            
            # Run OAuth flow
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_file), self.SCOPES)
            
            # Try local server first, fallback to console
            try:
                self.credentials = flow.run_local_server(port=0)
            except Exception:
                self.credentials = flow.run_console()
            
            logger.success("✅ New YouTube credentials created")
            
        except Exception as e:
            logger.error(f"❌ Error creating YouTube credentials: {e}")
            self.credentials = None
    
    async def post_video(self, video_path: str, title: str, description: str, 
                        hashtags: list, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Post video to YouTube Shorts
        
        Args:
            video_path: Path to video file
            title: Video title
            description: Video description
            hashtags: List of hashtags
            metadata: Additional metadata
            
        Returns:
            Dictionary with upload result
        """
        if not self.youtube_service:
            return {
                "success": False,
                "error": "YouTube API service not available"
            }
        
        try:
            logger.info(f"📤 Uploading to YouTube Shorts: {title}")
            
            # Prepare video metadata
            body = await self._prepare_video_metadata(title, description, hashtags, metadata)
            
            # Create media upload
            media = MediaFileUpload(
                video_path,
                chunksize=-1,
                resumable=True,
                mimetype='video/mp4'
            )
            
            # Execute upload
            insert_request = self.youtube_service.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            response = await self._execute_upload(insert_request)
            
            if response:
                video_id = response['id']
                video_url = f"https://www.youtube.com/shorts/{video_id}"
                
                logger.success(f"✅ YouTube Shorts uploaded: {video_url}")
                
                return {
                    "success": True,
                    "post_id": video_id,
                    "post_url": video_url,
                    "message": "Successfully uploaded to YouTube Shorts"
                }
            else:
                return {
                    "success": False,
                    "error": "Upload failed - no response from YouTube API"
                }
                
        except Exception as e:
            logger.error(f"❌ Error uploading to YouTube Shorts: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _prepare_video_metadata(self, title: str, description: str, 
                                    hashtags: list, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Prepare video metadata for YouTube upload"""
        # Get configuration
        shorts_config = self.youtube_config.get('shorts', {})
        
        # Combine description with hashtags
        full_description = description
        if hashtags:
            hashtag_text = ' '.join(hashtags[:15])  # YouTube limit
            full_description = f"{description}\n\n{hashtag_text}"
        
        # Prepare body
        body = {
            'snippet': {
                'title': title[:100],  # YouTube title limit
                'description': full_description[:5000],  # YouTube description limit
                'categoryId': str(shorts_config.get('categories', [22])[0]),  # Default to People & Blogs
                'defaultLanguage': 'en',
                'defaultAudioLanguage': 'en'
            },
            'status': {
                'privacyStatus': shorts_config.get('privacy', 'public'),
                'selfDeclaredMadeForKids': False
            }
        }
        
        # Add tags if provided
        if hashtags:
            # Extract tag words from hashtags
            tags = []
            for hashtag in hashtags[:10]:  # YouTube allows max 500 characters for tags
                tag = hashtag.replace('#', '').strip()
                if tag:
                    tags.append(tag)
            
            if tags:
                body['snippet']['tags'] = tags
        
        return body
    
    async def _execute_upload(self, insert_request) -> Optional[Dict[str, Any]]:
        """Execute the upload request with retries"""
        try:
            response = None
            error = None
            retry = 0
            max_retries = 3
            
            while response is None and retry < max_retries:
                try:
                    status, response = insert_request.next_chunk()
                    if response is not None:
                        if 'id' in response:
                            logger.info(f"📹 Video uploaded successfully: {response['id']}")
                            return response
                        else:
                            error = f"Upload failed: {response}"
                            break
                except Exception as e:
                    error = str(e)
                    retry += 1
                    if retry < max_retries:
                        logger.warning(f"⚠️ Upload attempt {retry} failed, retrying...")
                        await asyncio.sleep(2 ** retry)  # Exponential backoff
                    
            if error:
                logger.error(f"❌ Upload failed after {max_retries} attempts: {error}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error executing upload: {e}")
            return None
    
    async def test_connection(self) -> bool:
        """Test YouTube API connection"""
        if not self.youtube_service:
            return False
        
        try:
            # Try to get channel info
            response = self.youtube_service.channels().list(
                part='snippet',
                mine=True
            ).execute()
            
            if response.get('items'):
                channel_name = response['items'][0]['snippet']['title']
                logger.info(f"✅ YouTube connection test successful - Channel: {channel_name}")
                return True
            else:
                logger.error("❌ No channel found for authenticated user")
                return False
                
        except Exception as e:
            logger.error(f"❌ YouTube connection test failed: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get YouTube channel statistics"""
        if not self.youtube_service:
            return {"error": "YouTube API not available"}
        
        try:
            # Get channel statistics
            response = self.youtube_service.channels().list(
                part='statistics,snippet',
                mine=True
            ).execute()
            
            if response.get('items'):
                channel = response['items'][0]
                stats = channel.get('statistics', {})
                snippet = channel.get('snippet', {})
                
                return {
                    "channel_name": snippet.get('title', 'Unknown'),
                    "subscriber_count": int(stats.get('subscriberCount', 0)),
                    "total_views": int(stats.get('viewCount', 0)),
                    "video_count": int(stats.get('videoCount', 0)),
                    "last_updated": datetime.now().isoformat()
                }
            else:
                return {"error": "No channel data available"}
                
        except Exception as e:
            logger.error(f"❌ Error getting YouTube stats: {e}")
            return {"error": str(e)}
    
    async def get_recent_videos(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """Get recent uploaded videos"""
        if not self.youtube_service:
            return []
        
        try:
            # Get uploads playlist ID
            channel_response = self.youtube_service.channels().list(
                part='contentDetails',
                mine=True
            ).execute()
            
            if not channel_response.get('items'):
                return []
            
            uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # Get recent videos
            playlist_response = self.youtube_service.playlistItems().list(
                part='snippet',
                playlistId=uploads_playlist_id,
                maxResults=max_results
            ).execute()
            
            videos = []
            for item in playlist_response.get('items', []):
                snippet = item['snippet']
                video_id = snippet['resourceId']['videoId']
                
                videos.append({
                    'video_id': video_id,
                    'title': snippet['title'],
                    'description': snippet['description'][:100] + '...',
                    'published_at': snippet['publishedAt'],
                    'url': f"https://www.youtube.com/watch?v={video_id}"
                })
            
            return videos
            
        except Exception as e:
            logger.error(f"❌ Error getting recent YouTube videos: {e}")
            return []
    
    def setup_webhook(self, webhook_url: str) -> bool:
        """Setup webhook for YouTube notifications (if supported)"""
        try:
            # YouTube doesn't have direct webhook support for uploads
            # This would need to be implemented with periodic polling
            # or using YouTube Data API push notifications
            logger.info("📢 YouTube webhook setup - using polling method")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting up YouTube webhook: {e}")
            return False
