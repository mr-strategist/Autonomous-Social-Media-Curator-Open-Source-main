from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging
from collections import deque

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter for social media platforms"""
    
    def __init__(self, limits: Dict[str, int]):
        self.limits = limits
        self.post_history: deque = deque(maxlen=1000)  # Store last 1000 posts
        self.hourly_posts = 0
        self.daily_posts = 0
        self.last_reset = datetime.utcnow()
        
    def can_post(self) -> bool:
        """Check if posting is allowed based on rate limits"""
        now = datetime.utcnow()
        self._update_counters(now)
        
        # Check minimum interval between posts
        if self.post_history and (now - self.post_history[-1]).total_seconds() < self.limits['minimum_interval']:
            logger.warning("Minimum interval between posts not met")
            return False
            
        # Check hourly limit
        if self.hourly_posts >= self.limits['posts_per_hour']:
            logger.warning("Hourly post limit reached")
            return False
            
        # Check daily limit
        if self.daily_posts >= self.limits['posts_per_day']:
            logger.warning("Daily post limit reached")
            return False
            
        return True
        
    def record_post(self):
        """Record a new post"""
        now = datetime.utcnow()
        self.post_history.append(now)
        self.hourly_posts += 1
        self.daily_posts += 1
        
    def _update_counters(self, current_time: datetime):
        """Update post counters based on time passed"""
        # Reset hourly counter if an hour has passed
        if (current_time - self.last_reset).total_seconds() >= 3600:
            self.hourly_posts = 0
            
        # Reset daily counter if a day has passed
        if (current_time - self.last_reset).total_seconds() >= 86400:
            self.daily_posts = 0
            self.last_reset = current_time
            
        # Clean up old posts from history
        one_day_ago = current_time - timedelta(days=1)
        while self.post_history and self.post_history[0] < one_day_ago:
            self.post_history.popleft() 