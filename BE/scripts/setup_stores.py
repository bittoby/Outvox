"""
Seeds the ``stores`` table with sample records for development.

The data below is SAMPLE data only. Replace with your real store records
before running this script in any production environment.
"""

import sys
import os
import argparse
import pyodbc
from datetime import datetime

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

def get_db_connection():
    """Establish database connection"""
    try:
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={config.database.SQL_SERVER};"
            f"DATABASE={config.database.SQL_DATABASE};"
            f"UID={config.database.SQL_USER};"
            f"PWD={config.database.SQL_PASSWORD}"
        )
        conn = pyodbc.connect(conn_str)
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        raise


# SAMPLE store data — replace with your real stores before production use.
# Quotas (SMS and calls) are calculated dynamically from assigned phone numbers:
#   SMS quota   = phone_count * 50 per day
#   Call quota  = phone_count * 30 per day
STORES_DATA = [
    {
        'name': 'Downtown Store',
        'location': '100 Main St, Anytown, USA 00001',
        'is_active': True
    },
    {
        'name': 'Uptown Store',
        'location': '200 North Ave, Anytown, USA 00002',
        'is_active': True
    },
    {
        'name': 'Westside Store',
        'location': '300 West Blvd, Anytown, USA 00003',
        'is_active': True
    },
]


def setup_stores(clear_existing=False):
    """
    Create store records in the database.
    
    Args:
        clear_existing: If True, delete existing stores first
    """
    print(f"\n{'='*70}")
    print("🏪 STORE SETUP - MILESTONE 2")
    print(f"{'='*70}\n")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if table exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'stores'
        """)
        
        if cursor.fetchone()[0] == 0:
            print("❌ Error: 'stores' table does not exist!")
            print("   Start the database service first: python db_service.py")
            print("   The tables will be created automatically on startup.")
            return
        
        # Clear existing stores if requested
        if clear_existing:
            cursor.execute("SELECT COUNT(*) FROM stores")
            existing_count = cursor.fetchone()[0]
            
            if existing_count > 0:
                print(f"⚠️  Found {existing_count} existing stores")
                confirm = input("   Delete all existing stores? (yes/no): ")
                
                if confirm.lower() == 'yes':
                    cursor.execute("DELETE FROM stores")
                    conn.commit()
                    print(f"✅ Deleted {existing_count} existing stores\n")
                else:
                    print("❌ Cancelled. Existing stores not deleted.")
                    return
        
        # Insert stores
        inserted_count = 0
        
        for store_data in STORES_DATA:
            # Check if store already exists (by name)
            cursor.execute("SELECT store_id FROM stores WHERE name = ?", (store_data['name'],))
            existing = cursor.fetchone()
            
            if existing:
                print(f"⏭️  Store '{store_data['name']}' already exists (ID: {existing[0]})")
                continue
            
            # Insert store
            # Note: Quotas are dynamically calculated based on assigned phone numbers
            cursor.execute("""
                INSERT INTO stores (name, location, is_active, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                store_data['name'],
                store_data['location'],
                1 if store_data['is_active'] else 0,
                datetime.now()
            ))
            
            # Get inserted store_id
            cursor.execute("SELECT @@IDENTITY")
            store_id = cursor.fetchone()[0]
            
            print(f"✅ Created Store {store_id}: {store_data['name']}")
            print(f"   Location: {store_data['location']}")
            print(f"   Note: Quotas calculated dynamically (SMS: phone_count × 50, Calls: phone_count × 30)")
            print()
            
            inserted_count += 1
        
        conn.commit()
        
        # Summary
        cursor.execute("SELECT COUNT(*) FROM stores")
        total_stores = cursor.fetchone()[0]
        
        print(f"{'='*70}")
        print(f"✅ SETUP COMPLETE")
        print(f"{'='*70}")
        print(f"Stores created: {inserted_count}")
        print(f"Total stores in database: {total_stores}")
        print()
        
        # Show all stores with dynamically calculated quotas
        cursor.execute("""
            SELECT 
                s.store_id, 
                s.name, 
                s.location, 
                s.is_active,
                COUNT(tn.number_id) as phone_count
            FROM stores s
            LEFT JOIN TwilioNumbers tn ON s.store_id = tn.store_id AND (tn.is_active = 1 OR tn.is_active IS NULL)
            GROUP BY s.store_id, s.name, s.location, s.is_active
            ORDER BY s.store_id
        """)
        
        print("All Stores:")
        print("-" * 70)
        for row in cursor.fetchall():
            store_id, name, location, is_active, phone_count = row
            status = "✅ Active" if is_active else "❌ Inactive"
            sms_quota = phone_count * 50
            call_quota = phone_count * 30
            print(f"{store_id:2d}. {name:20s} | Phones: {phone_count} | SMS: {sms_quota}/day | Calls: {call_quota}/day | {status}")
        
        print()
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Setup stores for SMS Campaign System')
    parser.add_argument('--clear', action='store_true', help='Delete existing stores before setup')
    
    args = parser.parse_args()
    
    setup_stores(clear_existing=args.clear)
