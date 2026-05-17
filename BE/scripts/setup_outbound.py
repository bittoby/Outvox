#!/usr/bin/env python3
"""
Setup script for outbound calling system.
Run this once to initialize database tables and add Twilio numbers.
"""

import os
import sys
import csv
import pyodbc
from dotenv import load_dotenv

load_dotenv()

# SQL Server configuration
SQL_SERVER = os.getenv('SQLServer')
SQL_USER = os.getenv('SQLUser')
SQL_PASSWORD = os.getenv('SQLPassword')
SQL_DATABASE = os.getenv('SQLDatabase')

def get_db_connection():
    """Get database connection."""
    try:
        # Use Windows Authentication for LocalDB
        if SQL_SERVER and "localdb" in SQL_SERVER.lower():
            connection_string = (
                f"DRIVER={{ODBC Driver 18 for SQL Server}};TrustServerCertificate=yes;"
                f"SERVER={SQL_SERVER};"
                f"DATABASE={SQL_DATABASE};"
                f"Trusted_Connection=yes;"
            )
        else:
            # Use SQL Server authentication for remote servers
            connection_string = (
                f"DRIVER={{ODBC Driver 18 for SQL Server}};TrustServerCertificate=yes;"
                f"SERVER={SQL_SERVER};"
                f"DATABASE={SQL_DATABASE};"
                f"UID={SQL_USER};"
                f"PWD={SQL_PASSWORD}"
            )
        return pyodbc.connect(connection_string)
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        raise

def setup_database():
    """Verify database tables exist (tables are created by db_service.py)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if tables exist
        tables = ['OutboundLeads', 'TwilioNumbers']
        existing_tables = []
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{table}'")
            if cursor.fetchone()[0] > 0:
                existing_tables.append(table)
        
        if len(existing_tables) == len(tables):
            print("✅ All database tables exist and are ready!")
        else:
            missing = set(tables) - set(existing_tables)
            print(f"⚠️  Missing tables: {', '.join(missing)}")
            print("💡 Start the database service first: python db_service.py")
            
    except Exception as e:
        print(f"❌ Database check failed: {e}")
    finally:
        cursor.close()
        conn.close()

def add_twilio_numbers():
    """Add your Twilio numbers to the database with store assignments.

    Populate the ``numbers`` list below with the Twilio phone numbers you have
    purchased and the store-name keyword you want each one rotated through.
    Each tuple is ``(phone_number, store_name_keyword, rotation_weight)``.

    The shipped list is intentionally empty so that running this script in a
    fresh checkout does not register placeholder numbers.

    Example::

        numbers = [
            ("+15005550006", "Downtown", 1),   # Twilio magic test number
            ("+15005550006", "Uptown", 1),
        ]
    """
    # Format: (phone_number, store_name_keyword, rotation_weight)
    numbers: list[tuple[str, str, int]] = []
    
    if not numbers:
        print("ℹ️  No Twilio numbers configured in setup_outbound.py. Edit the ")
        print("   'numbers' list in add_twilio_numbers() or assign numbers from the")
        print("   frontend Phone Numbers page after starting the system.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get all stores to map shop names to store_id
        cursor.execute("SELECT store_id, name FROM stores")
        stores = cursor.fetchall()
        store_map = {}
        for store_id, store_name in stores:
            # Create mapping: lowercase store name keywords -> store_id
            store_key = store_name.lower().replace(' store', '').replace('store', '').strip()
            store_map[store_key] = store_id

        print("Adding Twilio numbers with store assignments...")
        for phone_number, store_keyword, weight in numbers:
            try:
                # Check if number already exists
                cursor.execute("SELECT COUNT(*) FROM TwilioNumbers WHERE phone_number = ?", phone_number)
                if cursor.fetchone()[0] > 0:
                    print(f"⚠️  Number {phone_number} already exists, skipping...")
                    continue
                
                # Find store_id by matching store keyword
                store_id = None
                store_keyword_lower = store_keyword.lower()
                for key, sid in store_map.items():
                    if store_keyword_lower in key or key in store_keyword_lower:
                        store_id = sid
                        break
                
                if store_id is None:
                    print(f"⚠️  Store '{store_keyword}' not found for {phone_number}, adding without store assignment")
                
                cursor.execute("""
                    INSERT INTO TwilioNumbers (phone_number, is_active, rotation_weight, store_id)
                    VALUES (?, 1, ?, ?)
                """, phone_number, weight, store_id)
                
                store_name_display = f"store_id={store_id}" if store_id else "Unassigned"
                print(f"✅ Added {phone_number} → {store_name_display} (weight: {weight})")
            except pyodbc.IntegrityError as e:
                # This catches other constraint violations (e.g., CHECK constraint for phone format)
                error_msg = str(e)
                if "UNIQUE" in error_msg or "duplicate" in error_msg.lower():
                    print(f"⚠️  Number {phone_number} already exists, skipping...")
                else:
                    print(f"❌ Error adding {phone_number}: {error_msg}")
            except Exception as e:
                print(f"❌ Unexpected error adding {phone_number}: {e}")
        
        conn.commit()
        print("✅ Twilio numbers setup completed!")
    finally:
        cursor.close()
        conn.close()

def add_sample_leads():
    """Add sample leads for testing (optional)."""
    # Sample leads with new schema fields
    # Note: Exchange codes (digits 4-6) must not start with 0 or 1 per NANP rules
    leads = [
        # (phone, name, address, city, county, state, zip, priority, dnc_flag)
        # ("+15552345678", "John Doe", "123 Main St", "New York", "New York", "NY", "10001", 1, False),
        # ("+15552345679", "Jane Smith", "456 Oak Ave", "Los Angeles", "Los Angeles", "CA", "90210", 2, False),
        # ("+15552345680", "Bob Johnson", "789 Pine St", "Chicago", "Cook", "IL", "60601", 1, True),
        # ("+15552345681", "Alice Brown", "321 Elm St", "Houston", "Harris", "TX", "77001", 3, False),
        # ("+15552345682", "Charlie Wilson", "654 Maple Dr", "Phoenix", "Maricopa", "AZ", "85001", 1, False),
    ]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        print("Adding sample leads...")
        added_count = 0
        for phone, name, address, city, county, state, zip_code, priority, dnc_flag in leads:
            try:
                # Check if lead already exists
                cursor.execute("SELECT COUNT(*) FROM OutboundLeads WHERE phone_number = ?", phone)
                if cursor.fetchone()[0] > 0:
                    print(f"⚠️  Lead {phone} already exists, skipping...")
                    continue
                
                cursor.execute("""
                    INSERT INTO OutboundLeads (phone_number, name, Address, City, County, State, Zip, priority, dnc_flag)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, phone, name, address, city, county, state, zip_code, priority, dnc_flag)
                print(f"✅ Added: {name} - {phone} - {address}, {city}, {state}")
                added_count += 1
            except pyodbc.IntegrityError as e:
                # This catches other constraint violations (e.g., CHECK constraint for phone format)
                error_msg = str(e)
                if "UNIQUE" in error_msg or "duplicate" in error_msg.lower():
                    print(f"⚠️  Lead {phone} already exists, skipping...")
                else:
                    print(f"❌ Error adding lead {phone}: {error_msg}")
            except Exception as e:
                print(f"❌ Unexpected error adding lead {phone}: {e}")
        
        conn.commit()
        print(f"📋 Added {added_count} new sample leads")
        
    except Exception as e:
        print(f"❌ Error adding sample leads: {e}")
    finally:
        cursor.close()
        conn.close()

def import_csv_leads():
    """Import leads from CSV file."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        print("Importing leads from CSV file...")
        
        # Check if CSV file exists
        csv_file = input("Enter CSV file path (or press Enter for 'leads.csv'): ").strip()
        if not csv_file:
            csv_file = 'leads.csv'
            
        if not os.path.exists(csv_file):
            print(f"❌ {csv_file} file not found!")
            return
        
        added_count = 0
        skipped_count = 0
        
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                # Skip if no phone number
                phone = row.get('MIXPHONE') or row.get('Phone') or row.get('CellPhone')
                if not phone:
                    continue
                
                # Extract data
                name = f"{row.get('FirstName', '')} {row.get('LastName', '')}".strip()
                address = row.get('Address', '')
                city = row.get('City', '')
                county = row.get('countyname', '')
                state = row.get('State', '')
                zip_code = row.get('Zip', '')
                dnc_flag = row.get('DNC', '').upper() in ['Y', 'YES', 'TRUE', '1']
                
                try:
                    # Check if lead already exists
                    cursor.execute("SELECT COUNT(*) FROM OutboundLeads WHERE phone_number = ?", phone)
                    if cursor.fetchone()[0] > 0:
                        print(f"⚠️  Lead {phone} already exists, skipping...")
                        skipped_count += 1
                        continue
                    
                    cursor.execute("""
                        INSERT INTO OutboundLeads (phone_number, name, Address, City, County, State, Zip, priority, dnc_flag)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, phone, name, address, city, county, state, zip_code, 1, dnc_flag)
                    print(f"✅ Added: {name} - {phone} - {address}, {city}, {state}")
                    added_count += 1
                except pyodbc.IntegrityError as e:
                    # This catches other constraint violations (e.g., CHECK constraint for phone format)
                    error_msg = str(e)
                    if "UNIQUE" in error_msg or "duplicate" in error_msg.lower():
                        print(f"⚠️  Lead {phone} already exists, skipping...")
                        skipped_count += 1
                    else:
                        print(f"❌ Error adding lead {phone}: {error_msg}")
                        skipped_count += 1
                except Exception as e:
                    print(f"❌ Unexpected error adding lead {phone}: {e}")
                    skipped_count += 1
        
        conn.commit()
        print(f"📋 Import completed: {added_count} new leads, {skipped_count} skipped")
        
    except Exception as e:
        print(f"❌ Error importing CSV leads: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("🚀 OUTBOUND CALLING SYSTEM SETUP")
    print("=" * 50)
    
    # Check command line arguments
    skip_sample_data = "--no-samples" in sys.argv
    import_csv = "--import-csv" in sys.argv
    
    try:
        # Step 1: Check database
        print("\n📊 Step 1: Checking database...")
        setup_database()
        
        # Step 2: Add Twilio numbers
        print("\n📞 Step 2: Setting up Twilio numbers...")
        add_twilio_numbers()
        
        # Step 3: Add sample data
        if import_csv:
            print("\n📋 Step 3: Importing leads from CSV file...")
            import_csv_leads()
        elif skip_sample_data:
            print("\n📋 Step 3: Skipping sample leads (use --no-samples to skip them)")
        else:
            print("\n📋 Step 3: Adding sample leads...")
            add_sample_leads()
        
        print("\n✅ Setup completed successfully!")
        print("\n Setup Options:")
        print("- Default: Adds Twilio numbers + sample leads")
        print("- Use --no-samples to skip sample leads")
        print("- Use --import-csv to import leads from CSV file")
        print("- Add your own leads: python call_manager.py add-lead <phone> [name] [address] [city] [state] [zip] [priority]")
        print("\n Next Steps:")
        print("- Start database service: python db_service.py")
        print("- Start voice agents: python outbound_main.py")
        print("- Access frontend: http://localhost:3000")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        print("\n Make sure:")
        print("- Database service is running")
        print("- Environment variables are set (.env file)")
        print("- SQL Server is accessible")
