# Enhanced Voice System with Real-time Google Speech + Gemini
"""
LocalAI Assistant - ChatGPT-style Voice Conversations
Real-time speech processing with natural bilingual conversations
Uses Google Speech-to-Text + Gemini AI + Google Text-to-Speech
"""

import os
import json
import logging
import asyncio
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Google Cloud APIs
from google.cloud import speech
from google.cloud import texttospeech

# Twilio imports
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Start, Stream

logger = logging.getLogger(__name__)

class EnhancedVoiceSystem:
    """Real-time voice conversation system with Google APIs + Gemini"""
    
    def __init__(self):
        self.setup_google_apis()
        self.setup_twilio()
        self.conversation_contexts = {}  # Store ongoing conversations
        
    def setup_google_apis(self):
        """Initialize Google Cloud Speech and Text-to-Speech"""
        try:
            # Speech-to-Text client
            self.speech_client = speech.SpeechClient()
            
            # Text-to-Speech client  
            self.tts_client = texttospeech.TextToSpeechClient()
            
            # Speech recognition config for phone calls
            self.speech_config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.MULAW,
                sample_rate_hertz=8000,
                language_code="en-US",  # Primary language
                alternative_language_codes=["fr-CA"],  # Quebec French
                enable_automatic_punctuation=True,
                enable_word_time_offsets=True,
                model="phone_call"  # Optimized for phone calls
            )
            
            # Streaming config
            self.streaming_config = speech.StreamingRecognitionConfig(
                config=self.speech_config,
                interim_results=True,
                single_utterance=False,
                enable_voice_activity_events=True
            )
            
            logger.info("✅ Google Speech APIs initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Google APIs initialization failed: {str(e)}")
            raise
    
    def setup_twilio(self):
        """Initialize Twilio client"""
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        
        if all([self.account_sid, self.auth_token, self.phone_number]):
            self.twilio_client = Client(self.account_sid, self.auth_token)
            logger.info("✅ Twilio initialized successfully")
        else:
            logger.warning("⚠️ Twilio credentials incomplete")
            self.twilio_client = None
    
    def create_welcome_twiml(self, call_sid: str, base_url: str = "https://your-domain.com") -> str:
        """Create TwiML to start real-time voice stream"""
        response = VoiceResponse()
        
        # Bilingual greeting
        response.say(
            "Bonjour! Hello! Welcome to our AI assistant. I can help you in English or French.",
            voice='Polly.Joanna',
            language='en-US'
        )
        
        # Start real-time audio stream
        start = Start()
        stream = Stream(
            url=f'wss://{base_url.replace("https://", "").replace("http://", "")}/voice/stream/{call_sid}',
            track='inbound_track'
        )
        start.append(stream)
        response.append(start)
        
        # Keep the call alive
        response.pause(length=30)
        response.say("Thank you for calling!", voice='Polly.Joanna')
        
        return str(response)
    
    async def handle_voice_stream(self, call_sid: str, audio_data: bytes) -> Optional[bytes]:
        """Process real-time audio stream and return response audio"""
        try:
            # Initialize conversation context if needed
            if call_sid not in self.conversation_contexts:
                self.conversation_contexts[call_sid] = {
                    'language': 'auto',
                    'conversation_history': [],
                    'current_utterance': '',
                    'last_response_time': datetime.now()
                }
            
            context = self.conversation_contexts[call_sid]
            
            # Convert audio to text using Google Speech-to-Text
            transcript = await self.speech_to_text(audio_data)
            
            if not transcript:
                return None
            
            logger.info(f"🎙️ Customer said: {transcript}")
            
            # Detect language and update context
            detected_language = self.detect_language_from_speech(transcript)
            context['language'] = detected_language
            
            # Add to conversation history
            context['conversation_history'].append({
                'speaker': 'customer',
                'text': transcript,
                'timestamp': datetime.now(),
                'language': detected_language
            })
            
            # Generate AI response using existing AI processor
            ai_response = await self.generate_voice_response(transcript, context)
            
            # Add AI response to history
            context['conversation_history'].append({
                'speaker': 'ai',
                'text': ai_response,
                'timestamp': datetime.now(),
                'language': detected_language
            })
            
            # Convert response to speech
            response_audio = await self.text_to_speech(ai_response, detected_language)
            
            logger.info(f"🤖 AI responded: {ai_response}")
            
            return response_audio
            
        except Exception as e:
            logger.error(f"❌ Voice stream processing error: {str(e)}")
            return None
    
    async def speech_to_text(self, audio_data: bytes) -> Optional[str]:
        """Convert audio to text using Google Speech-to-Text"""
        try:
            # Create audio content
            audio = speech.RecognitionAudio(content=audio_data)
            
            # Perform recognition
            response = self.speech_client.recognize(
                config=self.speech_config,
                audio=audio
            )
            
            # Get the best result
            if response.results:
                transcript = response.results[0].alternatives[0].transcript
                confidence = response.results[0].alternatives[0].confidence
                
                # Only return high-confidence results
                if confidence > 0.6:  # Lower threshold for phone audio
                    return transcript.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Speech-to-text error: {str(e)}")
            return None
    
    async def text_to_speech(self, text: str, language: str) -> bytes:
        """Convert text to speech using Google Text-to-Speech"""
        try:
            # Choose voice based on language
            if language == 'french':
                voice = texttospeech.VoiceSelectionParams(
                    language_code="fr-CA",  # Quebec French
                    name="fr-CA-Neural2-A",  # High quality neural voice
                    ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
                )
            else:
                voice = texttospeech.VoiceSelectionParams(
                    language_code="en-US",  # English US (since en-CA not available)
                    name="en-US-Standard-C", 
                    ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
                )
            
            # Audio config for phone calls
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MULAW,
                sample_rate_hertz=8000,
                speaking_rate=1.0,
                pitch=0.0
            )
            
            # Synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Perform text-to-speech
            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            return response.audio_content
            
        except Exception as e:
            logger.error(f"❌ Text-to-speech error: {str(e)}")
            # Return silence on error
            return b'\x00' * 1000
    
    def detect_language_from_speech(self, transcript: str) -> str:
        """Detect language from speech transcript"""
        transcript_lower = transcript.lower()
        
        # French indicators
        french_words = [
            'bonjour', 'salut', 'merci', 'oui', 'non', 'je', 'vous',
            'comment', 'quand', 'où', 'pourquoi', 'combien',
            'heures', 'ouvert', 'fermé', 'prix', 'rendez-vous',
            'allô', 'bonsoir', 'allo'
        ]
        
        french_count = sum(1 for word in french_words if word in transcript_lower)
        
        return 'french' if french_count >= 2 else 'english'
    
    async def generate_voice_response(self, transcript: str, context: Dict) -> str:
        """Generate AI response using existing AI processor"""
        try:
            # Import your existing AI processor
            from ai_processor import AIProcessor
            
            ai_processor = AIProcessor()
            
            # Get business context (using your existing database)
            from database import Database
            db = Database()
            business = await db.get_business_by_phone(self.phone_number)
            
            if not business:
                if context['language'] == 'french':
                    return "Désolé, je ne peux pas accéder aux informations d'entreprise en ce moment."
                else:
                    return "Sorry, I can't access business information right now."
            
            # Generate response using your existing AI logic
            ai_response = await ai_processor.generate_response(transcript, business)
            
            # Optimize for voice (shorter, more conversational)
            voice_optimized = self.optimize_for_voice(ai_response.text, context['language'])
            
            # Check if escalation needed
            if ai_response.escalate:
                if context['language'] == 'french':
                    return voice_optimized + " Je vais vous transférer à quelqu'un maintenant."
                else:
                    return voice_optimized + " Let me transfer you to someone who can help."
            
            return voice_optimized
            
        except Exception as e:
            logger.error(f"❌ AI response generation error: {str(e)}")
            
            # Fallback responses
            if context['language'] == 'french':
                return "Désolé, j'ai un petit problème technique. Comment puis-je vous aider?"
            else:
                return "Sorry, I'm having a technical issue. How can I help you?"
    
    def optimize_for_voice(self, text: str, language: str) -> str:
        """Optimize text response for voice conversation"""
        # Remove excessive punctuation
        text = text.replace('!', '.').replace('?', '.')
        
        # Shorten if too long (voice responses should be concise)
        if len(text) > 200:
            sentences = text.split('.')
            text = '. '.join(sentences[:2]) + '.'
        
        # Add natural voice pauses
        text = text.replace('. ', '. ... ')
        
        # Make more conversational
        if language == 'french':
            text = text.replace('Nous sommes', 'On est')
            text = text.replace('Pouvez-vous', 'Peux-tu')
        else:
            text = text.replace('We are', "We're")
            text = text.replace('You can', 'You can just')
        
        return text
    
    async def handle_call_end(self, call_sid: str):
        """Clean up when call ends"""
        if call_sid in self.conversation_contexts:
            context = self.conversation_contexts[call_sid]
            
            # Log conversation for analytics
            logger.info(f"📞 Call {call_sid} ended. Duration: {len(context['conversation_history'])} exchanges")
            
            # Save conversation to database if needed
            await self.save_conversation_log(call_sid, context)
            
            # Remove from memory
            del self.conversation_contexts[call_sid]
    
    async def save_conversation_log(self, call_sid: str, context: Dict):
        """Save voice conversation to database"""
        try:
            from database import Database
            db = Database()
            
            # Create conversation summary
            conversation_text = '\n'.join([
                f"{msg['speaker']}: {msg['text']}" 
                for msg in context['conversation_history']
            ])
            
            # Log to database
            await db.log_conversation({
                'business_id': 'demo_salon_001',  # Use actual business ID
                'customer_phone': 'voice_call',
                'platform': 'voice',
                'inbound_message': conversation_text,
                'outbound_message': 'Voice conversation completed',
                'intent': 'voice_call',
                'ai_confidence': 0.9,
                'escalated': False
            })
            
            logger.info(f"✅ Voice conversation {call_sid} saved to database")
            
        except Exception as e:
            logger.error(f"❌ Error saving voice conversation: {str(e)}")

# WebSocket handler for real-time audio streaming
class VoiceStreamHandler:
    """Handle WebSocket audio streaming from Twilio"""
    
    def __init__(self, voice_system: EnhancedVoiceSystem):
        self.voice_system = voice_system
        self.audio_buffer = {}
    
    async def handle_websocket(self, websocket, call_sid: str):
        """Handle WebSocket connection for audio streaming"""
        try:
            logger.info(f"🔗 Voice stream connected for call {call_sid}")
            
            self.audio_buffer[call_sid] = []
            
            async for message in websocket:
                data = json.loads(message)
                
                if data['event'] == 'media':
                    # Decode audio data
                    audio_data = base64.b64decode(data['media']['payload'])
                    
                    # Buffer audio until we have enough for processing
                    self.audio_buffer[call_sid].append(audio_data)
                    
                    # Process when we have ~1 second of audio
                    if len(self.audio_buffer[call_sid]) >= 50:  # ~1 second at 8kHz
                        combined_audio = b''.join(self.audio_buffer[call_sid])
                        self.audio_buffer[call_sid] = []
                        
                        # Process audio and get response
                        response_audio = await self.voice_system.handle_voice_stream(
                            call_sid, combined_audio
                        )
                        
                        if response_audio:
                            # Send response back to Twilio
                            await self.send_audio_response(websocket, response_audio)
                
                elif data['event'] == 'stop':
                    logger.info(f"📞 Voice stream ended for call {call_sid}")
                    await self.voice_system.handle_call_end(call_sid)
                    break
                    
        except Exception as e:
            logger.error(f"❌ WebSocket error: {str(e)}")
    
    async def send_audio_response(self, websocket, audio_data: bytes):
        """Send audio response back to Twilio"""
        try:
            # Encode audio as base64
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Send to Twilio
            response = {
                'event': 'media',
                'streamSid': 'stream_id',
                'media': {
                    'payload': audio_b64
                }
            }
            
            await websocket.send(json.dumps(response))
            
        except Exception as e:
            logger.error(f"❌ Error sending audio response: {str(e)}")