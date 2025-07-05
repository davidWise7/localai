# database.py - Fixed version with proper async handling
"""
LocalAI Assistant - Database Management
Handles business data, conversations, and analytics with proper async support
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Business:
    """Business data structure"""
    id: str
    name: str
    phone: str
    type: str
    services: List[str]
    hours: str
    address: str
    faq_data: Dict
    pricing_data: Dict

class Database:
    """Database management with proper async handling"""
    
    def __init__(self, db_path: str = "localai.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get database connection (synchronous)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize SQLite database with required tables"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Businesses table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS businesses (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    phone TEXT UNIQUE NOT NULL,
                    type TEXT DEFAULT 'service',
                    services TEXT,  -- JSON array
                    hours TEXT DEFAULT 'Mon-Fri 9am-6pm',
                    address TEXT,
                    faq_data TEXT,  -- JSON object
                    pricing_data TEXT,  -- JSON object
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    business_id TEXT,
                    customer_phone TEXT NOT NULL,
                    platform TEXT DEFAULT 'sms',
                    inbound_message TEXT NOT NULL,
                    outbound_message TEXT,
                    intent TEXT,
                    ai_confidence REAL,
                    escalated BOOLEAN DEFAULT 0,
                    response_time_ms INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (business_id) REFERENCES businesses (id)
                )
            """)
            
            # Bookings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    business_id TEXT,
                    customer_phone TEXT NOT NULL,
                    customer_name TEXT,
                    service TEXT NOT NULL,
                    scheduled_datetime TIMESTAMP,
                    duration_minutes INTEGER DEFAULT 60,
                    status TEXT DEFAULT 'pending',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (business_id) REFERENCES businesses (id)
                )
            """)
            
            # Analytics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    business_id TEXT,
                    metric_name TEXT NOT NULL,
                    metric_value REAL,
                    metadata TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (business_id) REFERENCES businesses (id)
                )
            """)
            
            conn.commit()
            conn.close()
            
            # Create demo business
            self.ensure_demo_business()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            raise
    
    def ensure_demo_business(self):
        """Create demo business for testing"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM businesses")
            count = cursor.fetchone()[0]
            
            if count == 0:
                demo_business = {
                    'id': 'demo_salon_001',
                    'name': 'Bella Hair Salon',
                    'phone': os.getenv('TWILIO_PHONE_NUMBER', '+1234567890'),
                    'type': 'hair_salon',
                    'services': json.dumps(['haircut', 'coloring', 'styling', 'treatment', 'blowout']),
                    'hours': 'Mon-Sat 9am-7pm, Closed Sunday',
                    'address': '123 Main Street, Anytown, ST 12345',
                    'faq_data': json.dumps({
                        'hours': 'We are open Monday through Saturday 9am-7pm, closed Sunday',
                        'parking': 'Free parking available in our rear lot',
                        'payment': 'We accept cash, all major credit cards, and mobile payments',
                        'cancellation': '24 hour notice required for cancellations to avoid fees',
                        'walk_ins': 'Walk-ins welcome when stylists are available'
                    }),
                    'pricing_data': json.dumps({
                        'haircut': '$45-65',
                        'coloring': '$85-150',
                        'styling': '$35-50',
                        'treatment': '$60-100',
                        'blowout': '$30-40'
                    })
                }
                
                cursor.execute("""
                    INSERT INTO businesses (id, name, phone, type, services, hours, address, faq_data, pricing_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    demo_business['id'], demo_business['name'], demo_business['phone'],
                    demo_business['type'], demo_business['services'], demo_business['hours'],
                    demo_business['address'], demo_business['faq_data'], demo_business['pricing_data']
                ))
                
                conn.commit()
                logger.info("Demo business created successfully")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Demo business creation error: {str(e)}")
    
    async def get_business_by_phone(self, phone: str) -> Optional[Dict]:
        """Get business by phone number"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM businesses WHERE phone = ?", (phone,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                business = dict(row)
                # Parse JSON fields safely
                try:
                    business['services'] = json.loads(business['services'] or '[]')
                except (json.JSONDecodeError, TypeError):
                    business['services'] = []
                
                try:
                    business['faq_data'] = json.loads(business['faq_data'] or '{}')
                except (json.JSONDecodeError, TypeError):
                    business['faq_data'] = {}
                
                try:
                    business['pricing_data'] = json.loads(business['pricing_data'] or '{}')
                except (json.JSONDecodeError, TypeError):
                    business['pricing_data'] = {}
                
                return business
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting business by phone: {str(e)}")
            return None
    
    async def log_conversation(self, conversation_data: Dict, response_time_ms: int = None) -> bool:
        """Log conversation with performance metrics"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO conversations 
                (business_id, customer_phone, platform, inbound_message, outbound_message, 
                 intent, ai_confidence, escalated, response_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conversation_data.get('business_id'),
                conversation_data.get('customer_phone'),
                conversation_data.get('platform', 'sms'),
                conversation_data.get('inbound_message'),
                conversation_data.get('outbound_message'),
                conversation_data.get('intent'),
                conversation_data.get('ai_confidence', 0.0),
                conversation_data.get('escalated', False),
                response_time_ms
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Conversation logging error: {str(e)}")
            return False
    
    async def get_conversation_stats(self, business_id: str, days: int = 7) -> Dict:
        """Get conversation statistics"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_conversations,
                    COUNT(CASE WHEN DATE(timestamp) = DATE('now') THEN 1 END) as today_count,
                    AVG(response_time_ms) as avg_response_time,
                    AVG(ai_confidence) as avg_confidence,
                    COUNT(CASE WHEN escalated = 1 THEN 1 END) as escalated_count
                FROM conversations 
                WHERE business_id = ? AND timestamp > datetime('now', '-{} days')
            """.format(days), (business_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'total_conversations': result['total_conversations'] or 0,
                    'today_count': result['today_count'] or 0,
                    'avg_response_time': result['avg_response_time'] or 0,
                    'avg_confidence': result['avg_confidence'] or 0,
                    'escalated_count': result['escalated_count'] or 0
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Stats query error: {str(e)}")
            return {}
    
    async def get_recent_conversations(self, business_id: str, limit: int = 20) -> List[Dict]:
        """Get recent conversations"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
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
            """, (business_id, limit))
            
            results = cursor.fetchall()
            conn.close()
            
            conversations = []
            for row in results:
                conversations.append({
                    "customer": row['customer_phone'][-4:] if row['customer_phone'] else "Unknown",
                    "inbound": (row['inbound_message'][:100] + "...") if len(row['inbound_message'] or "") > 100 else row['inbound_message'],
                    "outbound": (row['outbound_message'][:100] + "...") if len(row['outbound_message'] or "") > 100 else row['outbound_message'],
                    "intent": row['intent'],
                    "confidence": row['ai_confidence'],
                    "timestamp": row['timestamp'],
                    "escalated": bool(row['escalated']),
                    "platform": row['platform']
                })
            
            return conversations
            
        except Exception as e:
            logger.error(f"Recent conversations query error: {str(e)}")
            return []
    
    async def create_booking(self, booking_data: Dict) -> Optional[int]:
        """Create a new booking"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO bookings 
                (business_id, customer_phone, customer_name, service, 
                 scheduled_datetime, duration_minutes, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                booking_data.get('business_id'),
                booking_data.get('customer_phone'),
                booking_data.get('customer_name'),
                booking_data.get('service'),
                booking_data.get('scheduled_datetime'),
                booking_data.get('duration_minutes', 60),
                booking_data.get('status', 'pending'),
                booking_data.get('notes', '')
            ))
            
            booking_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Booking created successfully: {booking_id}")
            return booking_id
            
        except Exception as e:
            logger.error(f"Booking creation error: {str(e)}")
            return None
    
    async def get_bookings_for_business(self, business_id: str, limit: int = 50) -> List[Dict]:
        """Get bookings for a business"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    id, customer_phone, customer_name, service,
                    scheduled_datetime, duration_minutes, status, notes,
                    created_at
                FROM bookings 
                WHERE business_id = ? 
                ORDER BY scheduled_datetime DESC 
                LIMIT ?
            """, (business_id, limit))
            
            results = cursor.fetchall()
            conn.close()
            
            bookings = []
            for row in results:
                bookings.append({
                    "id": row['id'],
                    "customer_phone": row['customer_phone'],
                    "customer_name": row['customer_name'],
                    "service": row['service'],
                    "scheduled_datetime": row['scheduled_datetime'],
                    "duration_minutes": row['duration_minutes'],
                    "status": row['status'],
                    "notes": row['notes'],
                    "created_at": row['created_at']
                })
            
            return bookings
            
        except Exception as e:
            logger.error(f"Get bookings error: {str(e)}")
            return []
    
    async def update_booking_status(self, booking_id: int, status: str) -> bool:
        """Update booking status"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE bookings 
                SET status = ?
                WHERE id = ?
            """, (status, booking_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Booking {booking_id} status updated to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Update booking status error: {str(e)}")
            return False
    
    async def log_analytics(self, business_id: str, metric_name: str, metric_value: float, metadata: Dict = None) -> bool:
        """Log analytics data"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO analytics 
                (business_id, metric_name, metric_value, metadata)
                VALUES (?, ?, ?, ?)
            """, (
                business_id,
                metric_name,
                metric_value,
                json.dumps(metadata) if metadata else None
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Analytics logging error: {str(e)}")
            return False
    
    async def get_analytics(self, business_id: str, metric_name: str = None, days: int = 30) -> List[Dict]:
        """Get analytics data"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if metric_name:
                cursor.execute("""
                    SELECT metric_name, metric_value, metadata, timestamp
                    FROM analytics 
                    WHERE business_id = ? AND metric_name = ?
                    AND timestamp > datetime('now', '-{} days')
                    ORDER BY timestamp DESC
                """.format(days), (business_id, metric_name))
            else:
                cursor.execute("""
                    SELECT metric_name, metric_value, metadata, timestamp
                    FROM analytics 
                    WHERE business_id = ?
                    AND timestamp > datetime('now', '-{} days')
                    ORDER BY timestamp DESC
                """.format(days), (business_id,))
            
            results = cursor.fetchall()
            conn.close()
            
            analytics = []
            for row in results:
                analytics.append({
                    "metric_name": row['metric_name'],
                    "metric_value": row['metric_value'],
                    "metadata": json.loads(row['metadata']) if row['metadata'] else None,
                    "timestamp": row['timestamp']
                })
            
            return analytics
            
        except Exception as e:
            logger.error(f"Get analytics error: {str(e)}")
            return []