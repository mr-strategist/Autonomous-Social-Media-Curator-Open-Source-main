import os
import requests
import json
import time
from typing import Dict, Any
from .base import SocialMediaPlatform
from ..config.platforms import Platform
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging.config
from ..config.threads_config import ThreadsConfig
from datetime import datetime
import mimetypes
from PIL import Image
from io import BytesIO
from ..utils.rate_limiter import RateLimiter
import random

# Configure logging for Threads
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.FileHandler',
            'filename': 'threads.log',
            'mode': 'a',
        },
    },
    'loggers': {
        'threads': {
            'handlers': ['default', 'file'],
            'level': 'INFO',
            'propagate': True
        }
    }
})

logger = logging.getLogger('threads')

class ThreadsError(Exception):
    """Custom exception for Threads-related errors"""
    pass

class ThreadsAuthenticationError(ThreadsError):
    """Raised when authentication fails"""
    pass

class ThreadsPostingError(ThreadsError):
    """Raised when posting fails"""
    pass

class ThreadsMediaError(ThreadsError):
    """Raised when there's an issue with media handling"""
    pass

class Threads(SocialMediaPlatform):
    """Threads platform implementation using Instagram's API"""
    
    def __init__(self):
        super().__init__(Platform.THREADS)
        self.config = ThreadsConfig.get_config()
        self.username = os.getenv('INSTAGRAM_USERNAME')
        self.password = os.getenv('INSTAGRAM_PASSWORD')
        self.session = requests.Session()
        self.csrf_token = None
        self.user_id = None
        self.driver = None
        # Initialize rate limiter with Threads-specific limits
        rate_limits = {
            'posts_per_hour': int(os.getenv('THREADS_POSTS_PER_HOUR', '5')),
            'posts_per_day': int(os.getenv('THREADS_POSTS_PER_DAY', '20')),
            'minimum_interval': int(os.getenv('THREADS_MIN_INTERVAL', '300')),
            'cooldown_period': 3600
        }
        self.rate_limiter = RateLimiter(rate_limits)

    def _setup_selenium(self):
        """Setup Selenium with configured options"""
        if not self.driver:
            options = webdriver.ChromeOptions()
            selenium_options = ThreadsConfig.get_selenium_options()
            
            # Add arguments
            for arg in selenium_options['arguments']:
                options.add_argument(arg)
            
            # Add experimental options
            for key, value in selenium_options['experimental_options'].items():
                options.add_experimental_option(key, value)
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(self.config['timeout'])

    def authenticate(self) -> bool:
        """Authenticate with Instagram/Threads"""
        try:
            if not self.username or not self.password:
                logger.warning("Instagram credentials not found")
                return False

            self._setup_selenium()
            
            # Add random delay to avoid detection
            time.sleep(random.uniform(2, 5))
            
            # Login to Instagram
            self.driver.get('https://www.instagram.com/accounts/login/')
            
            # Wait longer for elements to load
            wait = WebDriverWait(self.driver, 20)
            
            # Add delay before entering credentials
            time.sleep(random.uniform(1, 3))
            
            # Fill username
            username_input = wait.until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            # Type slowly like a human
            for char in self.username:
                username_input.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))
            
            # Fill password with delay
            password_input = self.driver.find_element(By.NAME, "password")
            for char in self.password:
                password_input.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))
            
            # Wait before clicking login
            time.sleep(random.uniform(1, 2))
            
            # Click login
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # Wait longer for successful login
            try:
                # Save login info popup might appear
                try:
                    not_now_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now')]"))
                    )
                    not_now_button.click()
                except:
                    pass
                
                # Wait for navigation element to confirm login
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "nav")))
                
                # Get cookies
                cookies = self.driver.get_cookies()
                for cookie in cookies:
                    self.session.cookies.set(cookie['name'], cookie['value'])
                
                self.is_authenticated = True
                logger.info("Successfully authenticated with Instagram/Threads")
                return True
                
            except Exception as e:
                logger.error(f"Login failed: {str(e)}")
                return False

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise ThreadsAuthenticationError(f"Failed to authenticate: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

    def _retry_operation(self, operation_func, *args, **kwargs):
        """Retry an operation with exponential backoff"""
        for attempt in range(self.config['max_retries']):
            try:
                return operation_func(*args, **kwargs)
            except (ThreadsAuthenticationError, ThreadsPostingError) as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.config['max_retries'] - 1:
                    time.sleep(self.config['retry_delay'] * (2 ** attempt))
                else:
                    raise

    def _validate_content(self, content: str) -> bool:
        """Validate content for Threads platform"""
        if not content or not content.strip():
            logger.warning("Empty content provided")
            return False
        
        # Check content length
        if len(content) > self.config['max_content_length']:
            logger.warning(f"Content exceeds maximum length of {self.config['max_content_length']} characters")
            return False
        
        # Check for banned words or phrases
        banned_words = ['spam', 'advertise', 'promotion']
        content_lower = content.lower()
        for word in banned_words:
            if word in content_lower:
                logger.warning(f"Content contains banned word: {word}")
                return False
            
        return True

    def _validate_media(self, media_path: str) -> bool:
        """Validate media file for posting"""
        if not os.path.exists(media_path):
            logger.warning(f"Media file not found: {media_path}")
            return False
            
        # Check file type
        mime_type, _ = mimetypes.guess_type(media_path)
        if mime_type not in self.config['content_rules']['allowed_media_types']:
            logger.warning(f"Unsupported media type: {mime_type}")
            return False
            
        # Check file size
        file_size = os.path.getsize(media_path)
        if file_size > self.config['content_rules']['max_media_size']:
            logger.warning(f"File size exceeds limit: {file_size} bytes")
            return False
            
        return True
        
    def _optimize_image(self, image_path: str) -> str:
        """Optimize image for Threads"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    
                # Resize if too large
                max_size = (1080, 1080)
                if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                    img.thumbnail(max_size, Image.LANCZOS)
                    
                # Save optimized version
                optimized_path = f"{os.path.splitext(image_path)[0]}_optimized.jpg"
                img.save(optimized_path, 'JPEG', quality=85, optimize=True)
                return optimized_path
                
        except Exception as e:
            logger.error(f"Error optimizing image: {str(e)}")
            return image_path

    def post_content(self, content: str, media_path: str = None, **kwargs) -> Dict[str, Any]:
        """Post content with optional media to Threads with rate limiting"""
        # Check rate limits before posting
        if not self.rate_limiter.can_post():
            raise ThreadsPostingError("Rate limit exceeded")
            
        if not self._validate_content(content):
            raise ThreadsPostingError("Content validation failed")
            
        # Handle media if provided
        if media_path:
            if not self._validate_media(media_path):
                raise ThreadsMediaError("Media validation failed")
            if media_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                media_path = self._optimize_image(media_path)

        try:
            result = self._retry_operation(self._do_post, content, media_path)
            if result['success']:
                # Record successful post for rate limiting
                self.rate_limiter.record_post()
                # Track metrics
                self._track_metrics(result)
            return result
        except Exception as e:
            logger.error(f"Error posting content: {str(e)}")
            raise

    def _do_post(self, content: str, media_path: str = None) -> Dict[str, Any]:
        """Internal method to perform the actual posting"""
        def _do_post():
            if not self.is_authenticated:
                if not self.authenticate():
                    raise ThreadsAuthenticationError("Authentication failed")

            formatted_content = self._format_content(content)
            
            try:
                self._setup_selenium()
                self.driver.get(self.config['threads_url'])
                wait = WebDriverWait(self.driver, self.config['timeout'])
                
                # Click create button
                create_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[aria-label='Create new thread']"))
                )
                create_button.click()
                
                # Add media if provided
                if media_path:
                    media_input = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
                    )
                    media_input.send_keys(os.path.abspath(media_path))
                    
                    # Wait for media upload
                    wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label='Media preview']"))
                    )
                
                # Add content
                content_area = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label='Post content']"))
                )
                content_area.send_keys(formatted_content)
                
                # Post
                post_button = self.driver.find_element(By.XPATH, "//button[text()='Post']")
                post_button.click()
                
                # Wait for completion
                time.sleep(2)
                
                return {
                    "success": True,
                    "message": "Content posted successfully to Threads",
                    "platform": "threads",
                    "has_media": bool(media_path)
                }
                
            except Exception as e:
                raise ThreadsPostingError(f"Failed to post content: {str(e)}")
            finally:
                if self.driver:
                    self.driver.quit()
                    self.driver = None

        return self._retry_operation(_do_post)

    def _format_content(self, content: str) -> str:
        """Format content for Threads platform"""
        # Clean and format content
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                formatted_lines.append(line)

        # Join with proper spacing
        formatted_content = '\n\n'.join(formatted_lines)

        # Ensure content length meets Threads requirements
        if len(formatted_content) > 500:
            formatted_content = formatted_content[:497] + "..."

        return formatted_content

    def check_status(self) -> bool:
        """Check Threads API status"""
        try:
            response = requests.get(f"https://www.threads.net/status")
            return response.status_code == 200
        except:
            return False

    def _track_metrics(self, post_data: Dict[str, Any]) -> None:
        """Track posting metrics"""
        try:
            metrics = {
                'timestamp': datetime.utcnow().isoformat(),
                'platform': 'threads',
                'content_length': len(post_data.get('content', '')),
                'status': 'success' if post_data.get('success') else 'failed',
                'error': post_data.get('error'),
                'retries': post_data.get('retries', 0)
            }
            
            # Log metrics
            logger.info(f"Post metrics: {json.dumps(metrics)}")
            
            # Could be extended to store metrics in database
            # self._db.store_metrics(metrics)
            
        except Exception as e:
            logger.error(f"Error tracking metrics: {str(e)}")

    def reply_to_thread(self, thread_url: str, content: str, media_path: str = None) -> Dict[str, Any]:
        """Reply to an existing thread"""
        if not self.rate_limiter.can_post():
            raise ThreadsPostingError("Rate limit exceeded")
        
        if not self._validate_content(content):
            raise ThreadsPostingError("Content validation failed")

        def _do_reply():
            if not self.is_authenticated:
                if not self.authenticate():
                    raise ThreadsAuthenticationError("Authentication failed")

            try:
                self._setup_selenium()
                self.driver.get(thread_url)
                wait = WebDriverWait(self.driver, self.config['timeout'])
                
                # Click reply button
                reply_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[aria-label='Reply']"))
                )
                reply_button.click()
                
                # Handle media if provided
                if media_path:
                    if not self._validate_media(media_path):
                        raise ThreadsMediaError("Media validation failed")
                    media_input = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
                    )
                    media_input.send_keys(os.path.abspath(media_path))
                    
                    # Wait for media upload
                    wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label='Media preview']"))
                    )
                
                # Add reply content
                content_area = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label='Post content']"))
                )
                content_area.send_keys(self._format_content(content))
                
                # Post reply
                post_button = self.driver.find_element(By.XPATH, "//button[text()='Reply']")
                post_button.click()
                
                # Wait for completion
                time.sleep(2)
                
                result = {
                    "success": True,
                    "message": "Reply posted successfully",
                    "platform": "threads",
                    "type": "reply",
                    "parent_url": thread_url,
                    "has_media": bool(media_path)
                }
                
                # Track metrics
                self._track_metrics(result)
                
                return result
                
            except Exception as e:
                raise ThreadsPostingError(f"Failed to post reply: {str(e)}")
            finally:
                if self.driver:
                    self.driver.quit()
                    self.driver = None

        return self._retry_operation(_do_reply) 