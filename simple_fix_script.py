# simple_fix.py - Just fix the phone number
import sqlite3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fix_phone_number():
    """Simply update the phone number in existing business"""
    
    # Connect to database
    conn = sqlite3.connect("localai.db")
    cursor = conn.cursor()
    
    # Get the correct phone number from .env
    phone_number = os.getenv('TWILIO_PHONE_NUMBER', '+14502349148')
    print(f"Using phone number: {phone_number}")
    
    # Check what columns exist
    cursor.execute("PRAGMA table_info(businesses)")
    columns = cursor.fetchall()
    print("Available columns:")
    for col in columns:
        print(f"  - {col[1]}")
    
    # Check current business
    cursor.execute("SELECT name, phone FROM businesses WHERE id = 'demo_salon_001'")
    result = cursor.fetchone()
    if result:
        print(f"Current business: {result[0]} - {result[1]}")
    else:
        print("No demo business found")
    
    # Update just the phone number
    cursor.execute("UPDATE businesses SET phone = ? WHERE id = 'demo_salon_001'", (phone_number,))
    
    # Verify the update
    cursor.execute("SELECT name, phone FROM businesses WHERE id = 'demo_salon_001'")
    result = cursor.fetchone()
    
    if result:
        print(f"✅ Updated business: {result[0]} - {result[1]}")
    else:
        print("❌ Business not found after update")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("🔧 Fixing phone number only...")
    fix_phone_number()
    print("✅ Phone number fixed! Restart your server now.")