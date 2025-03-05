from enum import Enum
import os

class Platform(Enum):
    DEVTO = "dev.to"
    MASTODON = "mastodon"
    THREADS = "threads"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"

class PlatformConfig:
    """Platform configuration and availability"""
    
    @staticmethod
    def get_enabled_platforms():
        """Get list of enabled platforms"""
        # Only return platforms that have credentials configured
        enabled = []
        if os.getenv('DEVTO_API_KEY'):
            enabled.append(Platform.DEVTO)
        if os.getenv('MASTODON_ACCESS_TOKEN'):
            enabled.append(Platform.MASTODON)
        if os.getenv('INSTAGRAM_USERNAME') and os.getenv('INSTAGRAM_PASSWORD'):
            enabled.append(Platform.THREADS)
        return enabled

    @staticmethod
    def is_enabled(platform: Platform) -> bool:
        """Check if a platform is enabled"""
        return platform in PlatformConfig.get_enabled_platforms() 