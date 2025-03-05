from typing import Dict, List, Any
from .base import SocialMediaPlatform
from .devto import DevTo
from .mastodon import Mastodon
from .threads_api import ThreadsAPI  # Import the new API-based implementation
from ..config.platforms import Platform, PlatformConfig

class PlatformManager:
    """Manages multiple social media platforms"""
    
    def __init__(self):
        self.platforms: Dict[Platform, SocialMediaPlatform] = {}
        self._initialize_platforms()

    def _initialize_platforms(self):
        """Initialize all enabled platforms"""
        platform_map = {
            Platform.DEVTO: DevTo,
            Platform.MASTODON: Mastodon,
            Platform.THREADS: ThreadsAPI,  # Use the API implementation instead of Selenium
            # ... other platforms
        }
        
        enabled_platforms = PlatformConfig.get_enabled_platforms()
        
        for platform in enabled_platforms:
            if platform in platform_map:
                self.platforms[platform] = platform_map[platform]()

    def authenticate_all(self) -> Dict[Platform, bool]:
        """Authenticate all platforms"""
        results = {}
        for platform, instance in self.platforms.items():
            results[platform] = instance.authenticate()
        return results

    def post_to_platform(self, platform: Platform, content: str, **kwargs) -> Dict[str, Any]:
        """Post content to specific platform"""
        if platform not in self.platforms:
            return {"success": False, "error": f"Platform {platform.value} not initialized"}
            
        return self.platforms[platform].post_content(content, **kwargs)

    def post_to_all(self, content: str, **kwargs) -> Dict[Platform, Dict[str, Any]]:
        """Post content to all platforms"""
        results = {}
        for platform, instance in self.platforms.items():
            results[platform] = instance.post_content(content, **kwargs)
        return results

    def check_platform_status(self, platform: Platform) -> bool:
        """Check status of specific platform"""
        if platform not in self.platforms:
            return False
        return self.platforms[platform].check_status()

    def check_all_statuses(self) -> Dict[Platform, bool]:
        """Check status of all platforms"""
        return {
            platform: instance.check_status() 
            for platform, instance in self.platforms.items()
        } 