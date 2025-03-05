from typing import Dict, Any
import os

class ThreadsConfig:
    """Configuration settings for Threads platform"""
    
    @staticmethod
    def get_config() -> Dict[str, Any]:
        """Get Threads configuration settings"""
        return {
            'max_content_length': 500,
            'max_retries': 3,
            'retry_delay': 2,  # seconds
            'timeout': 30,  # seconds
            'headless': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'login_url': 'https://www.instagram.com/accounts/login/',
            'threads_url': 'https://www.threads.net',
            'status_url': 'https://www.threads.net/status'
        }
    
    @staticmethod
    def validate_credentials() -> bool:
        """Validate that required credentials are present"""
        return bool(
            os.getenv('INSTAGRAM_USERNAME') and 
            os.getenv('INSTAGRAM_PASSWORD')
        )
    
    @staticmethod
    def get_selenium_options() -> Dict[str, Any]:
        """Get Selenium WebDriver options"""
        return {
            'arguments': [
                '--headless',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-extensions',
                '--disable-notifications'
            ],
            'experimental_options': {
                'excludeSwitches': ['enable-automation', 'enable-logging'],
                'prefs': {
                    'profile.default_content_setting_values.notifications': 2
                }
            }
        }

    @staticmethod
    def get_content_rules() -> Dict[str, Any]:
        """Get content rules and restrictions"""
        return {
            'max_length': 500,
            'min_length': 1,
            'banned_words': ['spam', 'advertise', 'promotion'],
            'max_hashtags': 5,
            'max_mentions': 5,
            'allowed_media_types': ['image/jpeg', 'image/png', 'video/mp4'],
            'max_media_size': 10 * 1024 * 1024  # 10MB
        }

    @staticmethod
    def get_rate_limits() -> Dict[str, Any]:
        """Get rate limiting settings"""
        return {
            'posts_per_hour': 5,
            'posts_per_day': 20,
            'minimum_interval': 300,  # 5 minutes between posts
            'cooldown_period': 3600  # 1 hour cooldown if limit reached
        }

    @staticmethod
    def get_media_config() -> Dict[str, Any]:
        """Get media handling configuration"""
        return {
            'max_image_size': (1080, 1080),
            'image_quality': 85,
            'supported_formats': ['.jpg', '.jpeg', '.png'],
            'max_file_size': 10 * 1024 * 1024  # 10MB
        } 