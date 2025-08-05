"""
Configuration management for Clippy
"""

import yaml
import os
from pathlib import Path
from typing import Any, Dict, Optional
from loguru import logger


class Config:
    """Configuration manager for Clippy application"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize configuration from YAML file"""
        self.config_path = Path(config_path)
        self._config = {}
        self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f) or {}
                logger.info(f"✅ Configuration loaded from {self.config_path}")
            else:
                logger.warning(f"⚠️ Configuration file not found: {self.config_path}")
                self._config = {}
        except Exception as e:
            logger.error(f"❌ Error loading configuration: {e}")
            self._config = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key: Configuration key (supports dot notation like 'video.resolution')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """
        Set configuration value using dot notation
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        keys = key.split('.')
        config = self._config
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the final value
        config[keys[-1]] = value
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, indent=2)
            logger.info(f"💾 Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"❌ Error saving configuration: {e}")
    
    def get_platform_config(self, platform: str) -> Dict[str, Any]:
        """Get configuration for a specific platform"""
        return self.get(f"platforms.{platform}", {})
    
    def get_video_config(self) -> Dict[str, Any]:
        """Get video processing configuration"""
        return self.get("video", {})
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI model configuration"""
        return self.get("ai", {})
    
    def get_caption_config(self) -> Dict[str, Any]:
        """Get caption generation configuration"""
        return self.get("captions", {})
    
    def get_scheduler_config(self) -> Dict[str, Any]:
        """Get scheduler configuration"""
        return self.get("scheduler", {})
    
    def get_analytics_config(self) -> Dict[str, Any]:
        """Get analytics configuration"""
        return self.get("analytics", {})
    
    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration"""
        return self.get("storage", {})
    
    def get_hashtag_config(self) -> Dict[str, Any]:
        """Get hashtag generation configuration"""
        return self.get("hashtags", {})
    
    def is_platform_enabled(self, platform: str) -> bool:
        """Check if a platform is enabled"""
        return self.get(f"platforms.{platform}.enabled", False)
    
    def get_output_path(self) -> Path:
        """Get output directory path"""
        return Path(self.get("video.output_path", "./output"))
    
    def get_download_path(self) -> Path:
        """Get download directory path"""
        return Path(self.get("video.download_path", "./downloads"))
    
    def get_temp_path(self) -> Path:
        """Get temporary directory path"""
        return Path(self.get("video.temp_path", "./temp"))
    
    def ensure_directories(self):
        """Ensure all configured directories exist"""
        directories = [
            self.get_output_path(),
            self.get_download_path(),
            self.get_temp_path(),
            Path("./logs"),
            Path("./models")
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def validate_config(self) -> list:
        """
        Validate configuration and return list of issues
        
        Returns:
            List of configuration issues/warnings
        """
        issues = []
        
        # Check required directories
        try:
            self.ensure_directories()
        except Exception as e:
            issues.append(f"Directory creation failed: {e}")
        
        # Check platform configurations
        for platform in ['youtube', 'tiktok', 'instagram']:
            if self.is_platform_enabled(platform):
                platform_config = self.get_platform_config(platform)
                
                if platform == 'youtube':
                    if not platform_config.get('client_id') or not platform_config.get('client_secret'):
                        issues.append(f"YouTube API credentials missing")
                
                elif platform in ['tiktok', 'instagram']:
                    if not platform_config.get('username') or not platform_config.get('password'):
                        issues.append(f"{platform.title()} credentials missing")
        
        # Check AI model settings
        ai_config = self.get_ai_config()
        if not ai_config.get('whisper', {}).get('model'):
            issues.append("Whisper model not configured")
        
        if not ai_config.get('llm', {}).get('model'):
            issues.append("LLM model not configured")
        
        # Check video settings
        video_config = self.get_video_config()
        if not video_config.get('resolution'):
            issues.append("Video resolution not configured")
        
        return issues


class EnvironmentConfig:
    """Environment-specific configuration helpers"""
    
    @staticmethod
    def get_env_var(name: str, default: str = None) -> Optional[str]:
        """Get environment variable with optional default"""
        return os.getenv(name, default)
    
    @staticmethod
    def is_development() -> bool:
        """Check if running in development mode"""
        return os.getenv('CLIPPY_ENV', 'production').lower() in ['dev', 'development']
    
    @staticmethod
    def is_production() -> bool:
        """Check if running in production mode"""
        return os.getenv('CLIPPY_ENV', 'production').lower() == 'production'
    
    @staticmethod
    def get_log_level() -> str:
        """Get log level from environment"""
        return os.getenv('CLIPPY_LOG_LEVEL', 'INFO').upper()


# Global configuration instance
config = Config()
