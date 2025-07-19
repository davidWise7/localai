# AI Processing Logic with Bilingual Support
"""
LocalAI Assistant - Enhanced AI Processor with French/English Support
Handles intelligent message classification, response generation, and business logic
Perfect for Quebec/bilingual businesses
"""

import os
import json
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

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
    """Main AI processing engine with bilingual support"""
    
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
        """Load keyword patterns for intent classification (bilingual)"""
        return {
            'booking': [
                # English
                'appointment', 'book', 'schedule', 'reserve', 'available',
                'time', 'slot', 'tomorrow', 'today', 'next week',
                'haircut', 'massage', 'service', 'treatment', 'consultation',
                # French
                'rendez-vous', 'réserver', 'prendre', 'disponible', 'horaire',
                'coupe', 'cheveux', 'service', 'traitement', 'consultation',
                'demain', 'aujourd\'hui', 'semaine prochaine'
            ],
            'faq': [
                # English
                'hours', 'open', 'closed', 'location', 'address', 'price',
                'cost', 'how much', 'phone', 'contact', 'parking',
                'payment', 'accept', 'credit card', 'cash',
                # French
                'heures', 'ouvert', 'fermé', 'adresse', 'où', 'prix',
                'coût', 'combien', 'téléphone', 'contact', 'stationnement',
                'paiement', 'acceptez', 'carte', 'comptant'
            ],
            'complaint': [
                # English
                'disappointed', 'terrible', 'awful', 'worst', 'horrible',
                'refund', 'money back', 'unsatisfied', 'angry', 'upset',
                'manager', 'supervisor', 'complaint', 'problem',
                # French
                'déçu', 'terrible', 'affreux', 'pire', 'horrible',
                'remboursement', 'argent', 'insatisfait', 'fâché', 'contrarié',
                'gérant', 'superviseur', 'plainte', 'problème'
            ],
            'cancellation': [
                # English
                'cancel', 'reschedule', 'change', 'move', 'different time',
                # French
                'annuler', 'reporter', 'changer', 'déplacer', 'autre heure'
            ]
        }
    
    def _load_escalation_triggers(self) -> List[str]:
        """Load patterns that should trigger human escalation (bilingual)"""
        return [
            # English
            'manager', 'supervisor', 'owner', 'complaint', 'legal',
            'lawsuit', 'attorney', 'refund', 'money back',
            'terrible', 'awful', 'worst', 'horrible', 'disgusting',
            # French
            'gérant', 'superviseur', 'propriétaire', 'plainte', 'légal',
            'poursuites', 'avocat', 'remboursement', 'argent',
            'terrible', 'affreux', 'pire', 'horrible', 'dégoûtant'
        ]
    
    def detect_language(self, message: str) -> str:
        """Detect if message is in French or English"""
        message_lower = message.lower()
        
        # French indicators (more comprehensive)
        french_words = [
            # Greetings & politeness
            'bonjour', 'bonsoir', 'salut', 'merci', 'svp', 's\'il vous plaît',
            # Questions words
            'comment', 'quand', 'où', 'pourquoi', 'combien', 'quel', 'quelle',
            # Common words
            'oui', 'non', 'je', 'nous', 'vous', 'ils', 'elles', 'le', 'la', 'les',
            'un', 'une', 'des', 'du', 'de', 'et', 'ou', 'mais', 'avec', 'sans',
            # Business specific
            'heures', 'ouvert', 'fermé', 'prix', 'coût', 'rendez-vous',
            'coupe', 'cheveux', 'salon', 'adresse', 'téléphone',
            # Action words
            'j\'aimerais', 'j\'ai besoin', 'pouvez-vous', 'êtes-vous',
            'voudrais', 'cherche', 'veux', 'avoir', 'être'
        ]
        
        # Count French words
        french_count = sum(1 for word in french_words if word in message_lower)
        
        # If 2+ French words, respond in French
        return 'french' if french_count >= 2 else 'english'
    
    async def classify_intent(self, message: str, business: Dict) -> MessageIntent:
        """Classify customer message intent using hybrid approach (bilingual)"""
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
            if keyword_scores[top_intent] > 0.2:  # Lower threshold for bilingual
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
        """Use Gemini AI for intent classification (bilingual)"""
        try:
            # Detect language for appropriate prompt
            language = self.detect_language(message)
            
            # Build variables safely outside f-strings
            business_type = business.get('type', 'salon de coiffure')
            services_list = ', '.join(business.get('services', []))
            business_hours = business.get('hours', "Heures d'affaires standard")
            
            if language == 'french':
                prompt = f"""
                Classifiez ce message client pour un {business_type}:
                
                Message: "{message}"
                
                Contexte du commerce:
                - Type: {business_type}
                - Services: {services_list}
                - Heures: {business_hours}
                
                Classifiez l'intention comme une de:
                1. booking - veut prendre/réserver un rendez-vous ou service
                2. faq - demande sur heures, prix, lieu, services, politiques
                3. complaint - exprime insatisfaction, veut remboursement, escalade
                4. cancellation - veut annuler ou reporter un rendez-vous existant
                5. general - conversation casual, remerciements, ou intention peu claire
                
                Format de réponse (JSON):
                {{
                    "intent": "booking|faq|complaint|cancellation|general",
                    "confidence": 0.0-1.0,
                    "reason": "explication brève",
                    "escalate": true/false
                }}
                """
            else:
                # Build English variables safely
                business_type_en = business.get('type', 'local business')
                business_hours_en = business.get('hours', 'Standard business hours')
                
                prompt = f"""
                Classify this customer message for a {business_type_en}:
                
                Message: "{message}"
                
                Business context:
                - Type: {business_type_en}
                - Services: {services_list}
                - Hours: {business_hours_en}
                
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
            
            response_text = await self._safe_generate_content(prompt)
            if response_text:
                result = json.loads(response_text.strip())
                
                return MessageIntent(
                    intent=result['intent'],
                    confidence=result['confidence'],
                    entities=self._extract_entities(message, result['intent']),
                    requires_escalation=result.get('escalate', False)
                )
            else:
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
        """Fallback intent classification when AI fails (bilingual)"""
        message_lower = message.lower()
        
        # Bilingual keyword-based fallback
        if any(word in message_lower for word in ['book', 'appointment', 'schedule', 'rendez-vous', 'réserver']):
            intent = 'booking'
        elif any(word in message_lower for word in ['hours', 'open', 'price', 'cost', 'heures', 'ouvert', 'prix']):
            intent = 'faq'
        elif any(word in message_lower for word in ['terrible', 'awful', 'complaint', 'affreux', 'plainte']):
            intent = 'complaint'
        else:
            intent = 'general'
        
        return MessageIntent(
            intent=intent,
            confidence=0.6,
            entities={},
            requires_escalation=self._check_escalation_needed(message)
        )
    
    def _extract_entities(self, message: str, intent: str) -> Dict[str, Any]:
        """Extract relevant entities based on intent (bilingual)"""
        entities = {}
        
        if intent == 'booking':
            # Extract time/date references (bilingual)
            time_patterns = [
                r'(\d{1,2}):?(\d{2})?\s*(am|pm|h)',
                r'(tomorrow|today|monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
                r'(demain|aujourd\'hui|lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)',
                r'(next week|this week|semaine prochaine|cette semaine)',
                r'(\d{1,2})/(\d{1,2})'
            ]
            
            for pattern in time_patterns:
                matches = re.findall(pattern, message.lower())
                if matches:
                    entities['time_references'] = matches
                    break
                    
            # Extract service mentions (bilingual)
            services = ['haircut', 'massage', 'facial', 'manicure', 'pedicure',
                       'coupe', 'cheveux', 'massage', 'facial', 'manucure', 'pédicure']
            entities['services'] = [word for word in message.lower().split() if word in services]
        
        elif intent == 'faq':
            # Extract question type (bilingual)
            if any(word in message.lower() for word in ['hour', 'open', 'close', 'heure', 'ouvert', 'fermé']):
                entities['question_type'] = 'hours'
            elif any(word in message.lower() for word in ['price', 'cost', 'much', 'prix', 'coût', 'combien']):
                entities['question_type'] = 'pricing'
            elif any(word in message.lower() for word in ['location', 'address', 'where', 'adresse', 'où']):
                entities['question_type'] = 'location'
        
        return entities
    
    def _check_escalation_needed(self, message: str) -> bool:
        """Check if message needs human escalation (bilingual)"""
        message_lower = message.lower()
        return any(trigger in message_lower for trigger in self.escalation_triggers)
    
    async def generate_response(self, message: str, business: Dict, conversation: Dict = None) -> AIResponse:
        """Generate response with bilingual support"""
        
        # Detect customer's language
        language = self.detect_language(message)
        
        # Classify the message intent
        intent_result = await self.classify_intent(message, business)
        
        # Generate response based on language
        if language == 'french':
            return await self._generate_french_response(message, business, intent_result)
        else:
            return await self._generate_english_response(message, business, intent_result)
    
    async def _generate_french_response(self, message: str, business: Dict, intent: MessageIntent) -> AIResponse:
        """Generate French responses"""
        try:
            if intent.intent == 'booking':
                prompt = f"""
                Répondre en français à ce client qui veut prendre rendez-vous:
                
                Client: "{message}"
                
                Salon: {business.get('name', 'Salon de Coiffure')}
                Services: {', '.join(business.get('services', []))}
                Heures: {business.get('hours', 'Lun-Ven 9h-18h')}
                
                Instructions:
                - Répondre en français seulement
                - Être amical et professionnel
                - Si service et heure mentionnés, confirmer
                - Sinon demander quel service et quel moment
                - Garder sous 160 caractères pour SMS
                
                Réponse:
                """
            
            elif intent.intent == 'faq':
                if 'heure' in message.lower() or 'ouvert' in message.lower():
                    prompt = f"""
                    Répondre à cette question sur les heures d'ouverture:
                    
                    Question: "{message}"
                    Heures: {business.get('hours', 'Lun-Sam 9h-19h, Fermé Dimanche')}
                    
                    Répondre en français, être clair et utile.
                    Garder sous 160 caractères.
                    """
                
                elif 'prix' in message.lower() or 'coût' in message.lower() or 'combien' in message.lower():
                    prompt = f"""
                    Répondre à cette question sur les prix:
                    
                    Question: "{message}"
                    Services et prix: Coupe 45$-65$, Coloration 85$-150$, Coiffage 35$-50$
                    
                    Répondre en français, donner les prix pertinents.
                    Garder sous 160 caractères.
                    """
                
                elif 'adresse' in message.lower() or 'où' in message.lower():
                    prompt = f"""
                    Répondre à cette question sur l'adresse:
                    
                    Question: "{message}"
                    Adresse: {business.get('address', '123 rue Principale')}
                    
                    Répondre en français avec l'adresse et info de stationnement.
                    Garder sous 160 caractères.
                    """
                
                else:
                    prompt = f"""
                    Répondre à cette question en français:
                    
                    Question: "{message}"
                    Salon: {business.get('name')}
                    Adresse: {business.get('address')}
                    Heures: {business.get('hours')}
                    
                    Être utile et professionnel en français.
                    Garder sous 160 caractères.
                    """
            
            elif intent.intent == 'complaint':
                prompt = f"""
                Répondre avec empathie à cette plainte en français:
                
                Message: "{message}"
                Salon: {business.get('name')}
                
                Instructions:
                - Répondre en français seulement
                - Être empathique et professionnel
                - S'excuser appropriément
                - Offrir contact direct pour résoudre
                - Garder sous 160 caractères
                
                Réponse:
                """
            
            else:
                prompt = f"""
                Répondre à ce message client en français:
                
                Message: "{message}"
                Salon: {business.get('name')}
                
                Instructions:
                - Répondre en français seulement
                - Être amical et professionnel
                - Demander comment aider
                - Garder sous 160 caractères
                
                Réponse:
                """
            
            response_text = await self._safe_generate_content(prompt)
            if not response_text:
                response_text = "Merci de nous contacter! Comment puis-je vous aider aujourd'hui?"
            
            return AIResponse(
                text=response_text,
                confidence=intent.confidence,
                intent=intent.intent,
                escalate=intent.requires_escalation or intent.intent == 'complaint'
            )
            
        except Exception as e:
            logger.error(f"French response error: {str(e)}")
            return AIResponse(
                text="Merci de votre message! Quelqu'un de notre équipe vous contactera bientôt.",
                confidence=0.6,
                intent=intent.intent
            )
    
    async def _generate_english_response(self, message: str, business: Dict, intent: MessageIntent) -> AIResponse:
        """Generate English responses (existing logic enhanced)"""
        try:
            if intent.intent == 'booking':
                prompt = f"""
                Generate a helpful booking response for this customer message:
                
                Customer: "{message}"
                
                Business: {business.get('name', 'Local Business')}
                Type: {business.get('type', 'service business')}
                Services: {', '.join(business.get('services', []))}
                Hours: {business.get('hours', 'Mon-Fri 9am-6pm')}
                
                Guidelines:
                - Be friendly and professional
                - If they specified a service and time, acknowledge it
                - If they're vague, ask for specific service and preferred time
                - Mention our services if they didn't specify
                - Keep response under 160 characters for SMS
                - Include a call-to-action
                
                Response:
                """
            
            elif intent.intent == 'faq':
                faq_context = f"""
                Business: {business.get('name', 'Local Business')}
                Type: {business.get('type', 'service business')}
                Address: {business.get('address', 'Contact us for location')}
                Hours: {business.get('hours', 'Standard business hours')}
                Services: {', '.join(business.get('services', []))}
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
                - Keep under 160 characters
                
                Response:
                """
            
            elif intent.intent == 'complaint':
                prompt = f"""
                Respond empathetically to this customer complaint:
                
                Customer: "{message}"
                Business: {business.get('name')}
                
                Guidelines:
                - Acknowledge their concern genuinely
                - Apologize appropriately 
                - Explain next steps clearly
                - Offer direct contact
                - Professional but warm tone
                - Keep under 160 characters
                
                Response:
                """
            
            else:
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
                - Keep under 160 characters
                
                Response:
                """
            
            response_text = await self._safe_generate_content(prompt)
            if not response_text:
                response_text = f"Thanks for reaching out! How can I help you today?"
            
            return AIResponse(
                text=response_text,
                confidence=intent.confidence,
                intent=intent.intent,
                escalate=intent.requires_escalation or intent.intent == 'complaint'
            )
            
        except Exception as e:
            logger.error(f"English response error: {str(e)}")
            return AIResponse(
                text=f"Thanks for your message! Someone from our team will get back to you shortly.",
                confidence=0.6,
                intent=intent.intent
            )