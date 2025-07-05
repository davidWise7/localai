# fix_database.py - Reset demo business with correct phone number
import sqlite3
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fix_database():
    """Fix the demo business phone number"""
    
    # Connect to database
    conn = sqlite3.connect("localai.db")
    cursor = conn.cursor()
    
    # Get the correct phone number from .env
    phone_number = os.getenv('TWILIO_PHONE_NUMBER', '+14502349148')
    print(f"Using phone number: {phone_number}")
    
    # Delete existing demo business
    cursor.execute("DELETE FROM businesses WHERE id = 'demo_salon_001'")
    print("Deleted old demo business")
    
    # Create new demo business with correct phone number
    demo_business = {
        'id': 'demo_salon_001',
        'name': 'Bella Hair Salon',
        'phone': phone_number,
        'type': 'hair_salon',
        'services': json.dumps(['haircut', 'coloring', 'styling', 'treatment', 'blowout']),
        'hours': 'Mon-Sat 9am-7pm, Closed Sunday',
        'address': '123 Main Street, Anytown, ST 12345',
        'faq_data': json.dumps({
            'hours': 'We are open Monday through Saturday 9am-7pm, closed Sunday',
            'parking': 'Free parking available in our rear lot',
            'payment': 'We accept cash, all major credit cards, and mobile payments',
            'cancellation': '24 hour notice required for cancellations to avoid fees',
            'walk_ins': 'Walk-ins welcome when stylists are available'
        }),
        'pricing_data': json.dumps({
            'haircut': '$45-65',
            'coloring': '$85-150',
            'styling': '$35-50',
            'treatment': '$60-100',
            'blowout': '$30-40'
        })
    }
    
    cursor.execute("""
        INSERT INTO businesses (id, name, phone, type, services, hours, address, faq_data, pricing_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        demo_business['id'], demo_business['name'], demo_business['phone'],
        demo_business['type'], demo_business['services'], demo_business['hours'],
        demo_business['address'], demo_business['faq_data'], demo_business['pricing_data']
    ))
    
    print("Created new demo business")
    
    # Verify the business was created
    cursor.execute("SELECT name, phone FROM businesses WHERE id = 'demo_salon_001'")
    result = cursor.fetchone()
    
    if result:
        print(f"✅ Demo business created: {result[0]} - {result[1]}")
    else:
        print("❌ Failed to create demo business")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("🔧 Fixing database phone number...")
    fix_database()
    print("✅ Database fixed! Restart your server now.")