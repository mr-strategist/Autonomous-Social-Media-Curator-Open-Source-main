import os
import logging
from typing import Dict, List, Any
from crewai.tools import BaseTool
from ..platforms.manager import PlatformManager
from ..config.platforms import Platform

logger = logging.getLogger(__name__)

class PlatformSelector:
    """Interactive platform selection for content posting"""
    
    def __init__(self):
        self.platform_manager = PlatformManager()
        
    def show_platform_menu(self) -> Dict[str, Any]:
        """Display available platforms and get user selection"""
        platforms = {}
        connected_accounts = []
        
        # Get authentication status for all platforms
        auth_status = self.platform_manager.authenticate_all()
        
        print("\n=== Available Platforms ===")
        index = 1
        
        for platform, is_authenticated in auth_status.items():
            account_info = self._get_account_info(platform)
            if is_authenticated:
                platforms[str(index)] = platform
                status = "✅ Connected"
                username = f"(@{account_info['username']})" if account_info.get('username') else ""
                connected_accounts.append(f"{index}. {platform.value} {username} {status}")
                index += 1
        
        # Add "All Platforms" option
        platforms['all'] = 'all'
        connected_accounts.append(f"{index}. Post to All Platforms")
        
        # Display platforms
        print("\n".join(connected_accounts))
        print("\nEnter the number(s) of platforms to post to (comma-separated) or 'all':")
        
        while True:
            try:
                choice = input().strip().lower()
                if choice == 'all':
                    return {'platforms': list(Platform)}
                
                selected_indices = [p.strip() for p in choice.split(',')]
                selected_platforms = []
                
                for idx in selected_indices:
                    if idx in platforms:
                        if platforms[idx] != 'all':
                            selected_platforms.append(platforms[idx])
                        else:
                            return {'platforms': list(Platform)}
                
                if selected_platforms:
                    return {'platforms': selected_platforms}
                
                print("Invalid selection. Please try again.")
            
            except Exception as e:
                logger.error(f"Error in platform selection: {str(e)}")
                print("Invalid input. Please try again.")

    def _get_account_info(self, platform: Platform) -> Dict[str, str]:
        """Get account information for a platform"""
        try:
            if platform == Platform.DEVTO:
                return {"username": os.getenv('DEVTO_USERNAME', 'Dev.to Account')}
            elif platform == Platform.MASTODON:
                return {"username": os.getenv('MASTODON_USERNAME', 'Mastodon Account')}
            elif platform == Platform.THREADS:
                return {"username": os.getenv('INSTAGRAM_USERNAME', 'Threads Account')}
            return {"username": "Unknown"}
        except:
            return {"username": "Unknown"} 