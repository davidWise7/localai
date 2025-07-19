# test_gemini.py
import os
import google.generativeai as genai
from dotenv import load_dotenv

print("🧪 Testing Gemini API Key...")
print("=" * 40)

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv('GEMINI_API_KEY')
if api_key:
    print(f"✅ API Key found: {api_key[:10]}...")
else:
    print("❌ No API key found in .env file")
    exit()

# Configure Gemini
genai.configure(api_key=api_key)

try:
    print("🔄 Testing Gemini connection...")
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Hello, how are you?")
    print("✅ API Key works perfectly!")
    print("📤 Response:", response.text)
except Exception as e:
    print("❌ API Key issue:", str(e))
    print("💡 Try regenerating your API key at: https://aistudio.google.com/app/apikey")