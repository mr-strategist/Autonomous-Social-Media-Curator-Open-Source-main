import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.sql import func
from ..database.models import PostHistory, ContentMetrics, ContentSource
import re

logger = logging.getLogger(__name__)

class PerformanceTracker:
    """Track and analyze content performance metrics"""
    
    def __init__(self, db_manager):
        """
        Initialize performance tracker
        
        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        self.metric_weights = {
            'likes': 1.0,
            'comments': 2.0,
            'shares': 3.0,
            'clicks': 1.5,
            'views': 0.5
        }

    async def track_post_metrics(self, post_id: int, platform_metrics: Dict) -> bool:
        """
        Update metrics for a specific post
        
        Args:
            post_id: ID of the post
            platform_metrics: Raw metrics from the platform
        """
        try:
            # Calculate derived metrics
            engagement_rate = self._calculate_engagement_rate(platform_metrics)
            performance_score = self._calculate_performance_score(platform_metrics)
            
            # Update database
            metrics_data = {
                'likes': platform_metrics.get('likes', 0),
                'comments': platform_metrics.get('comments', 0),
                'shares': platform_metrics.get('shares', 0),
                'views': platform_metrics.get('views', 0),
                'clicks': platform_metrics.get('clicks', 0),
                'engagement_rate': engagement_rate,
                'performance_score': performance_score,
                'platform_metrics': platform_metrics,  # Store raw metrics
            }
            
            return self.db.update_metrics(post_id, metrics_data)
            
        except Exception as e:
            logger.error(f"Error tracking post metrics: {str(e)}")
            return False

    async def get_performance_report(self, 
                                   platform: Optional[str] = None,
                                   days: int = 30,
                                   category: Optional[str] = None) -> Dict:
        """
        Generate comprehensive performance report
        
        Args:
            platform: Optional platform filter
            days: Number of days to analyze
            category: Optional content category filter
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Base query
            query = self.db.session.query(PostHistory)
            
            # Apply filters
            if platform:
                query = query.filter(PostHistory.platform == platform)
            if category:
                query = query.join(ContentSource).filter(ContentSource.category == category)
            
            posts = query.filter(PostHistory.posted_at >= start_date).all()
            
            # Aggregate metrics
            total_metrics = {
                'posts': len(posts),
                'likes': 0,
                'comments': 0,
                'shares': 0,
                'views': 0,
                'clicks': 0
            }
            
            engagement_rates = []
            performance_scores = []
            top_posts = []
            
            for post in posts:
                if post.metrics:
                    metrics = post.metrics
                    # Aggregate totals
                    total_metrics['likes'] += metrics.likes
                    total_metrics['comments'] += metrics.comments
                    total_metrics['shares'] += metrics.shares
                    total_metrics['views'] += metrics.views
                    total_metrics['clicks'] += metrics.clicks
                    
                    # Track rates and scores
                    if metrics.engagement_rate:
                        engagement_rates.append(metrics.engagement_rate)
                    if metrics.performance_score:
                        performance_scores.append(metrics.performance_score)
                    
                    # Track top posts
                    top_posts.append({
                        'post_id': post.id,
                        'content': post.content[:100] + '...',  # Preview
                        'platform': post.platform,
                        'posted_at': post.posted_at.isoformat(),
                        'metrics': {
                            'likes': metrics.likes,
                            'comments': metrics.comments,
                            'shares': metrics.shares,
                            'views': metrics.views,
                            'engagement_rate': metrics.engagement_rate
                        }
                    })
            
            # Sort and get top performers
            top_posts.sort(key=lambda x: x['metrics']['engagement_rate'], reverse=True)
            
            return {
                'period': {
                    'start': start_date.isoformat(),
                    'end': datetime.utcnow().isoformat(),
                    'days': days
                },
                'total_metrics': total_metrics,
                'averages': {
                    'likes_per_post': total_metrics['likes'] / len(posts) if posts else 0,
                    'comments_per_post': total_metrics['comments'] / len(posts) if posts else 0,
                    'shares_per_post': total_metrics['shares'] / len(posts) if posts else 0,
                    'views_per_post': total_metrics['views'] / len(posts) if posts else 0,
                    'engagement_rate': sum(engagement_rates) / len(engagement_rates) if engagement_rates else 0,
                    'performance_score': sum(performance_scores) / len(performance_scores) if performance_scores else 0
                },
                'top_performing_posts': top_posts[:5],  # Top 5 posts
                'platform_breakdown': self._get_platform_breakdown(posts) if not platform else None,
                'category_breakdown': self._get_category_breakdown(posts) if not category else None
            }
            
        except Exception as e:
            logger.error(f"Error generating performance report: {str(e)}")
            return {}

    def _calculate_engagement_rate(self, metrics: Dict) -> float:
        """Calculate engagement rate from metrics"""
        try:
            total_engagement = (
                metrics.get('likes', 0) +
                metrics.get('comments', 0) * 2 +  # Weight comments more
                metrics.get('shares', 0) * 3      # Weight shares most
            )
            views = metrics.get('views', 0)
            if views > 0:
                return (total_engagement / views) * 100
            return 0
        except:
            return 0

    def _calculate_performance_score(self, metrics: Dict) -> float:
        """Calculate overall performance score (0-100)"""
        try:
            # Calculate weighted sum
            weighted_sum = sum(
                metrics.get(metric, 0) * self.metric_weights[metric] 
                for metric in self.metric_weights
            )
            
            # Normalize to 0-100 scale (you might need to adjust the normalization factor)
            return min(100, weighted_sum / 100)
        except:
            return 0

    def _get_platform_breakdown(self, posts: List[PostHistory]) -> Dict:
        """Get performance breakdown by platform"""
        breakdown = {}
        for post in posts:
            if post.platform not in breakdown:
                breakdown[post.platform] = {
                    'posts': 0,
                    'total_engagement': 0,
                    'avg_engagement_rate': 0
                }
            
            breakdown[post.platform]['posts'] += 1
            if post.metrics:
                breakdown[post.platform]['total_engagement'] += (
                    post.metrics.likes +
                    post.metrics.comments +
                    post.metrics.shares
                )
                if post.metrics.engagement_rate:
                    current_avg = breakdown[post.platform]['avg_engagement_rate']
                    new_count = breakdown[post.platform]['posts']
                    breakdown[post.platform]['avg_engagement_rate'] = (
                        (current_avg * (new_count - 1) + post.metrics.engagement_rate) / new_count
                    )
        
        return breakdown

    def _get_category_breakdown(self, posts: List[PostHistory]) -> Dict:
        """Get performance breakdown by content category"""
        breakdown = {}
        for post in posts:
            category = post.source.category if post.source else 'uncategorized'
            if category not in breakdown:
                breakdown[category] = {
                    'posts': 0,
                    'total_engagement': 0,
                    'avg_performance_score': 0
                }
            
            breakdown[category]['posts'] += 1
            if post.metrics:
                breakdown[category]['total_engagement'] += (
                    post.metrics.likes +
                    post.metrics.comments +
                    post.metrics.shares
                )
                if post.metrics.performance_score:
                    current_avg = breakdown[category]['avg_performance_score']
                    new_count = breakdown[category]['posts']
                    breakdown[category]['avg_performance_score'] = (
                        (current_avg * (new_count - 1) + post.metrics.performance_score) / new_count
                    )
        
        return breakdown

    async def track_audience_growth(self, platform: str, timeframe: str = 'day') -> Dict:
        """Track audience growth metrics"""
        try:
            # Get historical audience data
            audience_metrics = await self.db.get_audience_metrics(platform, timeframe)
            
            # Calculate growth rates
            current_followers = audience_metrics.get('current_followers', 0)
            previous_followers = audience_metrics.get('previous_followers', 0)
            
            growth_rate = ((current_followers - previous_followers) / max(1, previous_followers)) * 100
            
            return {
                'success': True,
                'platform': platform,
                'metrics': {
                    'current_followers': current_followers,
                    'new_followers': current_followers - previous_followers,
                    'growth_rate': growth_rate,
                    'engagement_rate': audience_metrics.get('engagement_rate', 0),
                    'active_followers': audience_metrics.get('active_followers', 0)
                },
                'timeframe': timeframe,
                'tracked_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error tracking audience growth: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def calculate_engagement_metrics(self, post_id: int) -> Dict:
        """Calculate detailed engagement metrics for a post"""
        try:
            post = await self.db.get_post_performance(post_id)
            if not post:
                raise ValueError(f"Post not found: {post_id}")

            metrics = post.get('metrics', {})
            total_engagement = sum([
                metrics.get('likes', 0) * self.metric_weights['likes'],
                metrics.get('comments', 0) * self.metric_weights['comments'],
                metrics.get('shares', 0) * self.metric_weights['shares']
            ])
            
            views = metrics.get('views', 0)
            engagement_rate = (total_engagement / max(1, views)) * 100
            
            # Calculate velocity metrics
            time_since_post = (datetime.utcnow() - datetime.fromisoformat(post['posted_at'])).total_seconds()
            engagement_velocity = total_engagement / max(1, time_since_post / 3600)  # Per hour
            
            return {
                'success': True,
                'post_id': post_id,
                'metrics': {
                    'total_engagement': total_engagement,
                    'engagement_rate': engagement_rate,
                    'engagement_velocity': engagement_velocity,
                    'weighted_score': total_engagement * (engagement_rate / 100),
                    'engagement_breakdown': {
                        'likes': {
                            'count': metrics.get('likes', 0),
                            'weighted': metrics.get('likes', 0) * self.metric_weights['likes']
                        },
                        'comments': {
                            'count': metrics.get('comments', 0),
                            'weighted': metrics.get('comments', 0) * self.metric_weights['comments']
                        },
                        'shares': {
                            'count': metrics.get('shares', 0),
                            'weighted': metrics.get('shares', 0) * self.metric_weights['shares']
                        }
                    }
                },
                'calculated_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error calculating engagement metrics: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def analyze_content_performance(self, days: int = 30) -> Dict:
        """Analyze content performance patterns"""
        try:
            posts = await self.db.get_post_history(days=days)
            
            performance_data = {
                'total_posts': len(posts),
                'engagement_by_type': {},
                'performance_by_time': {},
                'top_performing': [],
                'content_patterns': {
                    'optimal_length': 0,
                    'optimal_posting_times': [],
                    'successful_topics': []
                }
            }
            
            # Analyze each post
            for post in posts:
                metrics = post.get('metrics', {})
                posted_time = datetime.fromisoformat(post['posted_at']).strftime('%H:00')
                
                # Track engagement by post type
                post_type = self._determine_post_type(post['content'])
                if post_type not in performance_data['engagement_by_type']:
                    performance_data['engagement_by_type'][post_type] = {
                        'posts': 0,
                        'total_engagement': 0,
                        'avg_engagement_rate': 0
                    }
                
                type_data = performance_data['engagement_by_type'][post_type]
                type_data['posts'] += 1
                type_data['total_engagement'] += sum([
                    metrics.get('likes', 0),
                    metrics.get('comments', 0),
                    metrics.get('shares', 0)
                ])
                
                # Track performance by time
                if posted_time not in performance_data['performance_by_time']:
                    performance_data['performance_by_time'][posted_time] = {
                        'posts': 0,
                        'total_engagement': 0,
                        'avg_engagement_rate': 0
                    }
                
                time_data = performance_data['performance_by_time'][posted_time]
                time_data['posts'] += 1
                time_data['total_engagement'] += metrics.get('engagement_rate', 0)
                
                # Track top performing posts
                if metrics.get('engagement_rate', 0) > 0:
                    performance_data['top_performing'].append({
                        'post_id': post['id'],
                        'content_preview': post['content'][:100],
                        'engagement_rate': metrics['engagement_rate'],
                        'posted_at': post['posted_at']
                    })
            
            # Calculate averages and sort data
            for type_data in performance_data['engagement_by_type'].values():
                type_data['avg_engagement_rate'] = type_data['total_engagement'] / type_data['posts']
                
            for time_data in performance_data['performance_by_time'].values():
                time_data['avg_engagement_rate'] = time_data['total_engagement'] / time_data['posts']
            
            # Sort top performing posts
            performance_data['top_performing'].sort(
                key=lambda x: x['engagement_rate'],
                reverse=True
            )
            performance_data['top_performing'] = performance_data['top_performing'][:5]
            
            # Find optimal posting times
            sorted_times = sorted(
                performance_data['performance_by_time'].items(),
                key=lambda x: x[1]['avg_engagement_rate'],
                reverse=True
            )
            performance_data['content_patterns']['optimal_posting_times'] = [
                time for time, _ in sorted_times[:3]
            ]
            
            return {
                'success': True,
                'analysis': performance_data,
                'analyzed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing content performance: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _determine_post_type(self, content: str) -> str:
        """Determine the type of post based on content"""
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

    async def generate_trend_report(self, platform: str = None, days: int = 30) -> Dict:
        """Generate trend analysis report"""
        try:
            # Get historical data
            posts = await self.db.get_post_history(platform=platform, days=days)
            
            # Initialize trend data
            trends = {
                'engagement_trends': {
                    'likes': [],
                    'comments': [],
                    'shares': []
                },
                'posting_patterns': {
                    'frequency': {},
                    'timing': {}
                },
                'content_trends': {
                    'topics': {},
                    'hashtags': {},
                    'mentions': {}
                }
            }
            
            # Analyze each post
            for post in posts:
                posted_date = datetime.fromisoformat(post['posted_at']).date()
                metrics = post.get('metrics', {})
                
                # Track engagement trends
                for metric in ['likes', 'comments', 'shares']:
                    trends['engagement_trends'][metric].append({
                        'date': posted_date.isoformat(),
                        'value': metrics.get(metric, 0)
                    })
                
                # Track posting patterns
                day_name = posted_date.strftime('%A')
                hour = datetime.fromisoformat(post['posted_at']).strftime('%H:00')
                
                trends['posting_patterns']['frequency'][day_name] = \
                    trends['posting_patterns']['frequency'].get(day_name, 0) + 1
                trends['posting_patterns']['timing'][hour] = \
                    trends['posting_patterns']['timing'].get(hour, 0) + 1
                
                # Track content patterns
                content = post['content']
                hashtags = re.findall(r'#(\w+)', content)
                mentions = re.findall(r'@(\w+)', content)
                
                for hashtag in hashtags:
                    trends['content_trends']['hashtags'][hashtag] = \
                        trends['content_trends']['hashtags'].get(hashtag, 0) + 1
                
                for mention in mentions:
                    trends['content_trends']['mentions'][mention] = \
                        trends['content_trends']['mentions'].get(mention, 0) + 1
            
            # Sort and limit trend data
            for metric in trends['engagement_trends']:
                trends['engagement_trends'][metric].sort(key=lambda x: x['date'])
            
            trends['content_trends']['hashtags'] = dict(sorted(
                trends['content_trends']['hashtags'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10])
            
            trends['content_trends']['mentions'] = dict(sorted(
                trends['content_trends']['mentions'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10])
            
            return {
                'success': True,
                'trends': trends,
                'metadata': {
                    'platform': platform,
                    'days_analyzed': days,
                    'total_posts': len(posts),
                    'generated_at': datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating trend report: {str(e)}")
            return {'success': False, 'error': str(e)}

    """Add new tracking methods:
    1. Audience growth tracking
    2. Engagement rate calculation
    3. Content performance scoring
    4. Trend analysis
    """ 