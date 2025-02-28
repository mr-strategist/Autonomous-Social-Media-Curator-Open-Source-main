from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from collections import defaultdict
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)

class PostingOptimizer:
    """Optimize posting schedule based on analytics"""
    
    def __init__(self, db_manager, analytics_manager):
        self.db = db_manager
        self.analytics = analytics_manager
        self.platform_limits = {
            'twitter': {
                'daily_limit': 5,
                'min_interval_hours': 2,
                'optimal_times': []
            },
            'linkedin': {
                'daily_limit': 3,
                'min_interval_hours': 4,
                'optimal_times': []
            }
        }

    async def get_optimal_posting_time(self, platform: str, content: Dict) -> datetime:
        """Calculate optimal posting time based on historical data"""
        try:
            # Get engagement patterns
            patterns = await self.analytics.analyze_engagement_patterns(platform)
            if not patterns['success']:
                raise ValueError("Failed to get engagement patterns")

            # Get peak hours
            peak_hours = patterns['patterns']['timing']['peak_hours']
            if not peak_hours:
                return datetime.utcnow() + timedelta(hours=1)  # Default fallback

            # Get recent posts
            recent_posts = await self.db.get_post_history(
                platform=platform,
                days=1
            )

            # Find next available peak time
            now = datetime.utcnow()
            best_time = now + timedelta(hours=1)  # Default fallback
            best_score = -1

            for peak in peak_hours:
                hour = int(peak['time_slot'].split(':')[0])
                candidate_time = now.replace(hour=hour, minute=0, second=0)
                
                # If time is in past, move to next day
                if candidate_time <= now:
                    candidate_time += timedelta(days=1)

                # Check if this time respects minimum intervals
                if self._respects_posting_intervals(candidate_time, recent_posts, platform):
                    # Calculate score based on engagement rate and content type
                    score = self._calculate_time_score(
                        candidate_time,
                        peak['avg_engagement'],
                        content,
                        patterns['patterns']
                    )
                    
                    if score > best_score:
                        best_score = score
                        best_time = candidate_time

            return best_time

        except Exception as e:
            logger.error(f"Error getting optimal posting time: {str(e)}")
            return datetime.utcnow() + timedelta(hours=1)  # Safe fallback

    async def generate_posting_schedule(self, content_queue: List[Dict]) -> List[Dict]:
        """Generate optimized posting schedule"""
        try:
            schedule = []
            platform_schedules = defaultdict(list)

            # Sort content by priority/importance
            sorted_content = sorted(
                content_queue,
                key=lambda x: x.get('priority', 0),
                reverse=True
            )

            for content in sorted_content:
                platform = content['platform'].lower()
                
                # Get optimal time for this content
                optimal_time = await self.get_optimal_posting_time(platform, content)
                
                # Adjust time if too close to other posts
                while not self._is_time_available(optimal_time, platform_schedules[platform]):
                    optimal_time += timedelta(hours=1)

                # Add to schedule
                schedule_entry = {
                    'content_id': content.get('id'),
                    'platform': platform,
                    'scheduled_time': optimal_time.isoformat(),
                    'content': content,
                    'metadata': {
                        'optimization_factors': {
                            'engagement_prediction': await self._predict_engagement(content),
                            'time_score': self._calculate_time_score(
                                optimal_time,
                                1.0,  # Default engagement score
                                content,
                                {}  # Empty patterns as fallback
                            )
                        }
                    }
                }
                
                schedule.append(schedule_entry)
                platform_schedules[platform].append(schedule_entry)

            # Sort final schedule by time
            schedule.sort(key=lambda x: x['scheduled_time'])

            return {
                'success': True,
                'schedule': schedule,
                'metadata': {
                    'total_posts': len(schedule),
                    'platforms': list(platform_schedules.keys()),
                    'generated_at': datetime.utcnow().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Error generating posting schedule: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _respects_posting_intervals(self, candidate_time: datetime, 
                                  recent_posts: List[Dict],
                                  platform: str) -> bool:
        """Check if candidate time respects minimum intervals"""
        min_interval = timedelta(hours=self.platform_limits[platform]['min_interval_hours'])
        
        for post in recent_posts:
            if not post.get('posted_at'):
                continue
                
            post_time = datetime.fromisoformat(post['posted_at'])
            time_diff = abs(candidate_time - post_time)
            
            if time_diff < min_interval:
                return False
                
        return True

    def _is_time_available(self, time: datetime, scheduled_posts: List[Dict]) -> bool:
        """Check if time slot is available"""
        for post in scheduled_posts:
            scheduled_time = datetime.fromisoformat(post['scheduled_time'])
            time_diff = abs(time - scheduled_time).total_seconds() / 3600
            
            if time_diff < 1:  # Less than 1 hour difference
                return False
        
        return True

    async def _predict_engagement(self, content: Dict) -> float:
        """Predict potential engagement for content"""
        try:
            # Get historical performance for similar content
            similar_posts = await self._find_similar_posts(content)
            
            if not similar_posts:
                return 0.5  # Default score if no similar posts
            
            # Calculate average engagement rate
            engagement_rates = [
                post.get('metrics', {}).get('engagement_rate', 0)
                for post in similar_posts
            ]
            
            return sum(engagement_rates) / len(engagement_rates)
            
        except Exception as e:
            logger.error(f"Error predicting engagement: {str(e)}")
            return 0.5  # Default fallback score

    async def _find_similar_posts(self, content: Dict) -> List[Dict]:
        """Find similar historical posts"""
        try:
            # Get recent posts
            posts = await self.db.get_post_history(
                platform=content['platform'],
                days=30
            )
            
            similar_posts = []
            content_text = content.get('text', '').lower()
            
            for post in posts:
                post_text = post.get('content', '').lower()
                
                # Calculate similarity score
                similarity = self._calculate_text_similarity(content_text, post_text)
                
                if similarity > 0.3:  # Arbitrary threshold
                    similar_posts.append(post)
            
            return similar_posts
            
        except Exception as e:
            logger.error(f"Error finding similar posts: {str(e)}")
            return []

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        try:
            # Simple word overlap similarity
            words1 = set(text1.split())
            words2 = set(text2.split())
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            return len(intersection) / len(union) if union else 0
            
        except Exception as e:
            logger.error(f"Error calculating text similarity: {str(e)}")
            return 0

    def _calculate_time_score(self, time: datetime, base_engagement: float,
                            content: Dict, patterns: Dict) -> float:
        """Calculate score for a potential posting time"""
        try:
            score = base_engagement
            
            # Adjust for day of week
            day_name = time.strftime('%A')
            if patterns.get('timing', {}).get('daily_stats', {}).get(day_name):
                day_stats = patterns['timing']['daily_stats'][day_name]
                score *= (day_stats['mean'] / day_stats['max'])
            
            # Adjust for content type
            content_type = self._determine_content_type(content)
            if patterns.get('content', {}).get(content_type):
                type_stats = patterns['content'][content_type]
                score *= type_stats['success_rate']
            
            # Penalty for non-business hours (if B2B content)
            hour = time.hour
            if content.get('audience') == 'b2b' and (hour < 9 or hour > 17):
                score *= 0.7
            
            return score
            
        except Exception as e:
            logger.error(f"Error calculating time score: {str(e)}")
            return base_engagement  # Return base score as fallback

    def _determine_content_type(self, content: Dict) -> str:
        """Determine content type"""
        text = content.get('text', '')
        
        if any(url_pattern in text.lower() for url_pattern in ['http://', 'https://', 'www.']):
            return 'link'
        elif '#' in text:
            return 'hashtag'
        elif '@' in text:
            return 'mention'
        elif len(text) > 280:
            return 'long_form'
        else:
            return 'text' 