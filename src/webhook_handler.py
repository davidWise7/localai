# Webhook Handler for SMS and Facebook

"""
LocalAI Assistant - Advanced Webhook Handler
Processes incoming SMS and Facebook messages with AI responses
"""

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

from ai_processor import AIProcessor
from database import Database
from integrations.twilio_sms import TwilioSMS
from integrations.facebook_api import FacebookAPI

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
webhook_router = APIRouter()
ai_processor = AIProcessor()
db = Database()
twilio = TwilioSMS()
facebook = FacebookAPI()

class MessageProcessor:
    """Handles message processing pipeline"""
    
    def __init__(self):
        self.ai = ai_processor
        self.db = db
    
    async def process_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main message processing pipeline
        1. Extract message info
        2. Check for existing conversation context
        3. Generate AI response
        4. Log interaction
        5. Send response
        """
        try:
            # Extract message details
            customer_phone = message_data.get('from')
            business_phone = message_data.get('to')
            message_text = message_data.get('body', '').strip()
            platform = message_data.get('platform', 'sms')
            
            logger.info(f"Processing {platform} message from {customer_phone}")
            
            # Get business context
            business = await self.db.get_business_by_phone(business_phone)
            if not business:
                logger.warning(f"No business found for phone {business_phone}")
                return {"error": "Business not configured"}
            
            # Get conversation context
            conversation = await self.db.get_conversation(customer_phone, business['id'])
            
            # Classify message intent
            intent = await self.ai.classify_intent(message_text, business)
            logger.info(f"Message intent classified as: {intent}")
            
            # Generate appropriate response
            if intent == 'booking':
                response = await self.handle_booking_request(message_text, business, conversation)
            elif intent == 'faq':
                response = await self.handle_faq_request(message_text, business)
            elif intent == 'complaint':
                response = await self.handle_complaint(message_text, business, customer_phone)
            else:
                response = await self.ai.generate_response(message_text, business, conversation)
            
            # Log the interaction
            await self.db.log_interaction({
                'business_id': business['id'],
                'customer_phone': customer_phone,
                'platform': platform,
                'inbound_message': message_text,
                'outbound_message': response['text'],
                'intent': intent,
                'confidence': response.get('confidence', 0.0),
                'timestamp': datetime.utcnow()
            })
            
            return {
                'response_text': response['text'],
                'intent': intent,
                'escalate': response.get('escalate', False),
                'booking_created': response.get('booking_id') is not None
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {"error": str(e)}
    
    async def handle_booking_request(self, message: str, business: Dict, conversation: Dict) -> Dict:
        """Handle appointment booking requests"""
        try:
            # Extract booking details from message
            booking_details = await self.ai.extract_booking_info(message, conversation)
            
            if not booking_details.get('service') or not booking_details.get('datetime'):
                # Need more information
                return {
                    'text': f"I'd be happy to help you book an appointment! I need a bit more info:\n\n"
                           f"• What service would you like? ({', '.join(business.get('services', []))})\n"
                           f"• What day and time work for you?\n\n"
                           f"Example: 'Haircut on Friday at 2pm'",
                    'escalate': False
                }
            
            # Check availability
            from integrations.calendar_api import CalendarAPI
            calendar = CalendarAPI(business['calendar_id'])
            
            available_slots = await calendar.check_availability(
                booking_details['datetime'],
                booking_details.get('duration', 60)
            )
            
            if available_slots:
                # Book the appointment
                booking_id = await calendar.create_booking({
                    'service': booking_details['service'],
                    'datetime': booking_details['datetime'],
                    'duration': booking_details.get('duration', 60),
                    'customer_phone': conversation['customer_phone'],
                    'customer_name': booking_details.get('name', 'Customer'),
                    'notes': booking_details.get('notes', '')
                })
                
                return {
                    'text': f"✅ Perfect! I've booked your {booking_details['service']} for "
                           f"{booking_details['datetime'].strftime('%A, %B %d at %I:%M %p')}.\n\n"
                           f"📍 {business['address']}\n"
                           f"📞 {business['phone']}\n\n"
                           f"You'll get a reminder 24 hours before. Reply CANCEL if you need to reschedule.",
                    'escalate': False,
                    'booking_id': booking_id
                }
            else:
                # Suggest alternative times
                alternative_times = await calendar.suggest_alternatives(
                    booking_details['datetime'],
                    booking_details.get('duration', 60)
                )
                
                suggestions = "\n".join([f"• {time.strftime('%A, %B %d at %I:%M %p')}" 
                                       for time in alternative_times[:3]])
                
                return {
                    'text': f"That time isn't available, but I have these options:\n\n{suggestions}\n\n"
                           f"Which time works for you?",
                    'escalate': False
                }
                
        except Exception as e:
            logger.error(f"Booking error: {str(e)}")
            return {
                'text': "I'm having trouble with bookings right now. Let me connect you with someone who can help!",
                'escalate': True
            }
    
    async def handle_faq_request(self, message: str, business: Dict) -> Dict:
        """Handle frequently asked questions"""
        faq_response = await self.ai.answer_faq(message, business['faq_data'])
        
        if faq_response['confidence'] > 0.8:
            return {
                'text': faq_response['answer'],
                'escalate': False,
                'confidence': faq_response['confidence']
            }
        else:
            return {
                'text': f"I'm not completely sure about that. Here's what I think:\n\n"
                       f"{faq_response['answer']}\n\n"
                       f"For the most accurate info, you can call us at {business['phone']} "
                       f"or I can have someone get back to you.",
                'escalate': False,
                'confidence': faq_response['confidence']
            }
    
    async def handle_complaint(self, message: str, business: Dict, customer_phone: str) -> Dict:
        """Handle customer complaints with priority escalation"""
        # Analyze sentiment and urgency
        analysis = await self.ai.analyze_complaint(message)
        
        # Always escalate complaints to human
        await self.db.create_priority_alert({
            'business_id': business['id'],
            'customer_phone': customer_phone,
            'message': message,
            'severity': analysis['severity'],
            'sentiment_score': analysis['sentiment'],
            'requires_immediate_attention': analysis['urgent']
        })
        
        return {
            'text': f"I understand you're having an issue, and I want to make sure "
                   f"this gets resolved quickly. I've notified our manager and "
                   f"someone will contact you within the next hour.\n\n"
                   f"In the meantime, you can also call us directly at {business['phone']}.",
            'escalate': True
        }

# Initialize message processor
message_processor = MessageProcessor()

@webhook_router.post("/webhook/sms")
async def handle_sms_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle incoming SMS messages from Twilio
    """
    try:
        # Parse Twilio webhook data
        form_data = await request.form()
        message_data = {
            'from': form_data.get('From'),
            'to': form_data.get('To'),
            'body': form_data.get('Body'),
            'platform': 'sms',
            'message_sid': form_data.get('MessageSid')
        }
        
        logger.info(f"SMS webhook received: {message_data['from']} -> {message_data['to']}")
        
        # Process message in background
        background_tasks.add_task(process_and_respond_sms, message_data)
        
        # Return empty response to Twilio (required)
        return PlainTextResponse("", status_code=200)
        
    except Exception as e:
        logger.error(f"SMS webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@webhook_router.post("/webhook/facebook")
async def handle_facebook_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle incoming Facebook Messenger and page messages
    """
    try:
        data = await request.json()
        
        # Verify Facebook webhook
        if not facebook.verify_webhook(data):
            raise HTTPException(status_code=403, detail="Invalid webhook signature")
        
        # Process each messaging event
        for entry in data.get('entry', []):
            for message_event in entry.get('messaging', []):
                if 'message' in message_event:
                    message_data = {
                        'from': message_event['sender']['id'],
                        'to': message_event['recipient']['id'],
                        'body': message_event['message'].get('text', ''),
                        'platform': 'facebook',
                        'message_id': message_event['message']['mid']
                    }
                    
                    background_tasks.add_task(process_and_respond_facebook, message_data)
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Facebook webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@webhook_router.get("/webhook/facebook")
async def verify_facebook_webhook(request: Request):
    """
    Verify Facebook webhook subscription
    """
    hub_mode = request.query_params.get('hub.mode')
    hub_challenge = request.query_params.get('hub.challenge')
    hub_verify_token = request.query_params.get('hub.verify_token')
    
    if hub_mode == 'subscribe' and facebook.verify_token(hub_verify_token):
        logger.info("Facebook webhook verified successfully")
        return PlainTextResponse(hub_challenge)
    else:
        raise HTTPException(status_code=403, detail="Invalid verification token")

async def process_and_respond_sms(message_data: Dict[str, Any]):
    """
    Background task to process SMS and send response
    """
    try:
        # Process the message
        result = await message_processor.process_message(message_data)
        
        if 'error' not in result:
            # Send SMS response
            await twilio.send_sms(
                to_phone=message_data['from'],
                from_phone=message_data['to'],
                message=result['response_text']
            )
            
            # If escalation needed, notify business owner
            if result.get('escalate'):
                await notify_business_owner(message_data, result)
                
        logger.info(f"SMS response sent to {message_data['from']}")
        
    except Exception as e:
        logger.error(f"Error in SMS processing: {str(e)}")

async def process_and_respond_facebook(message_data: Dict[str, Any]):
    """
    Background task to process Facebook message and send response
    """