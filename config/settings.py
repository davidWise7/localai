# Configuration Settings
import os
from dotenv import load_dotenv

load_dotenv()

# API Settings
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
