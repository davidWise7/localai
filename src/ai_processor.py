# ai_processor.py - Fixed version with correct Gemini model
"""
LocalAI Assistant - Fixed AI Processor
Handles intelligent message classification, response generation, and business logic
"""

import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging

# AI/ML imports
import google.generativeai as genai
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MessageIntent:
    """Represents classified message intent"""
    intent: str  # 'booking', 'faq', 'complaint', 'general'
    confidence: float
    entities: Dict[str, Any]
    requires_escalation: bool = False

@dataclass
class AIResponse:
    """Represents AI-generated response"""
    text: str
    confidence: float
    intent: str
    escalate: bool = False
    booking_info: Optional[Dict] = None

class AIProcessor:
    """Main AI processing engine for customer messages"""
    
    def __init__(self):
        self.setup_gemini()
        self.intent_keywords = self._load_intent_keywords()
        self.escalation_triggers = self._load_escalation_triggers()
        
    def setup_gemini(self):
        """Initialize Google Gemini API with correct model name"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
            
        genai.configure(api_key=api_key)
        
        # Use the correct model name for current Gemini API
        try:
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("Gemini AI initialized successfully with gemini-1.5-flash")
        except Exception as e:
            # Fallback to older model names if needed
            try:
                self.model = genai.GenerativeModel('gemini-pro')
                logger.info("Gemini AI initialized successfully with gemini-pro")
            except Exception as e2:
                logger.error(f"Failed to initialize Gemini model: {str(e2)}")
                raise e2
    
    def _load_intent_keywords(self) -> Dict[str, List[str]]:
        """Load keyword patterns for intent classification"""
        return {
            'booking': [
                'appointment', 'book', 'schedule', 'reserve', 'available',
                'time', 'slot', 'tomorrow', 'today', 'next week',
                'haircut', 'massage', 'service', 'treatment', 'consultation'
            ],
            'faq': [
                'hours', 'open', 'closed', 'location', 'address', 'price',
                'cost', 'how much', 'phone', 'contact', 'parking',
                'payment', 'accept', 'credit card', 'cash'
            ],
            'complaint': [
                'disappointed', 'terrible', 'awful', 'worst', 'horrible',
                'refund', 'money back', 'unsatisfied', 'angry', 'upset',
                'manager', 'supervisor', 'complaint', 'problem'
            ],
            'cancellation': [
                'cancel', 'reschedule', 'change', 'move', 'different time'
            ]
        }
    
    def _load_escalation_triggers(self) -> List[str]:
        """Load patterns that should trigger human escalation"""
        return [
            'manager', 'supervisor', 'owner', 'complaint', 'legal',
            'lawsuit', 'attorney', 'refund', 'money back',
            'terrible', 'awful', 'worst', 'horrible', 'disgusting'
        ]
    
    async def classify_intent(self, message: str, business: Dict) -> MessageIntent:
        """
        Classify customer message intent using hybrid approach:
        1. Keyword matching for speed
        2. AI classification for accuracy
        """
        message_lower = message.lower()
        
        # Quick keyword-based classification
        keyword_scores = {}
        for intent, keywords in self.intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            if score > 0:
                keyword_scores[intent] = score / len(keywords)
        
        # If clear keyword match, use it
        if keyword_scores:
            top_intent = max(keyword_scores.keys(), key=lambda k: keyword_scores[k])
            if keyword_scores[top_intent] > 0.3:  # Strong keyword match
                return MessageIntent(
                    intent=top_intent,
                    confidence=min(keyword_scores[top_intent] * 2, 1.0),
                    entities=self._extract_entities(message, top_intent),
                    requires_escalation=self._check_escalation_needed(message)
                )
        
        # Use AI for ambiguous cases
        ai_classification = await self._ai_classify_intent(message, business)
        return ai_classification
    
    async def _ai_classify_intent(self, message: str, business: Dict) -> MessageIntent:
        """Use Gemini AI for intent classification"""
        try:
            prompt = f"""
            Classify this customer message for a {business.get('type', 'local business')}:
            
            Message: "{message}"
            
            Business context:
            - Type: {business.get('type', 'service business')}
            - Services: {', '.join(business.get('services', []))}
            - Hours: {business.get('hours', 'Standard business hours')}
            
            Classify the intent as one of:
            1. booking - wants to schedule/book an appointment or service
            2. faq - asking about hours, pricing, location, services, policies
            3. complaint - expressing dissatisfaction, wants refund, escalation
            4. cancellation - wants to cancel or reschedule existing booking
            5. general - casual conversation, thanks, or unclear intent
            
            Response format (JSON):
            {{
                "intent": "booking|faq|complaint|cancellation|general",
                "confidence": 0.0-1.0,
                "reason": "brief explanation",
                "escalate": true/false
            }}
            """
            
            response = await self._safe_generate_content(prompt)
            if response:
                result = json.loads(response.strip())
                
                return MessageIntent(
                    intent=result['intent'],
                    confidence=result['confidence'],
                    entities=self._extract_entities(message, result['intent']),
                    requires_escalation=result.get('escalate', False)
                )
            else:
                # Fallback if AI fails
                return self._fallback_intent_classification(message)
                
        except Exception as e:
            logger.error(f"AI classification error: {str(e)}")
            return self._fallback_intent_classification(message)
    
    async def _safe_generate_content(self, prompt: str) -> Optional[str]:
        """Safely generate content with error handling"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return None
    
    def _fallback_intent_classification(self, message: str) -> MessageIntent:
        """Fallback intent classification when AI fails"""
        message_lower = message.lower()
        
        # Simple keyword-based fallback
        if any(word in message_lower for word in ['book', 'appointment', 'schedule']):
            intent = 'booking'
        elif any(word in message_lower for word in ['hours', 'open', 'price', 'cost']):
            intent = 'faq'
        elif any(word in message_lower for word in ['terrible', 'awful', 'complaint']):
            intent = 'complaint'
        else:
            intent = 'general'
        
        return MessageIntent(
            intent=intent,
            confidence=0.6,  # Lower confidence for fallback
            entities={},
            requires_escalation=self._check_escalation_needed(message)
        )
    
    def _extract_entities(self, message: str, intent: str) -> Dict[str, Any]:
        """Extract relevant entities based on intent"""
        entities = {}
        
        if intent == 'booking':
            # Extract time/date references
            time_patterns = [
                r'(\d{1,2}):?(\d{2})?\s*(am|pm)',
                r'(tomorrow|today|monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
                r'(next week|this week)',
                r'(\d{1,2})/(\d{1,2})'
            ]
            
            for pattern in time_patterns:
                matches = re.findall(pattern, message.lower())
                if matches:
                    entities['time_references'] = matches
                    break
                    
            # Extract service mentions
            entities['services'] = [word for word in message.lower().split() 
                                  if word in ['haircut', 'massage', 'facial', 'manicure', 'pedicure']]
        
        elif intent == 'faq':
            # Extract question type
            if any(word in message.lower() for word in ['hour', 'open', 'close']):
                entities['question_type'] = 'hours'
            elif any(word in message.lower() for word in ['price', 'cost', 'much']):
                entities['question_type'] = 'pricing'
            elif any(word in message.lower() for word in ['location', 'address', 'where']):
                entities['question_type'] = 'location'
        
        return entities
    
    def _check_escalation_needed(self, message: str) -> bool:
        """Check if message needs human escalation"""
        message_lower = message.lower()
        return any(trigger in message_lower for trigger in self.escalation_triggers)
    
    async def generate_response(self, message: str, business: Dict, conversation: Dict = None) -> AIResponse:
        """
        Generate appropriate response based on message intent and business context
        """
        # Classify the message
        intent_result = await self.classify_intent(message, business)
        
        # Route to appropriate handler
        if intent_result.intent == 'booking':
            return await self._handle_booking_response(message, business, conversation, intent_result)
        elif intent_result.intent == 'faq':
            return await self._handle_faq_response(message, business, intent_result)
        elif intent_result.intent == 'complaint':
            return await self._handle_complaint_response(message, business, intent_result)
        elif intent_result.intent == 'cancellation':
            return await self._handle_cancellation_response(message, business, conversation, intent_result)
        else:
            return await self._handle_general_response(message, business, intent_result)
    
    async def _handle_booking_response(self, message: str, business: Dict, 
                                     conversation: Dict, intent: MessageIntent) -> AIResponse:
        """Handle booking-related messages"""
        try:
            prompt = f"""
            Generate a helpful booking response for this customer message:
            
            Customer: "{message}"
            
            Business: {business.get('name', 'Local Business')}
            Type: {business.get('type', 'service business')}
            Services: {', '.join(business.get('services', []))}
            Hours: {business.get('hours', 'Mon-Fri 9am-6pm')}
            
            Guidelines:
            - Be friendly and professional
            - If they specified a service and time, check if we need more info
            - If they're vague, ask for specific service and preferred time
            - Mention our services if they didn't specify
            - Keep response under 160 characters if possible for SMS
            - Include a call-to-action
            
            Response:
            """
            
            response_text = await self._safe_generate_content(prompt)
            if not response_text:
                response_text = f"I'd love to help you book an appointment! What service are you interested in and when would work for you?"
            
            # Check if we have enough info to attempt booking
            has_service = any(service in message.lower() 
                            for service in business.get('services', []))
            has_time = bool(intent.entities.get('time_references'))
            
            return AIResponse(
                text=response_text,
                confidence=intent.confidence,
                intent='booking',
                escalate=intent.requires_escalation,
                booking_info={
                    'has_service': has_service,
                    'has_time': has_time,
                    'needs_more_info': not (has_service and has_time)
                }
            )
            
        except Exception as e:
            logger.error(f"Booking response error: {str(e)}")
            return AIResponse(
                text=f"I'd love to help you book an appointment! What service are you interested in and when would work for you?",
                confidence=0.7,
                intent='booking'
            )
    
    async def _handle_faq_response(self, message: str, business: Dict, intent: MessageIntent) -> AIResponse:
        """Handle FAQ-related messages"""
        try:
            # Build FAQ context
            faq_context = f"""
            Business: {business.get('name', 'Local Business')}
            Type: {business.get('type', 'service business')}
            Address: {business.get('address', 'Contact us for location')}
            Phone: {business.get('phone', 'Contact us for phone')}
            Hours: {business.get('hours', 'Standard business hours')}
            Services: {', '.join(business.get('services', []))}
            Pricing: {business.get('pricing_info', 'Contact us for pricing')}
            Payment: {business.get('payment_methods', 'Cash and card accepted')}
            Parking: {business.get('parking_info', 'Street parking available')}
            """
            
            prompt = f"""
            Answer this customer question about our business:
            
            Question: "{message}"
            
            Business Information:
            {faq_context}
            
            Guidelines:
            - Answer directly and helpfully
            - Use the exact information provided
            - If info not available, say "Please call us for details"
            - Be friendly but concise
            - End with offer to help further
            
            Response:
            """
            
            response_text = await self._safe_generate_content(prompt)
            if not response_text:
                response_text = f"Thanks for your question! For the most accurate information, please call us at {business.get('phone', 'our main number')}."
            
            return AIResponse(
                text=response_text,
                confidence=intent.confidence,
                intent='faq',
                escalate=intent.requires_escalation
            )
            
        except Exception as e:
            logger.error(f"FAQ response error: {str(e)}")
            return AIResponse(
                text=f"Thanks for your question! For the most accurate information, please call us at {business.get('phone', 'our main number')}.",
                confidence=0.6,
                intent='faq'
            )
    
    async def _handle_complaint_response(self, message: str, business: Dict, intent: MessageIntent) -> AIResponse:
        """Handle complaint messages with empathy and escalation"""
        try:
            response_text = f"I'm sorry to hear about your experience. This is important to us and I want to make sure it's resolved properly. Someone from our team will contact you within the hour, or you can call us directly at {business.get('phone', 'our main number')}."
            
            return AIResponse(
                text=response_text,
                confidence=intent.confidence,
                intent='complaint',
                escalate=True  # Always escalate complaints
            )
            
        except Exception as e:
            logger.error(f"Complaint response error: {str(e)}")
            return AIResponse(
                text=f"I'm sorry to hear about your experience. Someone from our team will contact you within the hour.",
                confidence=0.8,
                intent='complaint',
                escalate=True
            )
    
    async def _handle_cancellation_response(self, message: str, business: Dict, 
                                          conversation: Dict, intent: MessageIntent) -> AIResponse:
        """Handle cancellation and rescheduling requests"""
        try:
            response_text = "I can help you with that! To cancel or reschedule your appointment, I'll need a few details. What's your name and when was your appointment scheduled?"
            
            return AIResponse(
                text=response_text,
                confidence=intent.confidence,
                intent='cancellation',
                escalate=False
            )
            
        except Exception as e:
            logger.error(f"Cancellation response error: {str(e)}")
            return AIResponse(
                text="I can help you with that! To cancel or reschedule your appointment, I'll need a few details.",
                confidence=0.7,
                intent='cancellation'
            )
    
    async def _handle_general_response(self, message: str, business: Dict, intent: MessageIntent) -> AIResponse:
        """Handle general conversation and unclear intents"""
        try:
            prompt = f"""
            Respond to this customer message professionally:
            
            Customer: "{message}"
            Business: {business.get('name', 'Local Business')}
            
            Guidelines:
            - Be friendly and helpful
            - Try to understand what they might need
            - Offer relevant services if appropriate
            - Ask clarifying questions if unclear
            - Keep response brief and engaging
            
            Response:
            """
            
            response_text = await self._safe_generate_content(prompt)
            if not response_text:
                response_text = f"Thanks for reaching out! How can I help you today? You can ask about our services, hours, or book an appointment."
            
            return AIResponse(
                text=response_text,
                confidence=intent.confidence,
                intent='general',
                escalate=intent.requires_escalation
            )
            
        except Exception as e:
            logger.error(f"General response error: {str(e)}")
            return AIResponse(
                text=f"Thanks for reaching out! How can I help you today?",
                confidence=0.6,
                intent='general'
            )