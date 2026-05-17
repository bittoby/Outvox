#!/usr/bin/env python3
"""
Creates 5 shared SMS template variations with TCPA compliance.

Run with:
    python BE/setup_templates.py           # Create templates
    python BE/setup_templates.py --verify  # Verify templates exist
    python BE/setup_templates.py --test   # Test template rendering
"""

import os
import sys
import traceback
import pyodbc
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.template_renderer import render_template, validate_template
from config import config

load_dotenv()

SQL_SERVER = os.getenv('SQLServer')
SQL_USER = os.getenv('SQLUser')
SQL_PASSWORD = os.getenv('SQLPassword')
SQL_DATABASE = os.getenv('SQLDatabase')

# Company name is interpolated into every template at seed time. The {name}
# placeholder remains in the stored template so render_template can substitute
# the recipient's name per-send.
COMPANY_NAME = config.brand.COMPANY_NAME


def get_db_connection():
    """Get database connection."""
    try:
        if SQL_SERVER and "localdb" in SQL_SERVER.lower():
            connection_string = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={SQL_SERVER};"
                f"DATABASE={SQL_DATABASE};"
                f"Trusted_Connection=yes;"
            )
        else:
            connection_string = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={SQL_SERVER};"
                f"DATABASE={SQL_DATABASE};"
                f"UID={SQL_USER};"
                f"PWD={SQL_PASSWORD}"
            )
        return pyodbc.connect(connection_string)
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        raise

_TEMPLATE_PATTERNS = [
    ("Hi {{name}}, this is {company}. We saw your earlier inquiry and we're here if you need help with your item or loan. Reply OK for details. Reply STOP to opt out.", "Carrier-Safe Template A"),
    ("Hi {{name}}, {company} here. If you still have questions about selling or borrowing against your valuables, we're available. Reply OK if you'd like more info. Reply STOP to opt out.", "Carrier-Safe Template B"),
    ("Hi {{name}}, {company} here. Just checking in on your previous request. Let us know if you'd like to speak with a team member. Reply OK. STOP to opt out.", "Carrier-Safe Template C"),
    ("Hi {{name}}, {company} here. We're following up on your earlier message. If you'd like help or info, reply OK. STOP to opt out.", "Carrier-Safe Template D"),
    ("Hello {{name}}, this is {company}. We received your prior inquiry and wanted to see if assistance is still needed. Reply OK for information. STOP to opt out.", "Carrier-Safe Template E"),
    ("Hi {{name}}, {company} checking in regarding your earlier inquiry. If you would like us to follow up, reply OK. STOP to opt out.", "Carrier-Safe Template F"),
    ("Hello {{name}}, {company} here. We're available if you need clarification related to your earlier request. Reply OK for next steps. STOP to opt out.", "Carrier-Safe Template G"),
    ("Hi {{name}}, this is {company}. Just a brief follow-up on your prior inquiry. Reply OK if you want assistance. STOP to opt out.", "Carrier-Safe Template H"),
    ("Hello {{name}}, {company} reaching out to see if you still need information related to your request. Reply OK if so. STOP to opt out.", "Carrier-Safe Template I"),
    ("Hi {{name}}, {company} here. We're available to answer questions from your earlier message. Reply OK for help. STOP to opt out.", "Carrier-Safe Template J"),
    ("Hello {{name}}, this is {company}. Let us know if you would like assistance related to your prior inquiry. Reply OK. STOP to opt out.", "Carrier-Safe Template K"),
    ("Hi {{name}}, {company} checking back regarding your previous outreach. Reply OK if you'd like to continue. STOP to opt out.", "Carrier-Safe Template L"),
    ("Hello {{name}}, {company} here. We're standing by if you need information from your earlier request. Reply OK. STOP to opt out.", "Carrier-Safe Template M"),
    ("Hi {{name}}, this is {company}. Just confirming whether you need assistance with your earlier inquiry. Reply OK. STOP to opt out.", "Carrier-Safe Template N"),
    ("Hello {{name}}, {company} following up on your prior message. If you'd like help, reply OK. STOP to opt out.", "Carrier-Safe Template O"),
]

TEMPLATE_VARIATIONS = [
    {'template_text': pattern.format(company=COMPANY_NAME), 'description': desc}
    for pattern, desc in _TEMPLATE_PATTERNS
]


NEGATIVE_KEYWORDS = [
  # Urgency / Pressure
  "urgent","act now","today only","last chance","limited time","don’t miss",
  "expires","final notice","immediately","asap",

  # Money / Incentives
  "free","cash now","instant cash","quick cash","fast money","get paid",
  "guaranteed","approval","pre-approved","no credit check",

  # Promotional / Sales
  "offer","deal","discount","promo","promotion","special","bonus",
  "reward","coupon","save","sale",

  # Prize / Lottery / Scam Signals
  "winner","won","prize","claim","congratulations","selected","chosen",
  "gift","giveaway",

  # Links / Phishing
  "click","link","tap here","visit","open now","http","https","www",
  "short link",

  # Manipulative / Psychological Pressure
  "risk-free","no obligation","hurry","exclusive","members only",
  "secret","hidden","once in a lifetime",

  # Financial / Lending Red Flags
  "loan approval","approved","interest rate","low rate","best rate",
  "financing","borrow now","apply","application","credit",

  # Aggressive CTAs
  "call now","text now","reply now","respond now","act fast",

  # Spam / Automation Signals
  "automated","system message","bot","blast","mass text",
  "campaign","marketing","advertisement",

  # Compliance / Legal Risk
  "guarantee","guaranteed","promise","assured","binding",
  "contract","legal action","lawsuit"
]

def check_table_exists(cursor):
    """Check if sms_templates table exists."""
    cursor.execute("""
        SELECT COUNT(*) 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_NAME = 'sms_templates'
    """)
    return cursor.fetchone()[0] > 0


def setup_templates():
    """Create 5 shared SMS template variations."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if not check_table_exists(cursor):
            print("❌ Error: 'sms_templates' table does not exist!")
            print("   Start the database service first: python db_service.py")
            return
        
        print(f"Creating {len(TEMPLATE_VARIATIONS)} carrier-safe SMS template variations...\n")
        
        # First, deactivate old risky templates that contain spam trigger keywords
        risky_keywords = ['highest cash offer', 'cash loan', 'today only', 'get cash today', 'best offer today']
        cursor.execute("""
            SELECT template_id, template_name, template_content
            FROM sms_templates
            WHERE is_active = 1
        """)
        risky_templates = []
        for row in cursor.fetchall():
            template_id, template_name, template_content = row
            content_lower = template_content.lower()
            if any(keyword in content_lower for keyword in risky_keywords):
                risky_templates.append((template_id, template_name))
        
        if risky_templates:
            print(f"⚠️  Found {len(risky_templates)} risky template(s) with spam trigger keywords. Deactivating...")
            for template_id, template_name in risky_templates:
                cursor.execute("""
                    UPDATE sms_templates
                    SET is_active = 0
                    WHERE template_id = ?
                """, (template_id,))
                print(f"   ✅ Deactivated template {template_id} ({template_name})")
        
        created_count = 0
        skipped_count = 0
        
        for idx, template_data in enumerate(TEMPLATE_VARIATIONS, 1):
            template_text = template_data['template_text']
            description = template_data['description']
            
            # Validate template
            validation = validate_template(template_text)
            if validation['errors']:
                print(f"[{idx}/{len(TEMPLATE_VARIATIONS)}] ❌ {description}: Validation failed")
                continue
            
            # Check if template already exists
            cursor.execute("""
                SELECT template_id 
                FROM sms_templates 
                WHERE template_content = ?
            """, (template_text,))
            
            if cursor.fetchone():
                print(f"[{idx}/{len(TEMPLATE_VARIATIONS)}] ⚠️  {description}: Already exists - skipping")
                skipped_count += 1
            else:
                cursor.execute("""
                    INSERT INTO sms_templates (template_name, template_content, template_type, usage_count, is_active)
                    VALUES (?, ?, 'consent', 0, 1)
                """, (description, template_text))
                cursor.execute("SELECT @@IDENTITY")
                template_id = cursor.fetchone()[0]
                print(f"[{idx}/{len(TEMPLATE_VARIATIONS)}] ✅ {description}: Created (ID: {template_id})")
                created_count += 1
        
        conn.commit()
        
        print(f"\n✅ Setup complete: {created_count} created, {skipped_count} skipped")
        if risky_templates:
            print(f"   {len(risky_templates)} risky template(s) deactivated")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Setup failed: {e}")
        traceback.print_exc()
        raise
    finally:
        cursor.close()
        conn.close()


def verify_templates():
    """Verify that all templates exist and are valid."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if not check_table_exists(cursor):
            print("❌ Error: 'sms_templates' table does not exist!")
            return
        
        cursor.execute("SELECT COUNT(*) FROM sms_templates WHERE is_active = 1")
        template_count = cursor.fetchone()[0]
        
        print(f"✅ Total active templates: {template_count}")
        
        if template_count < 5:
            print(f"⚠️  WARNING: Expected at least 5 templates, found {template_count}")
        
        cursor.execute("""
            SELECT template_id, template_name, template_content
            FROM sms_templates
            WHERE is_active = 1
            ORDER BY template_id
        """)
        
        all_valid = True
        for row in cursor.fetchall():
            template_id, template_name, template_content = row
            validation = validate_template(template_content)
            
            if validation['errors']:
                print(f"  ❌ Template {template_id} ({template_name}): Invalid")
                all_valid = False
            else:
                print(f"  ✅ Template {template_id} ({template_name}): Valid")
        
        print("\n✅ All templates valid" if all_valid else "\n⚠️  Some issues found")
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def test_templates():
    """Test template rendering with sample data."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if not check_table_exists(cursor):
            print("❌ Error: 'sms_templates' table does not exist!")
            return
        
        cursor.execute("""
            SELECT template_id, template_name, template_content
            FROM sms_templates
            WHERE is_active = 1
            ORDER BY template_id
        """)
        
        templates = cursor.fetchall()
        
        if not templates:
            print("❌ No active templates found!")
            return
        
        print(f"Testing {len(templates)} template(s)...\n")
        
        test_data = {'name': 'John Smith', 'store_name': COMPANY_NAME}
        
        for template_id, template_name, template_content in templates:
            rendered = render_template(template_content, **test_data)
            print(f"Template {template_id} ({template_name}):")
            print(f"  {rendered}\n")
        
        print("✅ All templates rendered successfully")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        traceback.print_exc()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    try:
        if "--verify" in sys.argv:
            verify_templates()
        elif "--test" in sys.argv:
            test_templates()
        else:
            setup_templates()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
