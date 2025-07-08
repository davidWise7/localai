# Twilio Voice Integration with Bilingual Support
"""
LocalAI Assistant - Voice Call Handler
Handles incoming voice calls with Quebec French/English support
Integrates with existing AI processor and graceful human transfer
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Twilio imports - FIXED
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather, Say

logger = logging.getLogger(__name__)

class TwilioVoice:
    """Twilio Voice integration with bilingual AI support"""
    
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        
        if not all([self.account_sid, self.auth_token, self.phone_number]):
            logger.warning("Twilio credentials not complete - voice features may be limited")
            self.client = None
        else:
            self.client = Client(self.account_sid, self.auth_token)
        
        # Voice settings for Quebec French and English
        self.voices = {
            'french': {
                'voice': 'Polly.Chantal',  # Quebec French voice
                'language': 'fr-CA'
            },
            'english': {
                'voice': 'Polly.Joanna',  # Clear English voice
                'language': 'en-CA'
            }
        }
        
        logger.info("Twilio Voice initialized successfully")
    
    def create_welcome_response(self, language: str = 'detect') -> str:
        """Create initial voice response with language detection"""
        response = VoiceResponse()
        
        if language == 'detect':
            # Start with bilingual greeting to detect language
            response.say(
                "Bonjour! Hello! How can I help you today? Comment puis-je vous aider?",
                voice=self.voices['english']['voice'],
                language='en-CA'
            )
            
            # Gather speech input for language detection
            gather = Gather(
                input='speech',
                action='/webhook/voice/process',
                method='POST',
                speech_timeout='auto',
                language='fr-CA,en-CA',
                enhanced='true'
            )
            
            gather.say(
                "Please speak naturally... Parlez naturellement...",
                voice=self.voices['english']['voice'],
                language='en-CA'
            )
            
            response.append(gather)
            
            # Fallback if no speech detected
            response.say(
                "I didn't hear anything. Please call back. Je n'ai rien entendu. Rappellez s'il vous plaît.",
                voice=self.voices['english']['voice'],
                language='en-CA'
            )
            
        elif language == 'french':
            response.say(
                "Bonjour! Comment puis-je vous aider aujourd'hui?",
                voice=self.voices['french']['voice'],
                language=self.voices['french']['language']
            )
            
            gather = Gather(
                input='speech',
                action='/webhook/voice/process',
                method='POST',
                speech_timeout='auto',
                language='fr-CA',
                enhanced='true'
            )
            
            gather.say(
                "Je vous écoute...",
                voice=self.voices['french']['voice'],
                language=self.voices['french']['language']
            )
            
            response.append(gather)
            
        else:  # English
            response.say(
                "Hello! How can I help you today?",
                voice=self.voices['english']['voice'],
                language=self.voices['english']['language']
            )
            
            gather = Gather(
                input='speech',
                action='/webhook/voice/process',
                method='POST',
                speech_timeout='auto',
                language='en-CA',
                enhanced='true'
            )
            
            gather.say(
                "Please go ahead...",
                voice=self.voices['english']['voice'],
                language=self.voices['english']['language']
            )
            
            response.append(gather)
        
        return str(response)
    
    def create_ai_response(self, message: str, ai_response_text: str, language: str) -> str:
        """Create voice response from AI text"""
        response = VoiceResponse()
        
        voice_config = self.voices.get(language, self.voices['english'])
        
        # Speak the AI response
        response.say(
            ai_response_text,
            voice=voice_config['voice'],
            language=voice_config['language']
        )
        
        # Continue conversation
        gather = Gather(
            input='speech',
            action='/webhook/voice/process',
            method='POST',
            speech_timeout='auto',
            language=voice_config['language'],
            enhanced='true'
        )
        
        if language == 'french':
            gather.say(
                "Avez-vous d'autres questions? Ou dites 'transférer' pour parler à quelqu'un.",
                voice=voice_config['voice'],
                language=voice_config['language']
            )
        else:
            gather.say(
                "Do you have any other questions? Or say 'transfer' to speak with someone.",
                voice=voice_config['voice'],
                language=voice_config['language']
            )
        
        response.append(gather)
        
        # Fallback
        if language == 'french':
            response.say(
                "Merci d'avoir appelé! Au revoir!",
                voice=voice_config['voice'],
                language=voice_config['language']
            )
        else:
            response.say(
                "Thanks for calling! Goodbye!",
                voice=voice_config['voice'],
                language=voice_config['language']
            )
        
        return str(response)
    
    def create_transfer_response(self, language: str, transfer_number: str = None) -> str:
        """Create response for transferring to human"""
        response = VoiceResponse()
        
        voice_config = self.voices.get(language, self.voices['english'])
        
        if language == 'french':
            response.say(
                "Bien sûr! Je vais vous transférer à quelqu'un qui peut vous aider. Un moment s'il vous plaît...",
                voice=voice_config['voice'],
                language=voice_config['language']
            )
        else:
            response.say(
                "Of course! Let me transfer you to someone who can help. Please hold on...",
                voice=voice_config['voice'],
                language=voice_config['language']
            )
        
        # Add hold music
        response.play('http://com.twilio.music.classical.s3.amazonaws.com/BusyStrings.wav')
        
        if transfer_number:
            # Transfer to specific number
            response.dial(transfer_number)
        else:
            # For now, just inform and hang up gracefully
            if language == 'french':
                response.say(
                    "Désolé, personne n'est disponible en ce moment. Quelqu'un vous rappellera bientôt. Merci!",
                    voice=voice_config['voice'],
                    language=voice_config['language']
                )
            else:
                response.say(
                    "Sorry, no one is available right now. Someone will call you back soon. Thank you!",
                    voice=voice_config['voice'],
                    language=voice_config['language']
                )
        
        return str(response)
    
    def create_error_response(self, language: str = 'english') -> str:
        """Create error response when AI fails"""
        response = VoiceResponse()
        
        voice_config = self.voices.get(language, self.voices['english'])
        
        if language == 'french':
            response.say(
                "Désolé, j'ai un petit problème technique. Je vais vous transférer à quelqu'un immédiatement.",
                voice=voice_config['voice'],
                language=voice_config['language']
            )
        else:
            response.say(
                "Sorry, I'm having a technical issue. Let me transfer you to someone right away.",
                voice=voice_config['voice'],
                language=voice_config['language']
            )
        
        # Transfer or provide fallback
        return self.create_transfer_response(language)
    
    def detect_transfer_request(self, speech_text: str, language: str) -> bool:
        """Detect if customer wants to be transferred"""
        speech_lower = speech_text.lower()
        
        transfer_keywords = {
            'french': [
                'transférer', 'transfert', 'humain', 'personne', 'quelqu\'un',
                'gérant', 'manager', 'superviseur', 'propriétaire', 'patron',
                'parler à', 'voir', 'rencontrer'
            ],
            'english': [
                'transfer', 'human', 'person', 'someone', 'manager',
                'supervisor', 'owner', 'speak to', 'talk to', 'representative',
                'agent', 'operator'
            ]
        }
        
        keywords = transfer_keywords.get(language, transfer_keywords['english'])
        return any(keyword in speech_lower for keyword in keywords)
    
    def detect_language_from_speech(self, speech_text: str) -> str:
        """Detect language from transcribed speech"""
        speech_lower = speech_text.lower()
        
        # French indicators
        french_words = [
            'bonjour', 'salut', 'merci', 'oui', 'non', 'je', 'vous', 'nous',
            'comment', 'quand', 'où', 'pourquoi', 'combien', 'quel', 'quelle',
            'heures', 'ouvert', 'fermé', 'prix', 'coût', 'rendez-vous',
            'j\'aimerais', 'voudrais', 'puis-je', 'pouvez-vous'
        ]
        
        french_count = sum(1 for word in french_words if word in speech_lower)
        
        # If 2+ French words, it's French
        return 'french' if french_count >= 2 else 'english'
    
    async def process_voice_input(self, speech_text: str, call_context: Dict = None) -> Dict[str, Any]:
        """Process voice input and return response data"""
        try:
            # Detect language
            language = self.detect_language_from_speech(speech_text)
            
            # Check for transfer request
            if self.detect_transfer_request(speech_text, language):
                return {
                    'action': 'transfer',
                    'language': language,
                    'message': speech_text
                }
            
            # Process with AI (will be handled by the webhook)
            return {
                'action': 'process_ai',
                'language': language,
                'message': speech_text,
                'call_context': call_context
            }
            
        except Exception as e:
            logger.error(f"Voice input processing error: {str(e)}")
            return {
                'action': 'error',
                'language': 'english',
                'error': str(e)
            }
    
    def log_voice_interaction(self, call_data: Dict[str, Any]) -> bool:
        """Log voice call interaction"""
        try:
            logger.info(f"Voice call logged: {call_data.get('from')} -> {call_data.get('to')}")
            logger.info(f"Speech: {call_data.get('speech_text', 'N/A')}")
            logger.info(f"Language: {call_data.get('language', 'unknown')}")
            logger.info(f"Action: {call_data.get('action', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"Voice logging error: {str(e)}")
            return False