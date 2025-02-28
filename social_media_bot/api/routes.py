from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from ..analytics.performance_tracker import PerformanceTracker
from ..analytics.engagement_analyzer import EngagementAnalyzer
from ..scheduler.posting_optimizer import PostingOptimizer
from ..database.db_manager import DatabaseManager
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1")

# Dependency injection
def get_db():
    db = DatabaseManager()
    try:
        yield db
    finally:
        db.close()

def get_analytics(db: DatabaseManager = Depends(get_db)):
    return PerformanceTracker(db), EngagementAnalyzer(db)

def get_scheduler(db: DatabaseManager = Depends(get_db),
                 analytics: tuple = Depends(get_analytics)):
    return PostingOptimizer(db, analytics[0])

# Request/Response Models
class AnalyticsPeriod(BaseModel):
    start_date: datetime
    end_date: datetime
    platform: Optional[str] = None
    metrics: List[str] = ['engagement', 'reach', 'growth']

class ScheduleRequest(BaseModel):
    content: List[Dict]
    platforms: List[str]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class ContentMetrics(BaseModel):
    post_id: int
    metrics: Dict
    timestamp: datetime

# Analytics Endpoints
@router.get("/analytics/summary")
async def get_analytics_summary(
    period: int = Query(7, description="Days to analyze"),
    platform: Optional[str] = None,
    db: DatabaseManager = Depends(get_db),
    analytics: tuple = Depends(get_analytics)
) -> Dict:
    """Get summary of performance metrics"""
    try:
        performance_tracker, engagement_analyzer = analytics
        
        # Get performance summary
        performance_data = await performance_tracker.analyze_content_performance(days=period)
        if not performance_data['success']:
            raise HTTPException(status_code=500, detail="Failed to analyze performance")
            
        # Get engagement patterns
        engagement_data = await engagement_analyzer.analyze_engagement_patterns(
            platform=platform,
            days=period
        )
        if not engagement_data['success']:
            raise HTTPException(status_code=500, detail="Failed to analyze engagement")
        
        return {
            'success': True,
            'period': {
                'days': period,
                'start': (datetime.utcnow() - timedelta(days=period)).isoformat(),
                'end': datetime.utcnow().isoformat()
            },
            'performance': performance_data['analysis'],
            'engagement': engagement_data['patterns'],
            'generated_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/trends")
async def get_trend_analysis(
    platform: Optional[str] = None,
    days: int = Query(30, description="Days to analyze"),
    db: DatabaseManager = Depends(get_db),
    analytics: tuple = Depends(get_analytics)
) -> Dict:
    """Get trend analysis data"""
    try:
        performance_tracker = analytics[0]
        trend_data = await performance_tracker.generate_trend_report(
            platform=platform,
            days=days
        )
        
        if not trend_data['success']:
            raise HTTPException(status_code=500, detail="Failed to generate trend report")
            
        return trend_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Content Management Endpoints
@router.get("/content/scheduled")
async def get_scheduled_content(
    platform: Optional[str] = None,
    start_date: Optional[datetime] = None,
    db: DatabaseManager = Depends(get_db)
) -> Dict:
    """Get upcoming scheduled posts"""
    try:
        posts = await db.get_post_history(
            platform=platform,
            status='scheduled',
            days=30 if not start_date else None
        )
        
        return {
            'success': True,
            'scheduled_posts': posts,
            'count': len(posts),
            'retrieved_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/content/schedule")
async def schedule_content(
    request: ScheduleRequest,
    scheduler: PostingOptimizer = Depends(get_scheduler)
) -> Dict:
    """Schedule content for posting"""
    try:
        schedule = await scheduler.generate_posting_schedule(request.content)
        if not schedule['success']:
            raise HTTPException(status_code=500, detail="Failed to generate schedule")
            
        return schedule
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Performance Reporting Endpoints
@router.get("/performance/reports")
async def get_performance_reports(
    platform: Optional[str] = None,
    days: int = Query(30, description="Days to analyze"),
    analytics: tuple = Depends(get_analytics)
) -> Dict:
    """Get detailed performance reports"""
    try:
        engagement_analyzer = analytics[1]
        report = await engagement_analyzer.generate_performance_report(
            platform=platform,
            days=days
        )
        
        if not report['success']:
            raise HTTPException(status_code=500, detail="Failed to generate performance report")
            
        return report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/metrics/{post_id}")
async def get_post_metrics(
    post_id: int,
    db: DatabaseManager = Depends(get_db),
    analytics: tuple = Depends(get_analytics)
) -> Dict:
    """Get metrics for a specific post"""
    try:
        performance_tracker = analytics[0]
        metrics = await performance_tracker.calculate_engagement_metrics(post_id)
        
        if not metrics['success']:
            raise HTTPException(status_code=404, detail="Post not found or metrics unavailable")
            
        return metrics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Optimization Endpoints
@router.get("/optimize/timing")
async def get_optimal_posting_time(
    platform: str,
    content_type: Optional[str] = None,
    scheduler: PostingOptimizer = Depends(get_scheduler)
) -> Dict:
    """Get optimal posting time for content"""
    try:
        content = {'platform': platform, 'type': content_type} if content_type else {'platform': platform}
        optimal_time = await scheduler.get_optimal_posting_time(platform, content)
        
        return {
            'success': True,
            'platform': platform,
            'optimal_time': optimal_time.isoformat(),
            'content_type': content_type,
            'calculated_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 