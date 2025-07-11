# main.py - LocalAI Assistant with Dashboard Router
"""
Main application file that imports modules from src/ directory
FIXED: Now includes dashboard router for /dashboard/web endpoint
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

# Load environment variables from .env file in current directory
from dotenv import load_dotenv
load_dotenv()  # This will look for .env in the current directory

# FastAPI imports
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Header
from fastapi.responses import PlainTextResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Import your modules from src directory
try:
    from ai_processor import AIProcessor
    from database import Database
    from integrations.twilio_sms import TwilioSMS
    from integrations.facebook_api import FacebookAPI
    # FIXED: Import the dashboard router
    from dashboard import dashboard_router
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
    title="LocalAI Assistant",
    description="AI-powered customer service automation for local businesses",
    version="1.0.0"
)

# Initialize components with better error handling
ai_processor = None
database = None
twilio_sms = None
facebook_api = None

def initialize_components():
    """Initialize all components with proper error handling"""
    global ai_processor, database, twilio_sms, facebook_api
    
    try:
        logger.info("🔄 Initializing components...")
        
        # Check for required environment variables
        gemini_key = os.getenv('GEMINI_API_KEY')
        if not gemini_key:
            logger.error("❌ GEMINI_API_KEY not found in environment variables")
            logger.error("Make sure your .env file is in the same directory as main.py")
            raise ValueError("Missing GEMINI_API_KEY")
        
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
        
        logger.info("🎉 All components initialized successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Component initialization failed: {str(e)}")
        return False

# Serve static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception:
    logger.warning("Static files directory not found - dashboard will be limited")

# FIXED: Include the dashboard router
app.include_router(dashboard_router, prefix="")

# ================================
# API ROUTES
# ================================

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "LocalAI Assistant - AI-Powered Customer Service",
        "status": "running",
        "version": "1.0.0",
        "architecture": "modular",
        "components": {
            "ai_processor": "✅ Active" if ai_processor else "❌ Not initialized",
            "database": "✅ Connected" if database else "❌ Not initialized",
            "twilio_sms": "✅ Configured" if twilio_sms else "❌ Not initialized",
            "facebook_api": "✅ Ready" if facebook_api else "❌ Not initialized"
        },
        "features": [
            "AI message processing with Gemini",
            "Smart intent classification",
            "Booking assistance", 
            "FAQ automation",
            "SMS & Facebook support",
            "Real-time analytics",
            "Conversation logging",
            "Escalation handling",
            "Professional Dashboard"
        ],
        "endpoints": {
            "webhooks": {
                "sms": "POST /webhook/sms",
                "facebook": "POST /webhook/facebook"
            },
            "dashboard": {
                "web_interface": "GET /dashboard/web",
                "api_metrics": "GET /api/dashboard/metrics",
                "live_feed": "GET /api/dashboard/live-feed"
            },
            "health": "GET /health"
        }
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    try:
        health_status = {
            "status": "healthy",
            "version": "1.0.0", 
            "timestamp": datetime.utcnow().isoformat(),
            "components": {},
            "environment": os.getenv("ENVIRONMENT", "development"),
            "env_file_location": os.path.abspath(".env") if os.path.exists(".env") else "Not found"
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
        
        # Check Twilio
        if twilio_sms:
            health_status["components"]["twilio"] = "✅ Ready"
        else:
            health_status["components"]["twilio"] = "❌ Not initialized"
            health_status["status"] = "degraded"
        
        # Check Facebook API
        if facebook_api:
            health_status["components"]["facebook"] = "✅ Ready"
        else:
            health_status["components"]["facebook"] = "❌ Not initialized"
            health_status["status"] = "degraded"
        
        # Dashboard is now included
        health_status["components"]["dashboard"] = "✅ Available at /dashboard/web"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.post("/webhook/sms")
async def handle_sms_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_twilio_signature: str = Header(None)
):
    """SMS webhook handler"""
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
        logger.info(f"📝 Message: {sms_data['Body']}")
        
        # Process message in background
        background_tasks.add_task(process_sms_message, sms_data)
        
        # Return empty response to Twilio (required)
        return PlainTextResponse("", status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ SMS webhook error: {str(e)}")
        return PlainTextResponse("Error", status_code=500)

@app.get("/dashboard")
async def dashboard_home():
    """Enhanced dashboard - REDIRECTS to new professional dashboard"""
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>LocalAI Assistant Dashboard</title>
        <meta http-equiv="refresh" content="0; url=/dashboard/web">
    </head>
    <body>
        <h1>Redirecting to Professional Dashboard...</h1>
        <p>If you're not redirected automatically, <a href="/dashboard/web">click here</a>.</p>
    </body>
    </html>
    """)

# ================================
# BACKGROUND TASKS
# ================================

async def process_sms_message(sms_data: Dict[str, Any]):
    """Process SMS using your existing modules"""
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
        
        logger.info(f"✅ SMS processed successfully in {processing_time_ms}ms")
        logger.info(f"📤 Response: {ai_response.text}")
        logger.info(f"🎯 Intent: {ai_response.intent} | Confidence: {ai_response.confidence:.2f}")
        logger.info(f"📨 SMS sent: {sms_result.get('success', False)}")
        
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
    logger.info("🚀 Starting LocalAI Assistant with modular architecture...")
    logger.info("=" * 60)
    
    # Initialize components
    success = initialize_components()
    
    if success:
        logger.info("=" * 60)
        logger.info("🎉 LocalAI Assistant ready for customers!")
        logger.info("📊 Professional Dashboard: /dashboard/web")
        logger.info("📊 Dashboard API: /api/dashboard/metrics")
        logger.info("🔍 Health: /health")
        logger.info("📱 SMS Webhook: /webhook/sms")
        logger.info("=" * 60)
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
    print("🤖 LocalAI Assistant - Modular Architecture")
    print("📦 Using existing modules from src/ directory")
    print("🔧 Make sure your .env file is in the same directory as this main.py")
    print("📊 Professional Dashboard available at /dashboard/web")
    print("🚀 Starting server...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
        log_level="info"
    )