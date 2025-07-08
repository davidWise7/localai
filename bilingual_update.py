# bilingual_update.py - Make demo business bilingual
import sqlite3
import json
from dotenv import load_dotenv

load_dotenv()

def update_business_bilingual():
    """Update demo business to be bilingual French/English"""
    
    conn = sqlite3.connect("localai.db")
    cursor = conn.cursor()
    
    # Bilingual business data
    bilingual_business = {
        'name': 'Bella Hair Salon / Salon de Coiffure Bella',
        'hours': 'Lun-Sam 9h-19h, Fermé Dimanche / Mon-Sat 9am-7pm, Closed Sunday',
        'address': '123 rue Principale, Anytown, QC H1H 1H1 / 123 Main Street, Anytown, QC H1H 1H1',
        'faq_data': json.dumps({
            'hours_fr': 'Nous sommes ouverts du lundi au samedi de 9h à 19h, fermés le dimanche',
            'hours_en': 'We are open Monday through Saturday 9am-7pm, closed Sunday',
            'parking_fr': 'Stationnement gratuit disponible dans notre lot arrière',
            'parking_en': 'Free parking available in our rear lot',
            'payment_fr': 'Nous acceptons comptant, toutes les cartes de crédit principales, et paiements mobiles',
            'payment_en': 'We accept cash, all major credit cards, and mobile payments',
            'cancellation_fr': 'Préavis de 24 heures requis pour les annulations afin d\'éviter les frais',
            'cancellation_en': '24 hour notice required for cancellations to avoid fees',
            'walk_ins_fr': 'Clients sans rendez-vous bienvenus selon disponibilité des stylistes',
            'walk_ins_en': 'Walk-ins welcome when stylists are available'
        }),
        'pricing_data': json.dumps({
            'haircut_fr': '45$-65$ / Coupe de cheveux',
            'haircut_en': '$45-65 / Haircut',
            'coloring_fr': '85$-150$ / Coloration',
            'coloring_en': '$85-150 / Coloring',
            'styling_fr': '35$-50$ / Coiffage',
            'styling_en': '$35-50 / Styling',
            'treatment_fr': '60$-100$ / Traitement',
            'treatment_en': '$60-100 / Treatment'
        })
    }
    
    # Update the business
    cursor.execute("""
        UPDATE businesses 
        SET name = ?, hours = ?, address = ?, faq_data = ?, pricing_data = ?
        WHERE id = 'demo_salon_001'
    """, (
        bilingual_business['name'],
        bilingual_business['hours'], 
        bilingual_business['address'],
        bilingual_business['faq_data'],
        bilingual_business['pricing_data']
    ))
    
    conn.commit()
    
    # Verify update
    cursor.execute("SELECT name, hours FROM businesses WHERE id = 'demo_salon_001'")
    result = cursor.fetchone()
    
    if result:
        print(f"✅ Business updated: {result[0]}")
        print(f"✅ Hours: {result[1]}")
    
    conn.close()
    print("🇫🇷 Demo business is now bilingual!")

if __name__ == "__main__":
    update_business_bilingual()