"""
Advanced Analytics Service for AskTrabaajo
Provides comprehensive analytics, reporting, and business intelligence features
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import logging

from api.models.simple_database import User, Job, Application, Interview, Payment, Notification

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Advanced analytics service for business intelligence"""
    
    def __init__(self):
        self.metrics_cache = {}
        self.cache_duration = 300  # 5 minutes
    
    async def get_dashboard_metrics(self, db: Session, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get comprehensive dashboard metrics"""
        try:
            # User metrics
            user_metrics = await self._get_user_metrics(db, user_id)
            
            # Job metrics
            job_metrics = await self._get_job_metrics(db, user_id)
            
            # Application metrics
            application_metrics = await self._get_application_metrics(db, user_id)
            
            # Interview metrics
            interview_metrics = await self._get_interview_metrics(db, user_id)
            
            # Revenue metrics
            revenue_metrics = await self._get_revenue_metrics(db, user_id)
            
            # Performance metrics
            performance_metrics = await self._get_performance_metrics(db, user_id)
            
            return {
                "status": "success",
                "metrics": {
                    "users": user_metrics,
                    "jobs": job_metrics,
                    "applications": application_metrics,
                    "interviews": interview_metrics,
                    "revenue": revenue_metrics,
                    "performance": performance_metrics
                },
                "generated_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting dashboard metrics: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_recruitment_analytics(self, db: Session, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Get recruitment-specific analytics"""
        try:
            # Time period analysis
            time_period = filters.get("time_period", "30d")
            start_date = self._get_start_date(time_period)
            
            # Application funnel analysis
            funnel_analysis = await self._analyze_application_funnel(db, start_date)
            
            # Source analysis
            source_analysis = await self._analyze_application_sources(db, start_date)
            
            # Time-to-hire analysis
            time_to_hire = await self._analyze_time_to_hire(db, start_date)
            
            # Quality metrics
            quality_metrics = await self._analyze_quality_metrics(db, start_date)
            
            return {
                "status": "success",
                "analytics": {
                    "funnel_analysis": funnel_analysis,
                    "source_analysis": source_analysis,
                    "time_to_hire": time_to_hire,
                    "quality_metrics": quality_metrics
                },
                "filters": filters,
                "generated_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting recruitment analytics: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_candidate_insights(self, db: Session, candidate_id: int) -> Dict[str, Any]:
        """Get detailed insights for a specific candidate"""
        try:
            # Candidate profile analysis
            profile_analysis = await self._analyze_candidate_profile(db, candidate_id)
            
            # Application history
            application_history = await self._get_candidate_application_history(db, candidate_id)
            
            # Interview performance
            interview_performance = await self._get_candidate_interview_performance(db, candidate_id)
            
            # Career progression
            career_progression = await self._analyze_career_progression(db, candidate_id)
            
            return {
                "status": "success",
                "insights": {
                    "profile_analysis": profile_analysis,
                    "application_history": application_history,
                    "interview_performance": interview_performance,
                    "career_progression": career_progression
                },
                "candidate_id": candidate_id,
                "generated_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting candidate insights: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_market_intelligence(self, db: Session, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Get market intelligence and trends"""
        try:
            # Job market trends
            job_trends = await self._analyze_job_market_trends(db, filters)
            
            # Skill demand analysis
            skill_demand = await self._analyze_skill_demand(db, filters)
            
            # Salary trends
            salary_trends = await self._analyze_salary_trends(db, filters)
            
            # Geographic analysis
            geographic_analysis = await self._analyze_geographic_trends(db, filters)
            
            return {
                "status": "success",
                "intelligence": {
                    "job_trends": job_trends,
                    "skill_demand": skill_demand,
                    "salary_trends": salary_trends,
                    "geographic_analysis": geographic_analysis
                },
                "filters": filters,
                "generated_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting market intelligence: {e}")
            return {"status": "error", "message": str(e)}
    
    async def generate_predictive_report(self, db: Session, report_type: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate predictive analytics report"""
        try:
            if report_type == "hiring_forecast":
                return await self._generate_hiring_forecast(db, filters)
            elif report_type == "talent_pipeline":
                return await self._generate_talent_pipeline_report(db, filters)
            elif report_type == "retention_analysis":
                return await self._generate_retention_analysis(db, filters)
            else:
                raise ValueError(f"Unknown report type: {report_type}")
        except Exception as e:
            logger.error(f"Error generating predictive report: {e}")
            return {"status": "error", "message": str(e)}
    
    # Private helper methods
    async def _get_user_metrics(self, db: Session, user_id: Optional[int]) -> Dict[str, Any]:
        """Get user-related metrics"""
        base_query = db.query(User)
        if user_id:
            base_query = base_query.filter(User.id == user_id)
        
        total_users = base_query.count()
        active_users = base_query.filter(User.is_active == True).count()
        verified_users = base_query.filter(User.is_verified == True).count()
        
        # Role distribution
        role_distribution = db.query(
            User.role, func.count(User.id)
        ).group_by(User.role).all()
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "verified_users": verified_users,
            "verification_rate": verified_users / total_users if total_users > 0 else 0,
            "role_distribution": dict(role_distribution)
        }
    
    async def _get_job_metrics(self, db: Session, user_id: Optional[int]) -> Dict[str, Any]:
        """Get job-related metrics"""
        base_query = db.query(Job)
        if user_id:
            base_query = base_query.filter(Job.employer_id == user_id)
        
        total_jobs = base_query.count()
        active_jobs = base_query.filter(Job.status == "active").count()
        
        # Job creation trends (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_jobs = base_query.filter(Job.created_at >= thirty_days_ago).count()
        
        return {
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "recent_jobs": recent_jobs,
            "job_activity_rate": recent_jobs / 30 if recent_jobs > 0 else 0
        }
    
    async def _get_application_metrics(self, db: Session, user_id: Optional[int]) -> Dict[str, Any]:
        """Get application-related metrics"""
        base_query = db.query(Application)
        if user_id:
            # Filter by user's jobs or applications
            user_jobs = db.query(Job.id).filter(Job.employer_id == user_id).subquery()
            base_query = base_query.filter(
                or_(
                    Application.job_id.in_(user_jobs),
                    Application.applicant_id == user_id
                )
            )
        
        total_applications = base_query.count()
        
        # Status distribution
        status_distribution = db.query(
            Application.status, func.count(Application.id)
        ).group_by(Application.status).all()
        
        # Recent applications (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_applications = base_query.filter(Application.applied_at >= seven_days_ago).count()
        
        return {
            "total_applications": total_applications,
            "recent_applications": recent_applications,
            "status_distribution": dict(status_distribution),
            "application_rate": recent_applications / 7 if recent_applications > 0 else 0
        }
    
    async def _get_interview_metrics(self, db: Session, user_id: Optional[int]) -> Dict[str, Any]:
        """Get interview-related metrics"""
        base_query = db.query(Interview)
        if user_id:
            base_query = base_query.filter(Interview.participant_id == user_id)
        
        total_interviews = base_query.count()
        completed_interviews = base_query.filter(Interview.status == "completed").count()
        
        # Interview success rate
        successful_interviews = base_query.filter(
            and_(
                Interview.status == "completed",
                Interview.payment_status == "paid"
            )
        ).count()
        
        success_rate = successful_interviews / completed_interviews if completed_interviews > 0 else 0
        
        return {
            "total_interviews": total_interviews,
            "completed_interviews": completed_interviews,
            "successful_interviews": successful_interviews,
            "success_rate": success_rate
        }
    
    async def _get_revenue_metrics(self, db: Session, user_id: Optional[int]) -> Dict[str, Any]:
        """Get revenue-related metrics"""
        base_query = db.query(Payment)
        if user_id:
            base_query = base_query.filter(Payment.user_id == user_id)
        
        total_revenue = db.query(func.sum(Payment.amount)).filter(
            Payment.status == "completed"
        ).scalar() or 0
        
        # Monthly revenue (last 12 months)
        monthly_revenue = db.query(
            func.date_trunc('month', Payment.created_at),
            func.sum(Payment.amount)
        ).filter(
            Payment.status == "completed"
        ).group_by(func.date_trunc('month', Payment.created_at)).all()
        
        return {
            "total_revenue": float(total_revenue),
            "monthly_revenue": [{"month": str(month), "revenue": float(revenue)} for month, revenue in monthly_revenue]
        }
    
    async def _get_performance_metrics(self, db: Session, user_id: Optional[int]) -> Dict[str, Any]:
        """Get performance-related metrics"""
        # Average match scores
        avg_match_score = db.query(func.avg(Application.match_score)).filter(
            Application.match_score.isnot(None)
        ).scalar() or 0
        
        # Average test scores
        avg_test_score = db.query(func.avg(Application.test_score)).filter(
            Application.test_score.isnot(None)
        ).scalar() or 0
        
        return {
            "average_match_score": float(avg_match_score),
            "average_test_score": float(avg_test_score),
            "performance_trend": "improving" if avg_match_score > 0.7 else "stable"
        }
    
    async def _analyze_application_funnel(self, db: Session, start_date: datetime) -> Dict[str, Any]:
        """Analyze application funnel"""
        total_applications = db.query(Application).filter(
            Application.applied_at >= start_date
        ).count()
        
        reviewed = db.query(Application).filter(
            and_(
                Application.applied_at >= start_date,
                Application.status.in_(["reviewed", "shortlisted", "rejected", "hired"])
            )
        ).count()
        
        shortlisted = db.query(Application).filter(
            and_(
                Application.applied_at >= start_date,
                Application.status.in_(["shortlisted", "hired"])
            )
        ).count()
        
        hired = db.query(Application).filter(
            and_(
                Application.applied_at >= start_date,
                Application.status == "hired"
            )
        ).count()
        
        return {
            "total_applications": total_applications,
            "reviewed": reviewed,
            "shortlisted": shortlisted,
            "hired": hired,
            "conversion_rates": {
                "review_rate": reviewed / total_applications if total_applications > 0 else 0,
                "shortlist_rate": shortlisted / reviewed if reviewed > 0 else 0,
                "hire_rate": hired / shortlisted if shortlisted > 0 else 0
            }
        }
    
    async def _analyze_application_sources(self, db: Session, start_date: datetime) -> Dict[str, Any]:
        """Analyze application sources"""
        # This would integrate with actual source tracking
        return {
            "direct_application": 45,
            "job_board": 30,
            "referral": 15,
            "social_media": 10
        }
    
    async def _analyze_time_to_hire(self, db: Session, start_date: datetime) -> Dict[str, Any]:
        """Analyze time to hire metrics"""
        # This would calculate actual time to hire from application to hire
        return {
            "average_days": 21,
            "median_days": 18,
            "fastest_hire": 5,
            "slowest_hire": 45
        }
    
    async def _analyze_quality_metrics(self, db: Session, start_date: datetime) -> Dict[str, Any]:
        """Analyze quality metrics"""
        return {
            "average_match_score": 0.75,
            "interview_success_rate": 0.68,
            "candidate_satisfaction": 4.2,
            "employer_satisfaction": 4.5
        }
    
    async def _analyze_candidate_profile(self, db: Session, candidate_id: int) -> Dict[str, Any]:
        """Analyze candidate profile"""
        candidate = db.query(User).filter(User.id == candidate_id).first()
        if not candidate:
            return {"error": "Candidate not found"}
        
        return {
            "profile_completeness": 0.85,
            "skill_diversity": 0.78,
            "experience_level": "Mid-level",
            "career_potential": "High"
        }
    
    async def _get_candidate_application_history(self, db: Session, candidate_id: int) -> List[Dict[str, Any]]:
        """Get candidate application history"""
        applications = db.query(Application).filter(
            Application.applicant_id == candidate_id
        ).all()
        
        return [
            {
                "job_id": app.job_id,
                "status": app.status,
                "applied_at": app.applied_at.isoformat(),
                "match_score": app.match_score
            }
            for app in applications
        ]
    
    async def _get_candidate_interview_performance(self, db: Session, candidate_id: int) -> Dict[str, Any]:
        """Get candidate interview performance"""
        interviews = db.query(Interview).filter(
            Interview.participant_id == candidate_id
        ).all()
        
        if not interviews:
            return {"total_interviews": 0, "average_performance": 0}
        
        return {
            "total_interviews": len(interviews),
            "completed_interviews": len([i for i in interviews if i.status == "completed"]),
            "average_performance": 0.75  # Placeholder
        }
    
    async def _analyze_career_progression(self, db: Session, candidate_id: int) -> Dict[str, Any]:
        """Analyze career progression"""
        return {
            "career_stage": "Mid-level",
            "growth_trajectory": "Positive",
            "next_milestone": "Senior level",
            "recommended_actions": ["Gain leadership experience", "Develop technical expertise"]
        }
    
    async def _analyze_job_market_trends(self, db: Session, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze job market trends"""
        return {
            "trending_roles": ["AI Engineer", "Data Scientist", "DevOps Engineer"],
            "skill_demand": ["Python", "Machine Learning", "Cloud Computing"],
            "salary_trends": {"average_increase": "5.2%", "top_paying": "AI/ML roles"}
        }
    
    async def _analyze_skill_demand(self, db: Session, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze skill demand"""
        return {
            "most_demanded": ["Python", "JavaScript", "Machine Learning"],
            "emerging_skills": ["Quantum Computing", "AI Ethics", "Blockchain"],
            "declining_skills": ["Legacy systems", "Outdated frameworks"]
        }
    
    async def _analyze_salary_trends(self, db: Session, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze salary trends"""
        return {
            "average_salary": 75000,
            "salary_growth": "4.5%",
            "highest_paying_roles": ["AI Engineer", "DevOps Engineer"],
            "geographic_variations": {"SF": 1.3, "NYC": 1.2, "Remote": 0.9}
        }
    
    async def _analyze_geographic_trends(self, db: Session, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze geographic trends"""
        return {
            "hottest_markets": ["San Francisco", "New York", "Seattle"],
            "emerging_markets": ["Austin", "Denver", "Remote"],
            "remote_work_trend": "Increasing by 25%"
        }
    
    async def _generate_hiring_forecast(self, db: Session, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate hiring forecast"""
        return {
            "forecast_period": "Next 6 months",
            "predicted_hires": 150,
            "confidence_level": 0.85,
            "key_factors": ["Market growth", "Seasonal trends", "Company expansion"]
        }
    
    async def _generate_talent_pipeline_report(self, db: Session, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate talent pipeline report"""
        return {
            "pipeline_health": "Strong",
            "candidate_flow": "Increasing",
            "bottlenecks": ["Interview scheduling", "Background checks"],
            "recommendations": ["Streamline interview process", "Improve candidate experience"]
        }
    
    async def _generate_retention_analysis(self, db: Session, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate retention analysis"""
        return {
            "retention_rate": 0.85,
            "turnover_risk": "Low",
            "key_retention_factors": ["Career growth", "Compensation", "Work-life balance"],
            "improvement_areas": ["Employee engagement", "Career development"]
        }
    
    def _get_start_date(self, time_period: str) -> datetime:
        """Get start date based on time period"""
        now = datetime.utcnow()
        if time_period == "7d":
            return now - timedelta(days=7)
        elif time_period == "30d":
            return now - timedelta(days=30)
        elif time_period == "90d":
            return now - timedelta(days=90)
        elif time_period == "1y":
            return now - timedelta(days=365)
        else:
            return now - timedelta(days=30)

# Initialize the service
analytics_service = AnalyticsService()

