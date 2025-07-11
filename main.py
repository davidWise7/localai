# main.py - LocalAI Assistant with Professional Dashboard
"""
Main application file with SMS, Voice webhooks, and Professional Dashboard
Bilingual AI customer service with Quebec French support
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, Any

# Add src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# FastAPI imports
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Header, Form
from fastapi.responses import PlainTextResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
import uvicorn

# Import modules from src directory
try:
    from ai_processor import AIProcessor
    from database import Database
    from integrations.twilio_sms import TwilioSMS
    from integrations.twilio_voice import TwilioVoice
    from integrations.facebook_api import FacebookAPI
    from dashboard_api import dashboard_router
    print("✅ All modules imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the parent directory and all modules exist in src/")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================================
# FASTAPI APPLICATION SETUP
# ================================

app = FastAPI(
    title="LocalAI Assistant - Professional Dashboard",
    description="Bilingual AI customer service with professional business management",
    version="2.1.0"
)

# Include dashboard router
app.include_router(dashboard_router)

# Initialize components
ai_processor = None
database = None
twilio_sms = None
twilio_voice = None
facebook_api = None

def initialize_components():
    """Initialize all components with proper error handling"""
    global ai_processor, database, twilio_sms, twilio_voice, facebook_api
    
    try:
        logger.info("🔄 Initializing components...")
        
        # Check for required environment variables
        gemini_key = os.getenv('GEMINI_API_KEY')
        twilio_sid = os.getenv('TWILIO_ACCOUNT_SID')
        twilio_token = os.getenv('TWILIO_AUTH_TOKEN')
        
        if not gemini_key:
            logger.error("❌ GEMINI_API_KEY not found")
            raise ValueError("Missing GEMINI_API_KEY")
        
        if not twilio_sid or not twilio_token:
            logger.error("❌ Twilio credentials not found")
            raise ValueError("Missing Twilio credentials")
        
        # Initialize components
        ai_processor = AIProcessor()
        logger.info("✅ AI Processor initialized")
        
        database = Database()
        logger.info("✅ Database initialized")
        
        twilio_sms = TwilioSMS()
        logger.info("✅ Twilio SMS initialized")
        
        twilio_voice = TwilioVoice()
        logger.info("✅ Twilio Voice initialized")
        
        facebook_api = FacebookAPI()
        logger.info("✅ Facebook API initialized")
        
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

# ================================
# API ROUTES
# ================================

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "LocalAI Assistant - Professional Business Management",
        "status": "running",
        "version": "2.1.0",
        "features": [
            "🎙️ Voice calls (Quebec French/English)",
            "📱 SMS support (bilingual)",
            "🤖 AI message processing",
            "🔄 Smart call transfers",
            "📊 Professional dashboard",
            "📈 Real-time analytics",
            "🇨🇦 Perfect for Quebec businesses"
        ],
        "components": {
            "ai_processor": "✅ Active" if ai_processor else "❌ Not initialized",
            "database": "✅ Connected" if database else "❌ Not initialized",
            "twilio_sms": "✅ Ready" if twilio_sms else "❌ Not initialized",
            "twilio_voice": "✅ Ready" if twilio_voice else "❌ Not initialized",
            "facebook_api": "✅ Ready" if facebook_api else "❌ Not initialized",
            "dashboard": "✅ Professional Interface Available"
        },
        "endpoints": {
            "dashboard": "GET /dashboard/web - Professional business management interface",
            "sms_webhook": "POST /webhook/sms",
            "voice_webhook": "POST /webhook/voice", 
            "voice_process": "POST /webhook/voice/process",
            "facebook_webhook": "POST /webhook/facebook",
            "health": "GET /health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check with dashboard support"""
    try:
        health_status = {
            "status": "healthy",
            "version": "2.1.0",
            "timestamp": datetime.utcnow().isoformat(),
            "features": {
                "voice_calls": "✅ Enabled",
                "sms_support": "✅ Enabled",
                "bilingual_ai": "✅ French/English",
                "call_transfers": "✅ Smart routing",
                "dashboard": "✅ Professional Interface",
                "real_time_analytics": "✅ Live metrics"
            },
            "components": {},
            "environment": os.getenv("ENVIRONMENT", "development")
        }
        
        # Test components
        if ai_processor:
            try:
                test_business = {
                    "name": "Test Salon",
                    "services": ["haircut"],
                    "hours": "9-5",
                    "address": "Test Address"
                }
                test_response = await ai_processor.generate_response("hello", test_business)
                health_status["components"]["ai_processor"] = "✅ Ready"
            except Exception as e:
                health_status["components"]["ai_processor"] = f"❌ Error: {str(e)}"
                health_status["status"] = "degraded"
        
        if database:
            try:
                business = await database.get_business_by_phone(os.getenv('TWILIO_PHONE_NUMBER', '+1234567890'))
                health_status["components"]["database"] = "✅ Connected"
            except Exception as e:
                health_status["components"]["database"] = f"❌ Error: {str(e)}"
                health_status["status"] = "degraded"
        
        if twilio_voice:
            health_status["components"]["twilio_voice"] = "✅ Ready"
        if twilio_sms:
            health_status["components"]["twilio_sms"] = "✅ Ready"
        if facebook_api:
            health_status["components"]["facebook_api"] = "✅ Ready"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

# ================================
# DASHBOARD REDIRECT
# ================================

@app.get("/dashboard")
async def dashboard_redirect():
    """Redirect old dashboard to new professional interface"""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Redirecting to Professional Dashboard</title>
        <meta http-equiv="refresh" content="0;url=/dashboard/web">
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex; align-items: center; justify-content: center; 
                min-height: 100vh; margin: 0; background: #f8fafc;
            }
            .redirect-message {
                text-align: center; padding: 2rem;
                background: white; border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            }
        </style>
    </head>
    <body>
        <div class="redirect-message">
            <h2>🚀 Redirecting to Professional Dashboard...</h2>
            <p>You're being redirected to the new business management interface.</p>
            <p><a href="/dashboard/web">Click here if you're not redirected automatically</a></p>
        </div>
    </body>
    </html>
    """)

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
            raise HTTPException(status_code=503, detail="Components not initialized")
        
        form_data = await request.form()
        sms_data = {
            'From': form_data.get('From'),
            'To': form_data.get('To'),
            'Body': form_data.get('Body', ''),
            'MessageSid': form_data.get('MessageSid')
        }
        
        logger.info(f"📱 SMS received from {sms_data['From']}")
        
        background_tasks.add_task(process_sms_message, sms_data)
        
        return PlainTextResponse("", status_code=200)
        
    except Exception as e:
        logger.error(f"❌ SMS webhook error: {str(e)}")
        return PlainTextResponse("Error", status_code=500)

# ================================
# VOICE WEBHOOKS (EXISTING)
# ================================

@app.post("/webhook/voice")
async def handle_voice_webhook(request: Request):
    """Handle incoming voice calls"""
    try:
        if not twilio_voice:
            raise HTTPException(status_code=503, detail="Voice system not initialized")
        
        form_data = await request.form()
        call_data = {
            'From': form_data.get('From'),
            'To': form_data.get('To'),
            'CallSid': form_data.get('CallSid'),
            'CallStatus': form_data.get('CallStatus')
        }
        
        logger.info(f"🎙️ Voice call received from {call_data['From']}")
        
        # Log the call
        twilio_voice.log_voice_interaction({
            **call_data,
            'action': 'incoming_call',
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Create welcome response with bilingual greeting
        twiml_response = twilio_voice.create_welcome_response()
        
        return Response(content=twiml_response, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"❌ Voice webhook error: {str(e)}")
        
        # Fallback TwiML response
        fallback_response = twilio_voice.create_error_response() if twilio_voice else """
        <Response>
            <Say voice="Polly.Joanna">Sorry, our system is temporarily unavailable. Please call back later.</Say>
        </Response>
        """
        return Response(content=fallback_response, media_type="application/xml")

@app.post("/webhook/voice/process")
async def handle_voice_processing(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Process voice input with AI"""
    try:
        if not ai_processor or not twilio_voice or not database:
            raise HTTPException(status_code=503, detail="Components not initialized")
        
        form_data = await request.form()
        call_data = {
            'From': form_data.get('From'),
            'To': form_data.get('To'),
            'CallSid': form_data.get('CallSid'),
            'SpeechResult': form_data.get('SpeechResult', ''),
            'Confidence': form_data.get('Confidence', '0')
        }
        
        speech_text = call_data['SpeechResult']
        logger.info(f"🎙️ Speech received: {speech_text}")
        
        if not speech_text:
            # No speech detected
            twiml_response = twilio_voice.create_welcome_response()
            return Response(content=twiml_response, media_type="application/xml")
        
        # Process voice input
        voice_result = await twilio_voice.process_voice_input(speech_text, call_data)
        
        if voice_result['action'] == 'transfer':
            # Customer wants transfer
            logger.info(f"🔄 Transfer requested by {call_data['From']}")
            twiml_response = twilio_voice.create_transfer_response(voice_result['language'])
            
            # Log transfer request
            background_tasks.add_task(log_voice_interaction, {
                **call_data,
                'speech_text': speech_text,
                'action': 'transfer_requested',
                'language': voice_result['language']
            })
            
        elif voice_result['action'] == 'process_ai':
            # Process with AI
            background_tasks.add_task(process_voice_with_ai, call_data, speech_text, voice_result['language'])
            
            # Generate AI response
            business = await database.get_business_by_phone(call_data['To'])
            if business:
                ai_response = await ai_processor.generate_response(speech_text, business)
                twiml_response = twilio_voice.create_ai_response(
                    speech_text, 
                    ai_response.text, 
                    voice_result['language']
                )
                
                # If AI wants to escalate, modify response
                if ai_response.escalate:
                    twiml_response = twilio_voice.create_transfer_response(voice_result['language'])
            else:
                twiml_response = twilio_voice.create_error_response(voice_result['language'])
        
        else:
            # Error case
            twiml_response = twilio_voice.create_error_response()
        
        return Response(content=twiml_response, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"❌ Voice processing error: {str(e)}")
        
        fallback_response = twilio_voice.create_error_response() if twilio_voice else """
        <Response>
            <Say voice="Polly.Joanna">Sorry, I'm having trouble processing your request.</Say>
        </Response>
        """
        return Response(content=fallback_response, media_type="application/xml")

# ================================
# BACKGROUND TASKS
# ================================

async def process_sms_message(sms_data: Dict[str, Any]):
    """Process SMS using existing logic"""
    try:
        start_time = datetime.now()
        
        customer_phone = sms_data.get('From')
        business_phone = sms_data.get('To')
        message_text = sms_data.get('Body', '').strip()
        
        logger.info(f"🔄 Processing SMS from {customer_phone}")
        
        business = await database.get_business_by_phone(business_phone)
        if not business:
            logger.warning(f"⚠️ No business found for phone {business_phone}")
            return
        
        ai_response = await ai_processor.generate_response(message_text, business)
        
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
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        await database.log_conversation(conversation_data, int(processing_time))
        
        sms_result = await twilio_sms.send_sms(
            to_phone=customer_phone,
            message=ai_response.text,
            from_phone=business_phone
        )
        
        logger.info(f"✅ SMS processed in {processing_time:.2f}ms")
        logger.info(f"📤 Response: {ai_response.text}")
        logger.info(f"🎯 Intent: {ai_response.intent}")
        
        if ai_response.escalate:
            logger.warning(f"🚨 SMS escalated - human attention required")
        
    except Exception as e:
        logger.error(f"❌ SMS processing error: {str(e)}")

async def process_voice_with_ai(call_data: Dict[str, Any], speech_text: str, language: str):
    """Process voice call with AI and log interaction"""
    try:
        start_time = datetime.now()
        
        customer_phone = call_data.get('From')
        business_phone = call_data.get('To')
        
        logger.info(f"🔄 Processing voice call from {customer_phone}")
        logger.info(f"🗣️ Speech: {speech_text}")
        logger.info(f"🌐 Language: {language}")
        
        business = await database.get_business_by_phone(business_phone)
        if business:
            ai_response = await ai_processor.generate_response(speech_text, business)
            
            conversation_data = {
                'business_id': business['id'],
                'customer_phone': customer_phone,
                'platform': 'voice',
                'inbound_message': speech_text,
                'outbound_message': ai_response.text,
                'intent': ai_response.intent,
                'ai_confidence': ai_response.confidence,
                'escalated': ai_response.escalate
            }
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            await database.log_conversation(conversation_data, int(processing_time))
            
            logger.info(f"✅ Voice call processed in {processing_time:.2f}ms")
            logger.info(f"🎙️ AI Response: {ai_response.text}")
            logger.info(f"🎯 Intent: {ai_response.intent}")
            
            if ai_response.escalate:
                logger.warning(f"🚨 Voice call escalated - human attention required")
        
    except Exception as e:
        logger.error(f"❌ Voice processing error: {str(e)}")

async def log_voice_interaction(interaction_data: Dict[str, Any]):
    """Log voice interaction details"""
    try:
        logger.info(f"📞 Voice interaction logged:")
        logger.info(f"   From: {interaction_data.get('From')}")
        logger.info(f"   Speech: {interaction_data.get('speech_text', 'N/A')}")
        logger.info(f"   Action: {interaction_data.get('action')}")
        logger.info(f"   Language: {interaction_data.get('language')}")
        
    except Exception as e:
        logger.error(f"❌ Voice logging error: {str(e)}")

# ================================
# STARTUP EVENTS
# ================================

@app.on_event("startup")
async def startup_event():
    """Initialize system with voice support and dashboard"""
    logger.info("🚀 Starting LocalAI Assistant with Professional Dashboard...")
    logger.info("=" * 70)
    
    success = initialize_components()
    
    if success:
        logger.info("=" * 70)
        logger.info("🎉 LocalAI Professional Assistant ready!")
        logger.info("🎙️ Voice calls: ENABLED")
        logger.info("📱 SMS messages: ENABLED") 
        logger.info("🤖 Bilingual AI: French/English")
        logger.info("🔄 Smart transfers: ACTIVE")
        logger.info("📊 Professional Dashboard: AVAILABLE")
        logger.info("📈 Real-time Analytics: ENABLED")
        logger.info("")
        logger.info("🌐 Access Points:")
        logger.info("📊 Dashboard: http://localhost:8000/dashboard/web")
        logger.info("🔍 Health: http://localhost:8000/health")
        logger.info("📞 Voice webhook: http://localhost:8000/webhook/voice")
        logger.info("📱 SMS webhook: http://localhost:8000/webhook/sms")
        logger.info("🔧 API docs: http://localhost:8000/docs")
        logger.info("=" * 70)
    else:
        logger.error("❌ Failed to initialize - check your configuration")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down LocalAI Assistant...")

# ================================
# MAIN ENTRY POINT
# ================================

if __name__ == "__main__":
    print("🎙️📱 LocalAI Assistant - Professional Dashboard")
    print("🇨🇦 Bilingual Quebec French/English AI")
    print("📊 Professional Business Management Interface")
    print("🔧 Voice calls + SMS messages + Smart transfers + Analytics")
    print("🚀 Starting professional server...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
        log_level="info"
    )