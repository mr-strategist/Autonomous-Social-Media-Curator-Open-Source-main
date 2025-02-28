from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from collections import defaultdict
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)

class EngagementAnalyzer:
    """Analyze post engagement patterns"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        
    async def analyze_engagement_patterns(self, platform: Optional[str] = None, 
                                        days: int = 30) -> Dict:
        """
        Analyze engagement patterns across posts
        
        Args:
            platform: Optional platform filter
            days: Number of days to analyze
        """
        try:
            posts = await self.db.get_post_history(platform=platform, days=days)
            
            # Initialize analysis containers
            hourly_engagement = defaultdict(list)
            daily_engagement = defaultdict(list)
            content_engagement = defaultdict(list)
            
            for post in posts:
                if not post.get('metrics'):
                    continue
                    
                posted_at = datetime.fromisoformat(post['posted_at'])
                metrics = post['metrics']
                
                # Track hourly patterns
                hour = posted_at.strftime('%H:00')
                hourly_engagement[hour].append(metrics.get('engagement_rate', 0))
                
                # Track daily patterns
                day = posted_at.strftime('%A')
                daily_engagement[day].append(metrics.get('engagement_rate', 0))
                
                # Track content type patterns
                content_type = self._classify_content(post['content'])
                content_engagement[content_type].append(metrics.get('engagement_rate', 0))
            
            # Calculate peak engagement times
            peak_hours = self._calculate_peak_times(hourly_engagement)
            peak_days = self._calculate_peak_times(daily_engagement)
            
            # Analyze content performance
            content_performance = self._analyze_content_performance(content_engagement)
            
            # Calculate engagement velocity
            velocity_patterns = await self._calculate_engagement_velocity(posts)
            
            return {
                'success': True,
                'patterns': {
                    'timing': {
                        'peak_hours': peak_hours,
                        'peak_days': peak_days,
                        'hourly_stats': self._calculate_stats(hourly_engagement),
                        'daily_stats': self._calculate_stats(daily_engagement)
                    },
                    'content': content_performance,
                    'velocity': velocity_patterns
                },
                'metadata': {
                    'platform': platform,
                    'days_analyzed': days,
                    'total_posts': len(posts),
                    'analyzed_at': datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing engagement patterns: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _classify_content(self, content: str) -> str:
        """Classify content type"""
        if any(url_pattern in content.lower() for url_pattern in ['http://', 'https://', 'www.']):
            return 'link'
        elif '#' in content:
            return 'hashtag'
        elif '@' in content:
            return 'mention'
        elif len(content) > 280:
            return 'long_form'
        else:
            return 'text'

    def _calculate_peak_times(self, time_engagement: Dict) -> List[Dict]:
        """Calculate peak engagement times"""
        peak_times = []
        
        for time_slot, rates in time_engagement.items():
            if not rates:
                continue
                
            avg_rate = sum(rates) / len(rates)
            confidence = stats.sem(rates) if len(rates) > 1 else 0
            
            peak_times.append({
                'time_slot': time_slot,
                'avg_engagement': avg_rate,
                'confidence': confidence,
                'sample_size': len(rates)
            })
        
        # Sort by average engagement
        peak_times.sort(key=lambda x: x['avg_engagement'], reverse=True)
        return peak_times[:3]  # Return top 3 peak times

    def _calculate_stats(self, engagement_data: Dict) -> Dict:
        """Calculate statistical metrics for engagement data"""
        stats_data = {}
        
        for time_slot, rates in engagement_data.items():
            if not rates:
                continue
                
            stats_data[time_slot] = {
                'mean': np.mean(rates),
                'median': np.median(rates),
                'std': np.std(rates) if len(rates) > 1 else 0,
                'min': min(rates),
                'max': max(rates),
                'count': len(rates)
            }
        
        return stats_data

    def _analyze_content_performance(self, content_engagement: Dict) -> Dict:
        """Analyze performance by content type"""
        performance = {}
        
        for content_type, rates in content_engagement.items():
            if not rates:
                continue
                
            performance[content_type] = {
                'avg_engagement': sum(rates) / len(rates),
                'total_posts': len(rates),
                'success_rate': len([r for r in rates if r > 0]) / len(rates),
                'stats': {
                    'mean': np.mean(rates),
                    'median': np.median(rates),
                    'std': np.std(rates) if len(rates) > 1 else 0
                }
            }
        
        return performance

    async def _calculate_engagement_velocity(self, posts: List[Dict]) -> Dict:
        """Calculate engagement velocity patterns"""
        velocity_data = defaultdict(list)
        
        for post in posts:
            if not post.get('metrics') or not post.get('posted_at'):
                continue
                
            posted_at = datetime.fromisoformat(post['posted_at'])
            age_hours = (datetime.utcnow() - posted_at).total_seconds() / 3600
            
            if age_hours <= 0:
                continue
                
            metrics = post['metrics']
            total_engagement = sum([
                metrics.get('likes', 0),
                metrics.get('comments', 0),
                metrics.get('shares', 0)
            ])
            
            velocity = total_engagement / age_hours
            
            # Group by age brackets
            if age_hours <= 1:
                velocity_data['first_hour'].append(velocity)
            elif age_hours <= 24:
                velocity_data['first_day'].append(velocity)
            else:
                velocity_data['after_day'].append(velocity)
        
        # Calculate average velocities
        velocity_patterns = {}
        for timeframe, velocities in velocity_data.items():
            if velocities:
                velocity_patterns[timeframe] = {
                    'avg_velocity': sum(velocities) / len(velocities),
                    'max_velocity': max(velocities),
                    'sample_size': len(velocities)
                }
        
        return velocity_patterns

    async def generate_performance_report(self, platform: Optional[str] = None,
                                        days: int = 30) -> Dict:
        """Generate comprehensive performance report"""
        try:
            # Get engagement patterns
            patterns = await self.analyze_engagement_patterns(platform, days)
            if not patterns['success']:
                raise ValueError(patterns['error'])
            
            # Get post history
            posts = await self.db.get_post_history(platform=platform, days=days)
            
            # Calculate overall metrics
            total_engagement = 0
            total_views = 0
            engagement_rates = []
            
            for post in posts:
                if not post.get('metrics'):
                    continue
                    
                metrics = post['metrics']
                total_engagement += sum([
                    metrics.get('likes', 0),
                    metrics.get('comments', 0),
                    metrics.get('shares', 0)
                ])
                total_views += metrics.get('views', 0)
                
                if metrics.get('engagement_rate'):
                    engagement_rates.append(metrics['engagement_rate'])
            
            # Generate report
            report = {
                'success': True,
                'overview': {
                    'total_posts': len(posts),
                    'total_engagement': total_engagement,
                    'total_views': total_views,
                    'avg_engagement_rate': sum(engagement_rates) / len(engagement_rates) if engagement_rates else 0
                },
                'patterns': patterns['patterns'],
                'recommendations': self._generate_recommendations(patterns['patterns']),
                'metadata': {
                    'platform': platform,
                    'days_analyzed': days,
                    'generated_at': datetime.utcnow().isoformat()
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating performance report: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _generate_recommendations(self, patterns: Dict) -> List[Dict]:
        """Generate actionable recommendations based on patterns"""
        recommendations = []
        
        # Timing recommendations
        if patterns.get('timing', {}).get('peak_hours'):
            peak_hours = patterns['timing']['peak_hours']
            recommendations.append({
                'category': 'timing',
                'title': 'Optimal Posting Times',
                'description': f"Schedule posts during peak engagement hours: {', '.join([p['time_slot'] for p in peak_hours])}",
                'confidence': sum([p['confidence'] for p in peak_hours]) / len(peak_hours)
            })
        
        # Content recommendations
        content_perf = patterns.get('content', {})
        if content_perf:
            best_type = max(content_perf.items(), key=lambda x: x[1]['avg_engagement'])
            recommendations.append({
                'category': 'content',
                'title': 'Content Type Optimization',
                'description': f"Focus on creating {best_type[0]} content, which shows highest engagement",
                'confidence': best_type[1]['success_rate']
            })
        
        # Velocity recommendations
        velocity = patterns.get('velocity', {})
        if velocity.get('first_hour'):
            recommendations.append({
                'category': 'engagement',
                'title': 'Engagement Window',
                'description': "Monitor and engage with posts actively in the first hour when velocity is highest",
                'confidence': 0.8
            })
        
        return recommendations 