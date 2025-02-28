import logging
from typing import Dict, Any, List
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from ..platforms.manager import PlatformManager
from ..config.platforms import Platform
from .platform_selector import PlatformSelector
import time

logger = logging.getLogger(__name__)

class PostContentSchema(BaseModel):
    content: str = Field(..., description="Content to post")
    platforms: List[str] = Field(
        default=["all"],
        description="List of platforms to post to (dev.to, mastodon, threads, or 'all')"
    )
    title: str = Field(
        default=None,
        description="Title for the post (required for Dev.to)"
    )
    tags: List[str] = Field(
        default=[],
        description="Tags for the post"
    )

class ContentPostingTool(BaseTool):
    name: str = "Content Posting Tool"
    description: str = "Create content and post to selected social media platforms"
    args_schema: type[BaseModel] = PostContentSchema
    
    def __init__(self):
        super().__init__()
        self.platform_manager = PlatformManager()
        self.platform_selector = PlatformSelector()
        self.max_retries = 3

    def _post_with_retry(self, platform: Platform, content: str, **kwargs) -> Dict[str, Any]:
        """Post content with retry logic"""
        for attempt in range(self.max_retries):
            try:
                result = self.platform_manager.post_to_platform(
                    platform=platform,
                    content=content,
                    **kwargs
                )
                if result.get("success"):
                    return result
                
                logger.warning(f"Attempt {attempt + 1} failed for {platform.value}: {result.get('error')}")
            except Exception as e:
                logger.error(f"Error posting to {platform.value}: {str(e)}")
            
            if attempt < self.max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return {
            "success": False,
            "error": f"Failed to post to {platform.value} after {self.max_retries} attempts"
        }

    def _run(
        self, 
        content: str,
        platforms: List[str] = ["all"],
        title: str = None,
        tags: List[str] = []
    ) -> Dict[str, Any]:
        """Create and post content"""
        try:
            logger.info("Starting content posting process...")
            
            # Show content for review
            print("\n=== Content Review ===")
            print(content)
            print("\nWould you like to post this content? (yes/no):")
            
            user_input = input().strip().lower()
            logger.info(f"User input for content approval: {user_input}")
            
            if user_input != 'yes':
                return {
                    "success": False,
                    "message": "Content posting cancelled by user"
                }

            # Get platform selection
            logger.info("Showing platform selection menu...")
            selection = self.platform_selector.show_platform_menu()
            
            if not selection or 'platforms' not in selection:
                logger.warning("No platforms selected")
                return {
                    "success": False,
                    "message": "No platforms selected"
                }

            selected_platforms = selection['platforms']
            logger.info(f"Selected platforms: {[p.value for p in selected_platforms]}")
            
            results = {}

            # Post to each selected platform
            for platform in selected_platforms:
                logger.info(f"Preparing to post to {platform.value}...")
                
                # Get platform-specific requirements
                if platform == Platform.DEVTO:
                    if not title:
                        print("\nEnter a title for your Dev.to post:")
                        title = input().strip()
                        logger.info(f"Title input for Dev.to: {title}")
                        
                        if not title:
                            logger.warning("No title provided for Dev.to post")
                            print("Title is required for Dev.to posts. Skipping...")
                            continue
                    
                    print("\nEnter tags for your Dev.to post (comma-separated):")
                    input_tags = input().strip()
                    if input_tags:
                        tags = [tag.strip() for tag in input_tags.split(',')]
                        logger.info(f"Tags for Dev.to: {tags}")

                # Post with retry logic
                result = self._post_with_retry(
                    platform=platform,
                    content=content,
                    title=title,
                    tags=tags
                )
                
                results[platform.value] = result
                status = "✅ Success" if result['success'] else f"❌ Failed: {result.get('error', 'Unknown error')}"
                logger.info(f"Posting result for {platform.value}: {status}")
                print(f"\nResult for {platform.value}: {status}")
                if result.get('url'):
                    print(f"Post URL: {result['url']}")

            return {
                "success": True,
                "results": results,
                "message": "Content posting completed"
            }

        except Exception as e:
            logger.error(f"Error in content posting tool: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _arun(self, query: str) -> str:
        raise NotImplementedError("Async not supported") 