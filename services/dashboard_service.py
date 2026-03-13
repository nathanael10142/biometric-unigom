"""
Dashboard Service - Meta-inspired microservice for dashboard analytics
Handles real-time dashboard data, metrics, and analytics
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import asyncio
from contextlib import asynccontextmanager

from app.database import LocalSessionLocal
from app.models.attendance import AttendanceRecord
from app.models.scan_log import ScanLog
from app.config import settings

logger = logging.getLogger("dashboard-service")

# Dashboard analytics service
dashboard_service = FastAPI(
    title="Dashboard Analytics Service",
    description="Meta-inspired dashboard analytics microservice",
    version="1.0.0"
)

dashboard_service.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DashboardAnalytics:
    """Meta-style analytics engine for dashboard metrics"""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes cache
        self.real_time_subscribers = []
    
    def get_cache_key(self, metric_type: str, params: Dict = None) -> str:
        """Generate cache key for metrics"""
        param_str = str(sorted(params.items())) if params else ""
        return f"{metric_type}:{param_str}"
    
    def is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.cache:
            return False
        
        cached_time = self.cache[cache_key].get("timestamp")
        if not cached_time:
            return False
        
        return datetime.now() - cached_time < timedelta(seconds=self.cache_ttl)
    
    def get_cached_data(self, cache_key: str) -> Optional[Any]:
        """Get data from cache if valid"""
        if self.is_cache_valid(cache_key):
            return self.cache[cache_key]["data"]
        return None
    
    def set_cache_data(self, cache_key: str, data: Any):
        """Set data in cache with timestamp"""
        self.cache[cache_key] = {
            "data": data,
            "timestamp": datetime.now()
        }
    
    async def get_real_time_metrics(self, db: Session) -> Dict[str, Any]:
        """Get real-time dashboard metrics"""
        cache_key = "real_time_metrics"
        cached_data = self.get_cached_data(cache_key)
        
        if cached_data:
            return cached_data
        
        try:
            today = datetime.now().date()
            
            # Get today's attendance stats
            today_records = db.query(AttendanceRecord).filter(
                func.date(AttendanceRecord.check_in) == today
            ).all()
            
            present_count = len([r for r in today_records if r.check_in and not r.is_late])
            late_count = len([r for r in today_records if r.is_late])
            absent_count = 0  # Would need employee list to calculate
            
            # Get total employees
            total_employees = db.query(AttendanceRecord.employee_id).distinct().count()
            
            # Calculate attendance rate
            attendance_rate = (present_count / total_employees * 100) if total_employees > 0 else 0
            
            metrics = {
                "date": today.isoformat(),
                "present": present_count,
                "late": late_count,
                "absent": absent_count,
                "refused": 0,
                "total_employees": total_employees,
                "attendance_rate": round(attendance_rate, 1),
                "is_weekend": today.weekday() >= 5,
                "last_updated": datetime.now().isoformat()
            }
            
            self.set_cache_data(cache_key, metrics)
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting real-time metrics: {e}")
            raise HTTPException(status_code=500, detail="Failed to get metrics")
    
    async def get_weekly_data(self, db: Session, days: int = 7) -> List[Dict[str, Any]]:
        """Get weekly attendance data"""
        cache_key = f"weekly_data:{days}"
        cached_data = self.get_cached_data(cache_key)
        
        if cached_data:
            return cached_data
        
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days-1)
            
            # Query attendance data for the week
            weekly_records = db.query(
                func.date(AttendanceRecord.check_in).label('date'),
                AttendanceRecord.employee_id,
                AttendanceRecord.is_late,
                AttendanceRecord.check_out
            ).filter(
                func.date(AttendanceRecord.check_in) >= start_date,
                func.date(AttendanceRecord.check_in) <= end_date
            ).all()
            
            # Process data by day
            daily_stats = {}
            for record in weekly_records:
                date_str = record.date.strftime('%Y-%m-%d')
                day_name = record.date.strftime('%a')  # Mon, Tue, etc.
                
                if date_str not in daily_stats:
                    daily_stats[date_str] = {
                        'date': date_str,
                        'day_label': day_name,
                        'present': 0,
                        'late': 0,
                        'absent': 0,
                        'refused': 0
                    }
                
                if record.check_in and not record.is_late:
                    daily_stats[date_str]['present'] += 1
                elif record.is_late:
                    daily_stats[date_str]['late'] += 1
            
            # Convert to list and sort by date
            weekly_data = sorted(daily_stats.values(), key=lambda x: x['date'])
            
            self.set_cache_data(cache_key, weekly_data)
            return weekly_data
            
        except Exception as e:
            logger.error(f"Error getting weekly data: {e}")
            raise HTTPException(status_code=500, detail="Failed to get weekly data")
    
    async def get_recent_activity(self, db: Session, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent attendance activity"""
        cache_key = f"recent_activity:{limit}"
        cached_data = self.get_cached_data(cache_key)
        
        if cached_data:
            return cached_data
        
        try:
            # Get recent scan logs
            recent_scans = db.query(ScanLog).order_by(ScanLog.timestamp.desc()).limit(limit).all()
            
            activity = []
            for scan in recent_scans:
                activity.append({
                    "employee_name": scan.employee_name or "Unknown",
                    "status": "present" if scan.success else "failed",
                    "time": scan.timestamp.strftime("%H:%M"),
                    "action": "Entrée" if scan.success else "Échec",
                    "timestamp": scan.timestamp.isoformat()
                })
            
            self.set_cache_data(cache_key, activity)
            return activity
            
        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")
            raise HTTPException(status_code=500, detail="Failed to get recent activity")
    
    async def get_analytics_insights(self, db: Session) -> Dict[str, Any]:
        """Get advanced analytics insights"""
        cache_key = "analytics_insights"
        cached_data = self.get_cached_data(cache_key)
        
        if cached_data:
            return cached_data
        
        try:
            # Get trends and patterns
            last_30_days = datetime.now() - timedelta(days=30)
            
            # Monthly trends
            monthly_trend = db.query(
                func.date(AttendanceRecord.check_in).label('date'),
                func.count(AttendanceRecord.id).label('count')
            ).filter(
                AttendanceRecord.check_in >= last_30_days
            ).group_by(func.date(AttendanceRecord.check_in)).all()
            
            # Peak hours analysis
            peak_hours = db.query(
                func.extract('hour', AttendanceRecord.check_in).label('hour'),
                func.count(AttendanceRecord.id).label('count')
            ).group_by(func.extract('hour', AttendanceRecord.check_in)).all()
            
            insights = {
                "monthly_trend": [{"date": str(t.date), "count": t.count} for t in monthly_trend],
                "peak_hours": [{"hour": int(t.hour), "count": t.count} for t in peak_hours],
                "generated_at": datetime.now().isoformat()
            }
            
            self.set_cache_data(cache_key, insights)
            return insights
            
        except Exception as e:
            logger.error(f"Error getting analytics insights: {e}")
            raise HTTPException(status_code=500, detail="Failed to get insights")

# Initialize analytics engine
analytics = DashboardAnalytics()

def get_db():
    """Database dependency"""
    db = LocalSessionLocal()
    try:
        yield db
    finally:
        db.close()

@dashboard_service.on_event("startup")
async def startup_event():
    """Initialize dashboard service"""
    logger.info("Starting Dashboard Analytics Service...")

@dashboard_service.get("/health")
async def health_check():
    """Service health check"""
    return {
        "status": "healthy",
        "service": "dashboard-analytics",
        "cache_size": len(analytics.cache),
        "timestamp": datetime.now().isoformat()
    }

@dashboard_service.get("/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics"""
    return await analytics.get_real_time_metrics(db)

@dashboard_service.get("/weekly")
async def get_weekly_attendance(
    days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """Get weekly attendance data"""
    return await analytics.get_weekly_data(db, days)

@dashboard_service.get("/recent-activity")
async def get_recent_activity(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get recent activity"""
    return await analytics.get_recent_activity(db, limit)

@dashboard_service.get("/analytics")
async def get_analytics(db: Session = Depends(get_db)):
    """Get advanced analytics insights"""
    return await analytics.get_analytics_insights(db)

@dashboard_service.post("/refresh-cache")
async def refresh_cache():
    """Refresh analytics cache"""
    analytics.cache.clear()
    return {"message": "Cache refreshed", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(dashboard_service, host="0.0.0.0", port=8004)
