import os
import requests
from typing import Dict, Any
from .base import SocialMediaPlatform
from ..config.platforms import Platform

class DevTo(SocialMediaPlatform):
    """Dev.to platform implementation"""
    
    def __init__(self):
        super().__init__(Platform.DEVTO)
        self.api_key = os.getenv('DEVTO_API_KEY')
        self.base_url = "https://dev.to/api"
        
    def authenticate(self) -> bool:
        """Verify Dev.to API key"""
        try:
            if not self.api_key:
                print("Dev.to API key is missing")
                return False
            
            headers = {'api-key': self.api_key}
            response = requests.get(f"{self.base_url}/articles/me", headers=headers)
            
            if response.status_code == 200:
                print("Dev.to authentication successful")
                self.is_authenticated = True
                return True
            
            print(f"Dev.to authentication failed: {response.status_code} - {response.text}")
            self.is_authenticated = False
            return False
        except Exception as e:
            print(f"Dev.to authentication error: {str(e)}")
            self.is_authenticated = False
            return False

    def post_content(self, content: str, **kwargs) -> Dict[str, Any]:
        """Post article to Dev.to"""
        try:
            if not self.is_authenticated:
                if not self.authenticate():
                    return {"success": False, "error": "Authentication failed"}

            title = kwargs.get('title')
            if not title:
                return {"success": False, "error": "Title is required for Dev.to posts"}

            # Ensure content is properly formatted
            article = {
                "article": {
                    "title": title,
                    "body_markdown": content,
                    "published": True,
                    "tags": kwargs.get('tags', ['technology']),  # Default tag
                }
            }

            print(f"Posting to Dev.to with title: {title}")
            headers = {
                'api-key': self.api_key,
                'Content-Type': 'application/json'
            }
            
            # Add debug logging
            print(f"Dev.to API Request URL: {self.base_url}/articles")
            print(f"Request Headers: {headers}")
            print(f"Request Body: {article}")
            
            response = requests.post(
                f"{self.base_url}/articles",
                json=article,
                headers=headers
            )

            print(f"Dev.to API Response Status: {response.status_code}")
            print(f"Dev.to API Response Body: {response.text}")

            if response.status_code in [201, 200]:
                result = response.json()
                url = result.get('url', '')
                return {
                    "success": True,
                    "data": result,
                    "url": url
                }
            
            error_msg = f"Dev.to API Error: {response.status_code} - {response.text}"
            print(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Dev.to posting error: {str(e)}"
            print(error_msg)
            return {
                "success": False,
                "error": error_msg
            }

    def check_status(self) -> bool:
        """Check Dev.to API status"""
        try:
            response = requests.get(f"{self.base_url}/articles")
            return response.status_code == 200
        except:
            return False 