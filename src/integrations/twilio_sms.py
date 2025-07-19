# Twilio SMS Integration
"""
LocalAI Assistant - Twilio SMS Integration
Handles SMS sending and receiving via Twilio API
"""

import os
import logging
from typing import Dict, Any, Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

logger = logging.getLogger(__name__)

class TwilioSMS:
    """Twilio SMS integration for sending and receiving messages"""
    
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        
        if not all([self.account_sid, self.auth_token, self.phone_number]):
            logger.warning("Twilio credentials not found in environment variables")
            self.client = None
        else:
            self.client = Client(self.account_sid, self.auth_token)
            logger.info("Twilio client initialized successfully")
    
    async def send_sms(self, to_phone: str, from_phone: str, message: str) -> Dict[str, Any]:
        """Send SMS message via Twilio"""
        try:
            if not self.client:
                logger.error("Twilio client not initialized")
                return {"error": "Twilio not configured"}
            
            # Clean phone numbers
            to_phone = self.format_phone_number(to_phone)
            from_phone = self.format_phone_number(from_phone)
            
            # Send message
            message_obj = self.client.messages.create(
                body=message,
                from_=from_phone,
                to=to_phone
            )
            
            logger.info(f"SMS sent successfully: {message_obj.sid}")
            return {
                "success": True,
                "message_sid": message_obj.sid,
                "status": message_obj.status,
                "to": to_phone,
                "from": from_phone
            }
            
        except TwilioException as e:
            logger.error(f"Twilio error: {str(e)}")
            return {"error": f"Twilio error: {str(e)}"}
        except Exception as e:
            logger.error(f"SMS send error: {str(e)}")
            return {"error": f"Failed to send SMS: {str(e)}"}
    
    async def receive_sms(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming SMS webhook data"""
        try:
            return {
                "from_phone": webhook_data.get('From'),
                "to_phone": webhook_data.get('To'),
                "message": webhook_data.get('Body', ''),
                "message_sid": webhook_data.get('MessageSid'),
                "account_sid": webhook_data.get('AccountSid'),
                "timestamp": webhook_data.get('DateSent')
            }
        except Exception as e:
            logger.error(f"SMS receive error: {str(e)}")
            return {"error": str(e)}
    
    def format_phone_number(self, phone: str) -> str:
        """Format phone number for Twilio"""
        if not phone:
            return ""
        
        # Remove any non-numeric characters except +
        phone = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        # Add +1 if it's a US number without country code
        if phone.startswith('1') and len(phone) == 11:
            phone = '+' + phone
        elif len(phone) == 10:
            phone = '+1' + phone
        elif not phone.startswith('+'):
            phone = '+' + phone
        
        return phone
    
    def validate_webhook(self, webhook_data: Dict[str, Any]) -> bool:
        """Validate incoming webhook data"""
        try:
            required_fields = ['From', 'To', 'Body', 'MessageSid']
            return all(field in webhook_data for field in required_fields)
        except Exception as e:
            logger.error(f"Webhook validation error: {str(e)}")
            return False
    
    async def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """Get status of a sent message"""
        try:
            if not self.client:
                return {"error": "Twilio not configured"}
            
            message = self.client.messages(message_sid).fetch()
            return {
                "sid": message.sid,
                "status": message.status,
                "error_code": message.error_code,
                "error_message": message.error_message,
                "date_sent": message.date_sent,
                "date_updated": message.date_updated
            }
        except TwilioException as e:
            logger.error(f"Error getting message status: {str(e)}")
            return {"error": str(e)}
    
    async def send_bulk_sms(self, messages: list) -> Dict[str, Any]:
        """Send multiple SMS messages"""
        results = []
        successful = 0
        failed = 0
        
        for msg in messages:
            result = await self.send_sms(
                to_phone=msg.get('to'),
                from_phone=msg.get('from', self.phone_number),
                message=msg.get('message')
            )
            
            if result.get('success'):
                successful += 1
            else:
                failed += 1
            
            results.append(result)
        
        return {
            "total_messages": len(messages),
            "successful": successful,
            "failed": failed,
            "results": results
        }