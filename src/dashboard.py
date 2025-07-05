# Advanced Business Dashboard API
"""
LocalAI Assistant - Business Dashboard with Real-time Analytics
Provides comprehensive business intelligence and management interface
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import logging
from dataclasses import dataclass
import asyncio

from database import Database
from ai_processor import AIProcessor

logger = logging.getLogger(__name__)
dashboard_router = APIRouter()

# Pydantic models for API responses
class ConversationStats(BaseModel):
    total_conversations: int
    active_today: int
    response_time_avg: float
    satisfaction_score: float
    top_intents: List[Dict[str, Any]]

class BookingStats(BaseModel):
    total_bookings: int
    bookings_today: int
    booking_conversion_rate: float
    popular_services: List[Dict[str, Any]]
    upcoming_appointments: List[Dict[str, Any]]

class AIPerformance(BaseModel):
    accuracy_score: float
    escalation_rate: float
    most_common_failures: List[str]
    response_confidence_avg: float

class BusinessMetrics(BaseModel):
    conversations: ConversationStats
    bookings: BookingStats
    ai_performance: AIPerformance
    revenue_impact: Dict[str, float]

@dataclass
class DashboardData:
    """Complete dashboard data structure"""
    business_id: str
    metrics: BusinessMetrics
    recent_conversations: List[Dict]
    alerts: List[Dict]
    performance_trends: Dict[str, List[float]]

class BusinessDashboard:
    """Advanced business dashboard with real-time analytics"""
    
    def __init__(self):
        self.db = Database()
        self.ai = AIProcessor()
    
    async def get_dashboard_data(self, business_id: str, days: int = 30) -> DashboardData:
        """Get comprehensive dashboard data for a business"""
        try:
            # Get date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Fetch all data concurrently
            conversations_task = self.get_conversation_stats(business_id, start_date, end_date)
            bookings_task = self.get_booking_stats(business_id, start_date, end_date)
            ai_performance_task = self.get_ai_performance(business_id, start_date, end_date)
            recent_conversations_task = self.get_recent_conversations(business_id, limit=20)
            alerts_task = self.get_business_alerts(business_id)
            trends_task = self.get_performance_trends(business_id, days)
            
            # Execute all tasks
            conversations, bookings, ai_performance, recent_conversations, alerts, trends = await asyncio.gather(
                conversations_task,
                bookings_task,
                ai_performance_task,
                recent_conversations_task,
                alerts_task,
                trends_task
            )
            
            # Calculate revenue impact
            revenue_impact = await self.calculate_revenue_impact(business_id, bookings, conversations)
            
            metrics = BusinessMetrics(
                conversations=conversations,
                bookings=bookings,
                ai_performance=ai_performance,
                revenue_impact=revenue_impact
            )
            
            return DashboardData(
                business_id=business_id,
                metrics=metrics,
                recent_conversations=recent_conversations,
                alerts=alerts,
                performance_trends=trends
            )
            
        except Exception as e:
            logger.error(f"Dashboard data error: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to load dashboard data")
    
    async def get_conversation_stats(self, business_id: str, start_date: datetime, end_date: datetime) -> ConversationStats:
        """Get conversation statistics and metrics"""
        query = """
        SELECT 
            COUNT(*) as total_conversations,
            COUNT(CASE WHEN DATE(timestamp) = DATE('now') THEN 1 END) as active_today,
            AVG(response_time_seconds) as response_time_avg,
            AVG(satisfaction_rating) as satisfaction_score,
            intent,
            COUNT(intent) as intent_count
        FROM conversations 
        WHERE business_id = ? AND timestamp BETWEEN ? AND ?
        GROUP BY intent
        ORDER BY intent_count DESC
        """
        
        results = await self.db.execute_query(query, [business_id, start_date, end_date])
        
        if not results:
            return ConversationStats(
                total_conversations=0,
                active_today=0,
                response_time_avg=0.0,
                satisfaction_score=0.0,
                top_intents=[]
            )
        
        # Process results
        total_conversations = results[0]['total_conversations']
        active_today = results[0]['active_today']
        response_time_avg = results[0]['response_time_avg'] or 0.0
        satisfaction_score = results[0]['satisfaction_score'] or 0.0
        
        # Top intents
        top_intents = [
            {
                "intent": row['intent'],
                "count": row['intent_count'],
                "percentage": (row['intent_count'] / total_conversations * 100) if total_conversations > 0 else 0
            }
            for row in results[:5]  # Top 5 intents
        ]
        
        return ConversationStats(
            total_conversations=total_conversations,
            active_today=active_today,
            response_time_avg=response_time_avg,
            satisfaction_score=satisfaction_score,
            top_intents=top_intents
        )
    
    async def get_booking_stats(self, business_id: str, start_date: datetime, end_date: datetime) -> BookingStats:
        """Get booking statistics and conversion rates"""
        # Bookings query
        booking_query = """
        SELECT 
            COUNT(*) as total_bookings,
            COUNT(CASE WHEN DATE(created_at) = DATE('now') THEN 1 END) as bookings_today,
            service_type,
            COUNT(service_type) as service_count,
            scheduled_datetime,
            customer_name,
            status
        FROM bookings 
        WHERE business_id = ? AND created_at BETWEEN ? AND ?
        GROUP BY service_type
        ORDER BY service_count DESC
        """
        
        # Conversion rate query
        conversion_query = """
        SELECT 
            COUNT(CASE WHEN intent = 'booking' THEN 1 END) as booking_inquiries,
            COUNT(CASE WHEN intent = 'booking' AND booking_created = 1 THEN 1 END) as successful_bookings
        FROM conversations 
        WHERE business_id = ? AND timestamp BETWEEN ? AND ?
        """
        
        booking_results = await self.db.execute_query(booking_query, [business_id, start_date, end_date])
        conversion_results = await self.db.execute_query(conversion_query, [business_id, start_date, end_date])
        
        # Calculate conversion rate
        booking_conversion_rate = 0.0
        if conversion_results and conversion_results[0]['booking_inquiries'] > 0:
            booking_conversion_rate = (
                conversion_results[0]['successful_bookings'] / 
                conversion_results[0]['booking_inquiries'] * 100
            )
        
        # Popular services
        popular_services = []
        total_bookings = 0
        if booking_results:
            total_bookings = booking_results[0]['total_bookings']
            popular_services = [
                {
                    "service": row['service_type'],
                    "count": row['service_count'],
                    "percentage": (row['service_count'] / total_bookings * 100) if total_bookings > 0 else 0
                }
                for row in booking_results[:5]
            ]
        
        # Upcoming appointments
        upcoming_query = """
        SELECT customer_name, service_type, scheduled_datetime, status
        FROM bookings 
        WHERE business_id = ? AND scheduled_datetime > ? AND status = 'confirmed'
        ORDER BY scheduled_datetime ASC
        LIMIT 10
        """
        
        upcoming_results = await self.db.execute_query(upcoming_query, [business_id, datetime.utcnow()])
        upcoming_appointments = [
            {
                "customer": row['customer_name'],
                "service": row['service_type'],
                "datetime": row['scheduled_datetime'],
                "status": row['status']
            }
            for row in upcoming_results or []
        ]
        
        return BookingStats(
            total_bookings=total_bookings,
            bookings_today=booking_results[0]['bookings_today'] if booking_results else 0,
            booking_conversion_rate=booking_conversion_rate,
            popular_services=popular_services,
            upcoming_appointments=upcoming_appointments
        )
    
    async def get_ai_performance(self, business_id: str, start_date: datetime, end_date: datetime) -> AIPerformance:
        """Get AI performance metrics"""
        query = """
        SELECT 
            AVG(ai_confidence) as avg_confidence,
            COUNT(CASE WHEN escalated = 1 THEN 1 END) as escalated_count,
            COUNT(*) as total_count,
            intent,
            COUNT(CASE WHEN ai_confidence < 0.7 THEN 1 END) as low_confidence_count
        FROM conversations 
        WHERE business_id = ? AND timestamp BETWEEN ? AND ?
        GROUP BY intent
        """
        
        results = await self.db.execute_query(query, [business_id, start_date, end_date])
        
        if not results:
            return AIPerformance(
                accuracy_score=0.0,
                escalation_rate=0.0,
                most_common_failures=[],
                response_confidence_avg=0.0
            )
        
        # Calculate metrics
        total_conversations = sum(row['total_count'] for row in results)
        total_escalated = sum(row['escalated_count'] for row in results)
        total_low_confidence = sum(row['low_confidence_count'] for row in results)
        avg_confidence = sum(row['avg_confidence'] or 0 for row in results) / len(results)
        
        escalation_rate = (total_escalated / total_conversations * 100) if total_conversations > 0 else 0
        accuracy_score = ((total_conversations - total_low_confidence) / total_conversations * 100) if total_conversations > 0 else 0
        
        # Most common failure intents
        most_common_failures = [
            row['intent'] for row in results 
            if (row['low_confidence_count'] / row['total_count']) > 0.3
        ][:3]
        
        return AIPerformance(
            accuracy_score=accuracy_score,
            escalation_rate=escalation_rate,
            most_common_failures=most_common_failures,
            response_confidence_avg=avg_confidence
        )
    
    async def get_recent_conversations(self, business_id: str, limit: int = 20) -> List[Dict]:
        """Get recent conversations for review"""
        query = """
        SELECT 
            customer_phone,
            inbound_message,
            outbound_message,
            intent,
            ai_confidence,
            timestamp,
            escalated,
            platform
        FROM conversations 
        WHERE business_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
        """
        
        results = await self.db.execute_query(query, [business_id, limit])
        
        return [
            {
                "customer": row['customer_phone'][-4:],  # Last 4 digits for privacy
                "inbound": row['inbound_message'][:100] + "..." if len(row['inbound_message']) > 100 else row['inbound_message'],
                "outbound": row['outbound_message'][:100] + "..." if len(row['outbound_message']) > 100 else row['outbound_message'],
                "intent": row['intent'],
                "confidence": row['ai_confidence'],
                "timestamp": row['timestamp'],
                "escalated": row['escalated'],
                "platform": row['platform']
            }
            for row in results or []
        ]
    
    async def get_business_alerts(self, business_id: str) -> List[Dict]:
        """Get important alerts and notifications"""
        alerts = []
        
        # Check for high escalation rate
        escalation_query = """
        SELECT COUNT(*) as escalated_count, COUNT(*) as total_count
        FROM conversations 
        WHERE business_id = ? AND timestamp > datetime('now', '-24 hours')
        """
        
        escalation_result = await self.db.execute_query(escalation_query, [business_id])
        if escalation_result and escalation_result[0]['total_count'] > 0:
            escalation_rate = escalation_result[0]['escalated_count'] / escalation_result[0]['total_count']
            if escalation_rate > 0.3:  # More than 30% escalation rate
                alerts.append({
                    "type": "warning",
                    "message": f"High escalation rate: {escalation_rate:.1%} of conversations escalated in last 24h",
                    "action": "Review AI responses and training data"
                })
        
        # Check for low AI confidence
        confidence_query = """
        SELECT AVG(ai_confidence) as avg_confidence
        FROM conversations 
        WHERE business_id = ? AND timestamp > datetime('now', '-7 days')
        """
        
        confidence_result = await self.db.execute_query(confidence_query, [business_id])
        if confidence_result and confidence_result[0]['avg_confidence'] < 0.7:
            alerts.append({
                "type": "info",
                "message": f"AI confidence is low: {confidence_result[0]['avg_confidence']:.1%} average",
                "action": "Consider updating business knowledge base"
            })
        
        # Check for missed appointments
        missed_query = """
        SELECT COUNT(*) as missed_count
        FROM bookings 
        WHERE business_id = ? AND scheduled_datetime < datetime('now') AND status = 'confirmed'
        """
        
        missed_result = await self.db.execute_query(missed_query, [business_id])
        if missed_result and missed_result[0]['missed_count'] > 0:
            alerts.append({
                "type": "warning",
                "message": f"{missed_result[0]['missed_count']} appointments may have been missed",
                "action": "Update appointment statuses"
            })
        
        return alerts
    
    async def get_performance_trends(self, business_id: str, days: int) -> Dict[str, List[float]]:
        """Get performance trends over time"""
        query = """
        SELECT 
            DATE(timestamp) as date,
            COUNT(*) as daily_conversations,
            AVG(ai_confidence) as daily_confidence,
            COUNT(CASE WHEN escalated = 1 THEN 1 END) as daily_escalations,
            COUNT(CASE WHEN intent = 'booking' THEN 1 END) as daily_booking_inquiries
        FROM conversations 
        WHERE business_id = ? AND timestamp > datetime('now', '-{} days')
        GROUP BY DATE(timestamp)
        ORDER BY date ASC
        """.format(days)
        
        results = await self.db.execute_query(query, [business_id])
        
        trends = {
            "conversations": [],
            "confidence": [],
            "escalations": [],
            "booking_inquiries": []
        }
        
        for row in results or []:
            trends["conversations"].append(row['daily_conversations'])
            trends["confidence"].append(row['daily_confidence'] or 0)
            trends["escalations"].append(row['daily_escalations'])
            trends["booking_inquiries"].append(row['daily_booking_inquiries'])
        
        return trends
    
    async def calculate_revenue_impact(self, business_id: str, bookings: BookingStats, conversations: ConversationStats) -> Dict[str, float]:
        """Calculate estimated revenue impact"""
        # Get business pricing info
        business_query = """
        SELECT average_service_price, monthly_revenue_before_ai
        FROM businesses 
        WHERE id = ?
        """
        
        business_result = await self.db.execute_query(business_query, [business_id])
        avg_price = business_result[0]['average_service_price'] if business_result else 100
        
        # Calculate metrics
        estimated_monthly_revenue = bookings.total_bookings * avg_price
        time_saved_hours = conversations.total_conversations * 0.1  # 6 minutes per conversation
        cost_savings = time_saved_hours * 25  # $25/hour saved
        
        return {
            "estimated_monthly_revenue": estimated_monthly_revenue,
            "time_saved_hours": time_saved_hours,
            "cost_savings": cost_savings,
            "roi_percentage": ((estimated_monthly_revenue + cost_savings) / 200) * 100  # Assuming $200/month service cost
        }

# Initialize dashboard
dashboard = BusinessDashboard()

# API Routes
@dashboard_router.get("/dashboard/{business_id}", response_model=BusinessMetrics)
async def get_business_dashboard(
    business_id: str,
    days: int = Query(30, description="Number of days to analyze")
):
    """Get comprehensive business dashboard data"""
    try:
        dashboard_data = await dashboard.get_dashboard_data(business_id, days)
        return dashboard_data.metrics
    except Exception as e:
        logger.error(f"Dashboard API error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to load dashboard")

@dashboard_router.get("/dashboard/{business_id}/conversations")
async def get_recent_conversations(business_id: str, limit: int = Query(20, le=100)):
    """Get recent conversations for a business"""
    conversations = await dashboard.get_recent_conversations(business_id, limit)
    return {"conversations": conversations}

@dashboard_router.get("/dashboard/{business_id}/alerts")
async def get_business_alerts(business_id: str):
    """Get alerts and notifications for a business"""
    alerts = await dashboard.get_business_alerts(business_id)
    return {"alerts": alerts}

@dashboard_router.get("/dashboard/{business_id}/trends")
async def get_performance_trends(business_id: str, days: int = Query(30, le=365)):
    """Get performance trends over time"""
    trends = await dashboard.get_performance_trends(business_id, days)
    return {"trends": trends}

@dashboard_router.post("/dashboard/{business_id}/update-knowledge")
async def update_business_knowledge(business_id: str, knowledge_data: Dict[str, Any]):
    """Update business knowledge base"""
    try:
        # Update business FAQ and knowledge
        await dashboard.db.update_business_knowledge(business_id, knowledge_data)
        
        # Retrain AI if needed
        if knowledge_data.get('retrain_ai'):
            await dashboard.ai.retrain_business_model(business_id, knowledge_data)
        
        return {"status": "success", "message": "Knowledge base updated"}
    except Exception as e:
        logger.error(f"Knowledge update error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update knowledge")

@dashboard_router.get("/dashboard/{business_id}/export")
async def export_dashboard_data(business_id: str, format: str = Query("json", regex="^(json|csv)$")):
    """Export dashboard data"""
    try:
        dashboard_data = await dashboard.get_dashboard_data(business_id)
        
        if format == "csv":
            # Convert to CSV format
            import csv
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write conversations data
            writer.writerow(["Date", "Conversations", "Bookings", "Escalations", "AI Confidence"])
            for i, date in enumerate(dashboard_data.performance_trends.get("conversations", [])):
                writer.writerow([
                    f"Day {i+1}",
                    dashboard_data.performance_trends["conversations"][i],
                    dashboard_data.performance_trends["booking_inquiries"][i],
                    dashboard_data.performance_trends["escalations"][i],
                    dashboard_data.performance_trends["confidence"][i]
                ])
            
            return {"data": output.getvalue(), "format": "csv"}
        else:
            return {"data": dashboard_data.dict(), "format": "json"}
            
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to export data")