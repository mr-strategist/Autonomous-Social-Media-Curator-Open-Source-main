import os
import requests
import json
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from .base import SocialMediaPlatform
from ..config.platforms import Platform
from ..utils.rate_limiter import RateLimiter

# Configure logging
logger = logging.getLogger('threads_api')

class ThreadsAPIError(Exception):
    """Base exception for Threads API errors"""
    pass

class ThreadsAPIAuthError(ThreadsAPIError):
    """Authentication error with Threads API"""
    pass

class ThreadsAPIPostError(ThreadsAPIError):
    """Error posting content via Threads API"""
    pass

class ThreadsAPI(SocialMediaPlatform):
    """Implementation of Threads platform using the official API"""
    
    BASE_URL = "https://graph.threads.net/v1"
    
    def __init__(self):
        super().__init__(Platform.THREADS)
        # Get credentials from environment
        self.client_id = os.getenv('THREADS_CLIENT_ID')
        self.client_secret = os.getenv('THREADS_CLIENT_SECRET')
        self.redirect_uri = os.getenv('THREADS_REDIRECT_URI')
        self.access_token = os.getenv('THREADS_ACCESS_TOKEN')
        self.refresh_token = os.getenv('THREADS_REFRESH_TOKEN')
        self.token_expiry = os.getenv('THREADS_TOKEN_EXPIRY')
        
        # Initialize rate limiter
        rate_limits = {
            'posts_per_hour': int(os.getenv('THREADS_POSTS_PER_HOUR', '5')),
            'posts_per_day': int(os.getenv('THREADS_POSTS_PER_DAY', '20')),
            'minimum_interval': int(os.getenv('THREADS_MIN_INTERVAL', '300')),
            'cooldown_period': 3600
        }
        self.rate_limiter = RateLimiter(rate_limits)
        
        # Check if we have a valid token
        if self.access_token:
            self.is_authenticated = True
        
    def authenticate(self) -> bool:
        """Authenticate with Threads API using OAuth flow"""
        try:
            # If we already have a valid token, use it
            if self.access_token and self.token_expiry and float(self.token_expiry) > time.time():
                logger.info("Using existing access token")
                self.is_authenticated = True
                return True
                
            # If we have a refresh token, try to refresh
            if self.refresh_token:
                logger.info("Refreshing access token")
                return self._refresh_token()
                
            # Otherwise, we need to start the OAuth flow
            logger.warning("No valid tokens found. Manual OAuth flow required.")
            logger.info(f"Please visit: https://www.threads.net/oauth/authorize?client_id={self.client_id}&redirect_uri={self.redirect_uri}&scope=threads_basic,threads_media")
            
            # In a web app, you'd redirect the user to the auth URL
            # For a CLI app, you'd need to manually get the code
            auth_code = input("Enter the authorization code from the redirect URL: ")
            
            # Exchange code for tokens
            token_data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'authorization_code',
                'code': auth_code,
                'redirect_uri': self.redirect_uri
            }
            
            response = requests.post(
                "https://graph.threads.net/oauth/access_token", 
                data=token_data
            )
            
            if response.status_code == 200:
                token_info = response.json()
                self._save_tokens(token_info)
                self.is_authenticated = True
                return True
            else:
                logger.error(f"Failed to get access token: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise ThreadsAPIAuthError(f"Failed to authenticate: {str(e)}")
    
    def _refresh_token(self) -> bool:
        """Refresh the access token using the refresh token"""
        try:
            refresh_data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token
            }
            
            response = requests.post(
                "https://graph.threads.net/oauth/access_token", 
                data=refresh_data
            )
            
            if response.status_code == 200:
                token_info = response.json()
                self._save_tokens(token_info)
                return True
            else:
                logger.error(f"Failed to refresh token: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            return False
    
    def _save_tokens(self, token_info: Dict[str, Any]) -> None:
        """Save tokens to environment and instance variables"""
        self.access_token = token_info.get('access_token')
        self.refresh_token = token_info.get('refresh_token')
        expires_in = token_info.get('expires_in', 3600)
        self.token_expiry = str(time.time() + expires_in)
        
        # In a real app, you'd save these securely
        # For now, we'll just log that we got them
        logger.info("Tokens received and saved")
        
        # You could also save to .env file or secure storage
        # with open('.env', 'a') as f:
        #     f.write(f"\nTHREADS_ACCESS_TOKEN={self.access_token}")
        #     f.write(f"\nTHREADS_REFRESH_TOKEN={self.refresh_token}")
        #     f.write(f"\nTHREADS_TOKEN_EXPIRY={self.token_expiry}")
    
    def post_content(self, content: str, media_paths: List[str] = None, **kwargs) -> Dict[str, Any]:
        """Post content to Threads using the official API"""
        # Check rate limits
        if not self.rate_limiter.can_post():
            raise ThreadsAPIPostError("Rate limit exceeded")
            
        # Ensure we're authenticated
        if not self.is_authenticated and not self.authenticate():
            raise ThreadsAPIAuthError("Authentication failed")
            
        try:
            # Format content for Threads
            formatted_content = self._format_content(content)
            
            # Prepare the API request
            post_url = f"{self.BASE_URL}/me/posts"
            post_data = {
                'message': formatted_content,
                'access_token': self.access_token
            }
            
            # Handle media if provided
            if media_paths and len(media_paths) > 0:
                media_ids = self._upload_media(media_paths)
                if media_ids:
                    if len(media_ids) == 1:
                        # Single media post
                        post_data['media_id'] = media_ids[0]
                    else:
                        # Carousel post
                        post_data['carousel_media_ids'] = ','.join(media_ids)
            
            # Make the API request
            response = requests.post(post_url, data=post_data)
            
            if response.status_code == 200:
                result = response.json()
                post_id = result.get('id')
                
                # Record successful post for rate limiting
                self.rate_limiter.record_post()
                
                # Return success response
                success_data = {
                    "success": True,
                    "message": "Content posted successfully to Threads",
                    "platform": "threads",
                    "post_id": post_id,
                    "has_media": bool(media_paths),
                    "media_count": len(media_paths) if media_paths else 0
                }
                
                # Track metrics
                self._track_metrics(success_data)
                
                return success_data
            else:
                error_msg = f"API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "platform": "threads"
                }
                
        except Exception as e:
            logger.error(f"Error posting content: {str(e)}")
            raise ThreadsAPIPostError(f"Failed to post content: {str(e)}")
    
    def _upload_media(self, media_paths: List[str]) -> List[str]:
        """Upload media files and return media IDs"""
        media_ids = []
        
        for media_path in media_paths:
            if not os.path.exists(media_path):
                logger.warning(f"Media file not found: {media_path}")
                continue
                
            try:
                # Upload media endpoint
                upload_url = f"{self.BASE_URL}/me/media"
                
                # Prepare file upload
                with open(media_path, 'rb') as media_file:
                    files = {'file': media_file}
                    data = {'access_token': self.access_token}
                    
                    # For video, you might need to add type parameter
                    if media_path.lower().endswith(('.mp4', '.mov')):
                        data['type'] = 'VIDEO'
                    
                    # Upload the media
                    response = requests.post(upload_url, data=data, files=files)
                    
                if response.status_code == 200:
                    result = response.json()
                    media_id = result.get('id')
                    if media_id:
                        media_ids.append(media_id)
                        logger.info(f"Media uploaded successfully: {media_id}")
                    else:
                        logger.warning(f"No media ID in response: {result}")
                else:
                    logger.error(f"Media upload failed: {response.status_code} - {response.text}")
                    
            except Exception as e:
                logger.error(f"Error uploading media {media_path}: {str(e)}")
                
        return media_ids
    
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
    
    def reply_to_thread(self, thread_id: str, content: str, media_paths: List[str] = None) -> Dict[str, Any]:
        """Reply to an existing thread"""
        # Check rate limits
        if not self.rate_limiter.can_post():
            raise ThreadsAPIPostError("Rate limit exceeded")
            
        # Ensure we're authenticated
        if not self.is_authenticated and not self.authenticate():
            raise ThreadsAPIAuthError("Authentication failed")
            
        try:
            # Format content for Threads
            formatted_content = self._format_content(content)
            
            # Prepare the API request
            reply_url = f"{self.BASE_URL}/{thread_id}/replies"
            reply_data = {
                'message': formatted_content,
                'access_token': self.access_token
            }
            
            # Handle media if provided
            if media_paths and len(media_paths) > 0:
                media_ids = self._upload_media(media_paths)
                if media_ids:
                    if len(media_ids) == 1:
                        # Single media post
                        reply_data['media_id'] = media_ids[0]
                    else:
                        # Carousel post
                        reply_data['carousel_media_ids'] = ','.join(media_ids)
            
            # Make the API request
            response = requests.post(reply_url, data=reply_data)
            
            if response.status_code == 200:
                result = response.json()
                reply_id = result.get('id')
                
                # Record successful post for rate limiting
                self.rate_limiter.record_post()
                
                # Return success response
                success_data = {
                    "success": True,
                    "message": "Reply posted successfully",
                    "platform": "threads",
                    "type": "reply",
                    "reply_id": reply_id,
                    "parent_id": thread_id,
                    "has_media": bool(media_paths),
                    "media_count": len(media_paths) if media_paths else 0
                }
                
                # Track metrics
                self._track_metrics(success_data)
                
                return success_data
            else:
                error_msg = f"API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "platform": "threads",
                    "type": "reply"
                }
                
        except Exception as e:
            logger.error(f"Error posting reply: {str(e)}")
            raise ThreadsAPIPostError(f"Failed to post reply: {str(e)}")
    
    def get_profile(self) -> Dict[str, Any]:
        """Get the authenticated user's profile information"""
        if not self.is_authenticated and not self.authenticate():
            raise ThreadsAPIAuthError("Authentication failed")
            
        try:
            profile_url = f"{self.BASE_URL}/me"
            params = {'access_token': self.access_token}
            
            response = requests.get(profile_url, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get profile: {response.status_code} - {response.text}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logger.error(f"Error getting profile: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def check_status(self) -> bool:
        """Check if the Threads API is available"""
        try:
            response = requests.get(f"{self.BASE_URL}/status")
            return response.status_code == 200
        except:
            return False
    
    def _track_metrics(self, post_data: Dict[str, Any]) -> None:
        """Track posting metrics"""
        try:
            metrics = {
                'timestamp': datetime.utcnow().isoformat(),
                'platform': 'threads',
                'content_length': len(post_data.get('message', '')),
                'status': 'success' if post_data.get('success') else 'failed',
                'error': post_data.get('error'),
                'has_media': post_data.get('has_media', False),
                'media_count': post_data.get('media_count', 0),
                'post_type': post_data.get('type', 'post')
            }
            
            # Log metrics
            logger.info(f"Post metrics: {json.dumps(metrics)}")
            
        except Exception as e:
            logger.error(f"Error tracking metrics: {str(e)}") 