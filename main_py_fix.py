# main.py - LocalAI Assistant with Complete Voice Support
"""
Main application file with SMS + Voice + Dashboard
Complete bilingual AI customer service system
"""

import os
import sys
import logging
import json
from datetime import datetime
from typing import Dict, Any

# Add src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# FIXED: Setup Google credentials before any imports
def setup_google_credentials():
    """Setup Google credentials from environment variable"""
    try:
        credentials_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
        if credentials_json:
            # Create credentials file
            with open('/tmp/google-credentials.json', 'w') as f:
                f.write(credentials_json)
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/tmp/google-credentials.json'
            logger.info("✅ Google credentials configured")
        else:
            logger.warning("⚠️ No Google credentials found - voice features disabled")
    except Exception as e:
        logger.error(f"❌ Google credentials setup failed: {str(e)}")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Setup Google credentials first
setup_google_credentials()

# FastAPI imports
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Header, WebSocket
from fastapi.responses import PlainTextResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Import your modules
try:
    from ai_processor import AIProcessor
    from database import Database
    from integrations.twilio_sms import TwilioSMS
    from integrations.facebook_api import FacebookAPI
    from dashboard import dashboard_router
    
    # Try to import voice system (may fail if Google Cloud not configured)
    try:
        from enhanced_voice_system import EnhancedVoiceSystem, VoiceStreamHandler
        VOICE_ENABLED = True
        print("✅ Voice system imported successfully")
    except Exception as e:
        print(f"⚠️ Voice system disabled: {str(e)}")
        VOICE_ENABLED = False
        
    print("✅ All core modules imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the parent directory and all modules exist in src/")
    sys.exit(1)

# ================================
# FASTAPI APPLICATION SETUP
# ================================

app = FastAPI(
    title="LocalAI Assistant - Voice & SMS",
    description="AI-powered bilingual customer service with voice and SMS",
    version="2.0.0"
)

# Initialize components
ai_processor = None
database = None
twilio_sms = None
facebook_api = None
voice_system = None
voice_handler = None

def initialize_components():
    """Initialize all components including voice system"""
    global ai_processor, database, twilio_sms, facebook_api, voice_system, voice_handler
    
    try:
        logger.info("🔄 Initializing components...")
        
        # Check for required environment variables
        required_vars = ['GEMINI_API_KEY']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"❌ Missing environment variables: {missing_vars}")
            raise ValueError(f"Missing required environment variables: {missing_vars}")
        
        # Initialize AI Processor
        ai_processor = AIProcessor()
        logger.info("✅ AI Processor initialized")
        
        # Initialize Database
        database = Database()
        logger.info("✅ Database initialized")
        
        # Initialize Twilio SMS
        twilio_sms = TwilioSMS()
        logger.info("✅ Twilio SMS initialized")
        
        # Initialize Facebook API
        facebook_api = FacebookAPI()
        logger.info("✅ Facebook API initialized")
        
        # Initialize Voice System (if available)
        if VOICE_ENABLED:
            try:
                voice_system = EnhancedVoiceSystem()
                voice_handler = VoiceStreamHandler(voice_system)
                logger.info("✅ Voice System initialized")
            except Exception as e:
                logger.warning(f"⚠️ Voice System disabled: {str(e)}")
                VOICE_ENABLED = False
        
        logger.info("🎉 All components initialized successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Component initialization failed: {str(e)}")
        return False

# Serve static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception:
    logger.warning("Static files directory not found")

# Include dashboard router
app.include_router(dashboard_router, prefix="")

# ================================
# API ROUTES
# ================================

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "LocalAI Assistant - Voice & SMS AI Customer Service",
        "status": "running",
        "version": "2.0.0",
        "features": [
            "🎙️ Voice calls with real-time AI" if VOICE_ENABLED else "🎙️ Voice calls (disabled - needs Google Cloud)",
            "💬 SMS message processing",
            "🇫🇷🇨🇦 Bilingual French/English",
            "🤖 Natural conversations",
            "📊 Professional dashboard",
            "🔄 Smart call transfers"
        ],
        "components": {
            "ai_processor": "✅ Active" if ai_processor else "❌ Not initialized",
            "database": "✅ Connected" if database else "❌ Not initialized",
            "twilio_sms": "✅ Configured" if twilio_sms else "❌ Not initialized",
            "voice_system": "✅ Ready" if voice_system else "❌ Not initialized",
            "facebook_api": "✅ Ready" if facebook_api else "❌ Not initialized"
        },
        "endpoints": {
            "voice_calls": "POST /webhook/voice" if VOICE_ENABLED else "Voice disabled",
            "sms_messages": "POST /webhook/sms",
            "voice_stream": "WS /voice/stream/{call_sid}" if VOICE_ENABLED else "Voice disabled",
            "dashboard": "GET /dashboard/web",
            "health": "GET /health"
        }
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    try:
        health_status = {
            "status": "healthy",
            "version": "2.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {},
            "voice_enabled": VOICE_ENABLED,
            "google_cloud": {
                "credentials": bool(os.getenv('GOOGLE_APPLICATION_CREDENTIALS')),
                "project": os.getenv('GOOGLE_CLOUD_PROJECT', 'Not set')
            }
        }
        
        # Check AI Processor
        if ai_processor:
            try:
                test_business = {
                    "name": "Test Business",
                    "services": ["test"],
                    "hours": "9-5",
                    "address": "Test Address"
                }
                test_response = await ai_processor.generate_response("hello", test_business)
                health_status["components"]["ai_processor"] = "✅ Ready"
            except Exception as e:
                health_status["components"]["ai_processor"] = f"❌ Error: {str(e)}"
                health_status["status"] = "degraded"
        else:
            health_status["components"]["ai_processor"] = "❌ Not initialized"
            health_status["status"] = "degraded"
        
        # Check Database
        if database:
            try:
                business = await database.get_business_by_phone(os.getenv('TWILIO_PHONE_NUMBER', '+1234567890'))
                health_status["components"]["database"] = "✅ Connected"
            except Exception as e:
                health_status["components"]["database"] = f"❌ Error: {str(e)}"
                health_status["status"] = "degraded"
        else:
            health_status["components"]["database"] = "❌ Not initialized"
            health_status["status"] = "degraded"
        
        # Check Voice System
        if voice_system:
            health_status["components"]["voice_system"] = "✅ Ready"
        else:
            health_status["components"]["voice_system"] = "❌ Not initialized"
            health_status["status"] = "degraded"
        
        # Dashboard is available
        health_status["components"]["dashboard"] = "✅ Available at /dashboard/web"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

# ================================
# VOICE WEBHOOKS (if enabled)
# ================================

if VOICE_ENABLED:
    @app.post("/webhook/voice")
    async def handle_voice_call(request: Request):
        """Handle incoming voice calls from Twilio"""
        try:
            if not voice_system:
                raise HTTPException(status_code=503, detail="Voice system not initialized")
            
            form_data = await request.form()
            call_sid = form_data.get('CallSid')
            from_number = form_data.get('From')
            to_number = form_data.get('To')
            
            logger.info(f"📞 Voice call: {from_number} -> {to_number} (SID: {call_sid})")
            
            # Get the base URL for websocket
            host = request.headers.get('host', 'localhost:8000')
            base_url = f"https://{host}" if 'railway.app' in host else f"http://{host}"
            
            # Create TwiML response for real-time voice
            twiml_response = voice_system.create_welcome_twiml(call_sid, base_url)
            
            return PlainTextResponse(
                content=twiml_response,
                media_type="application/xml"
            )
            
        except Exception as e:
            logger.error(f"❌ Voice webhook error: {str(e)}")
            
            # Fallback TwiML for errors
            fallback_twiml = '''<?xml version="1.0" encoding="UTF-8"?>
            <Response>
                <Say voice="Polly.Joanna" language="en-US">
                    Thank you for calling. We're experiencing technical difficulties. 
                    Please try calling back in a few minutes or send us a text message.
                </Say>
            </Response>'''
            
            return PlainTextResponse(
                content=fallback_twiml,
                media_type="application/xml"
            )

    @app.websocket("/voice/stream/{call_sid}")
    async def voice_stream_websocket(websocket: WebSocket, call_sid: str):
        """WebSocket endpoint for real-time audio streaming"""
        if not voice_handler:
            await websocket.close(code=4000, reason="Voice system not available")
            return
        
        await websocket.accept()
        logger.info(f"🎙️ Voice stream connected for call {call_sid}")
        
        try:
            await voice_handler.handle_websocket(websocket, call_sid)
        except Exception as e:
            logger.error(f"❌ Voice stream error: {str(e)}")
        finally:
            await websocket.close()

    @app.post("/voice/status")
    async def voice_call_status(request: Request):
        """Handle call status updates from Twilio"""
        try:
            form_data = await request.form()
            call_sid = form_data.get('CallSid')
            call_status = form_data.get('CallStatus')
            
            logger.info(f"📞 Call {call_sid} status: {call_status}")
            
            if call_status in ['completed', 'failed', 'canceled'] and voice_system:
                await voice_system.handle_call_end(call_sid)
            
            return PlainTextResponse("OK", status_code=200)
            
        except Exception as e:
            logger.error(f"❌ Voice status error: {str(e)}")
            return PlainTextResponse("Error", status_code=500)

# ================================
# SMS WEBHOOKS (EXISTING)
# ================================

@app.post("/webhook/sms")
async def handle_sms_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_twilio_signature: str = Header(None)
):
    """SMS webhook handler (existing functionality)"""
    try:
        if not ai_processor or not database or not twilio_sms:
            raise HTTPException(status_code=503, detail="Components not properly initialized")
        
        # Parse Twilio form data
        form_data = await request.form()
        sms_data = {
            'From': form_data.get('From'),
            'To': form_data.get('To'),
            'Body': form_data.get('Body', ''),
            'MessageSid': form_data.get('MessageSid')
        }
        
        logger.info(f"📱 SMS webhook received from {sms_data['From']}")
        
        # Process message in background
        background_tasks.add_task(process_sms_message, sms_data)
        
        return PlainTextResponse("", status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ SMS webhook error: {str(e)}")
        return PlainTextResponse("Error", status_code=500)

# ================================
# BACKGROUND TASKS
# ================================

async def process_sms_message(sms_data: Dict[str, Any]):
    """Process SMS using existing modules"""
    try:
        start_time = datetime.now()
        
        customer_phone = sms_data.get('From')
        business_phone = sms_data.get('To')
        message_text = sms_data.get('Body', '').strip()
        
        logger.info(f"🔄 Processing SMS from {customer_phone}")
        
        # Get business using database
        business = await database.get_business_by_phone(business_phone)
        if not business:
            logger.warning(f"⚠️ No business found for phone {business_phone}")
            return
        
        # Generate AI response
        ai_response = await ai_processor.generate_response(message_text, business)
        
        # Calculate processing time
        processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Log conversation
        conversation_data = {
            'business_id': business['id'],
            'customer_phone': customer_phone,
            'platform': 'sms',
            'inbound_message': message_text,
            'outbound_message': ai_response.text,
            'intent': ai_response.intent,
            'ai_confidence': ai_response.confidence,
            'escalated': ai_response.escalate
        }
        
        await database.log_conversation(conversation_data, processing_time_ms)
        
        # Send SMS response
        sms_result = await twilio_sms.send_sms(
            to_phone=customer_phone,
            message=ai_response.text,
            from_phone=business_phone
        )
        
        logger.info(f"✅ SMS processed in {processing_time_ms}ms")
        logger.info(f"📤 Response: {ai_response.text}")
        logger.info(f"🎯 Intent: {ai_response.intent} | Confidence: {ai_response.confidence:.2f}")
        
        if ai_response.escalate:
            logger.warning(f"🚨 Message escalated - human attention required")
        
    except Exception as e:
        logger.error(f"❌ SMS processing error: {str(e)}")

# ================================
# STARTUP EVENTS
# ================================

@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    logger.info("🚀 Starting LocalAI Assistant with Voice & SMS support...")
    logger.info("=" * 70)
    
    # Initialize components
    success = initialize_components()
    
    if success:
        logger.info("=" * 70)
        logger.info("🎉 LocalAI Assistant Voice & SMS ready!")
        logger.info(f"🎙️ Voice calls: {'ENABLED' if VOICE_ENABLED else 'DISABLED (needs Google Cloud)'}")
        logger.info("📱 SMS messages: ENABLED")
        logger.info("🤖 Bilingual AI: French/English")
        logger.info("🔄 Smart transfers: ACTIVE")
        logger.info("📊 Professional Dashboard: /dashboard/web")
        logger.info("🔍 Health Check: /health")
        logger.info("📞 Voice webhook: /webhook/voice")
        logger.info("💬 SMS webhook: /webhook/sms")
        logger.info("=" * 70)
    else:
        logger.error("❌ Failed to initialize components - check your configuration")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down LocalAI Assistant...")

# ================================
# MAIN ENTRY POINT
# ================================

if __name__ == "__main__":
    print("🎙️📱 LocalAI Assistant - Voice & SMS Support")
    print("🇨🇦 Bilingual Quebec French/English AI")
    print("🔧 Voice calls + SMS messages + Smart transfers")
    print("🚀 Starting enhanced server...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
        log_level="info"
    )