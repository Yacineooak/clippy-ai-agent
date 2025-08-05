#!/usr/bin/env python3
"""
Quick test script to verify YouTube OAuth setup
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

try:
    from src.utils.config import Config
    from src.platforms.youtube_shorts import YouTubeShortsManager
    
    print("🧪 Testing YouTube OAuth setup...")
    
    # Load config
    config = Config("config.yaml")
    print("✅ Config loaded successfully")
    
    # Initialize YouTube manager
    youtube = YouTubeShortsManager(config)
    print("✅ YouTube manager initialized")
    
    # Check if credentials file exists
    if youtube.credentials_file.exists():
        print(f"✅ Credentials file found: {youtube.credentials_file}")
    else:
        print(f"❌ Credentials file missing: {youtube.credentials_file}")
        
    # Check API service
    if youtube.youtube_service:
        print("✅ YouTube API service available")
        
        # Try to get channel info (requires authentication)
        try:
            # This will trigger OAuth flow if needed
            request = youtube.youtube_service.channels().list(
                part="snippet,contentDetails,statistics",
                mine=True
            )
            response = request.execute()
            
            if response.get('items'):
                channel = response['items'][0]
                print(f"✅ Successfully authenticated!")
                print(f"📺 Channel: {channel['snippet']['title']}")
                print(f"👥 Subscribers: {channel['statistics'].get('subscriberCount', 'Hidden')}")
            else:
                print("⚠️ No channel found for authenticated user")
                
        except Exception as e:
            print(f"🔐 Authentication required: {e}")
            print("💡 This is normal on first run - OAuth browser will open")
    else:
        print("❌ YouTube API service not available")
        
except Exception as e:
    print(f"❌ Error during test: {e}")
    import traceback
    traceback.print_exc()
