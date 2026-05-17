"""
Database Schema Initialization
Handles creation of all database tables on startup.
"""

import os
import pyodbc
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Constants
PHONE_E164_PATTERN = "+1[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]"
PHONE_E164_CHECK = f"LIKE '{PHONE_E164_PATTERN}'"


def _build_connection_strings() -> Tuple[str, str]:
    """
    Build connection strings for master and target database.
    
    Returns:
        Tuple of (master_connection_string, target_connection_string)
    """
    SQL_SERVER = os.getenv('SQLServer')
    SQL_USER = os.getenv('SQLUser')
    SQL_PASSWORD = os.getenv('SQLPassword')
    SQL_DATABASE = os.getenv('SQLDatabase')
    
    if not SQL_SERVER:
        raise ValueError("SQLServer environment variable is not set")
    if not SQL_DATABASE:
        raise ValueError("SQLDatabase environment variable is not set")
    
    is_localdb = "localdb" in SQL_SERVER.lower()
    
    if is_localdb:
        # LocalDB: Use Windows Authentication
        base_conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SQL_SERVER};"
            f"Trusted_Connection=yes;"
        )
    else:
        # Remote servers: Use SQL Server authentication
        if not SQL_USER or not SQL_PASSWORD:
            raise ValueError("SQLUser and SQLPassword are required for remote SQL Server")
        base_conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SQL_SERVER};"
            f"UID={SQL_USER};"
            f"PWD={SQL_PASSWORD}"
        )
    
    master_conn_str = f"{base_conn_str}DATABASE=master;"
    target_conn_str = f"{base_conn_str}DATABASE={SQL_DATABASE};"
    
    return master_conn_str, target_conn_str


def _ensure_database_exists():
    """Ensure the target database exists, creating it if necessary."""
    SQL_DATABASE = os.getenv('SQLDatabase')
    master_conn_str, _ = _build_connection_strings()
    
    try:
        # Connect with autocommit=True for CREATE DATABASE (can't be in transaction)
        master_conn = pyodbc.connect(master_conn_str, autocommit=True)
        cursor = master_conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT name FROM sys.databases WHERE name = ?", SQL_DATABASE)
        
        if not cursor.fetchone():
            logger.info(f"Database '{SQL_DATABASE}' does not exist. Creating it...")
            cursor.execute(f"CREATE DATABASE [{SQL_DATABASE}]")
            logger.info(f"✅ Database '{SQL_DATABASE}' created successfully")
        else:
            logger.info(f"Database '{SQL_DATABASE}' already exists")
        
        cursor.close()
        master_conn.close()
    except Exception as e:
        logger.warning(f"Could not check/create database via master connection: {e}")
        # Continue anyway - maybe database already exists and we can connect directly


def get_db_connection():
    """Get database connection for schema operations."""
    _ensure_database_exists()
    _, target_conn_str = _build_connection_strings()
    
    try:
        return pyodbc.connect(target_conn_str)
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise


def _execute_sql(cursor, sql: str, description: str = None):
    """Execute SQL with error handling."""
    try:
        cursor.execute(sql)
        if description:
            logger.debug(f"Executed: {description}")
    except Exception as e:
        logger.warning(f"Error executing SQL ({description or 'unknown'}): {e}")
        raise


def _create_table_if_not_exists(cursor, table_name: str, create_sql: str):
    """Create a table if it doesn't exist."""
    sql = f"""
        IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{table_name}')
        BEGIN
            {create_sql}
        END
    """
    _execute_sql(cursor, sql, f"Create table {table_name}")


def _add_phone_constraint_if_not_exists(cursor, table_name: str, constraint_name: str):
    """Add phone E164 constraint to a table if it doesn't exist."""
    sql = f"""
        IF NOT EXISTS (
            SELECT * FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS 
            WHERE CONSTRAINT_NAME = '{constraint_name}'
        )
        BEGIN
            -- Normalize existing phone numbers if table has data
            IF EXISTS (SELECT TOP 1 1 FROM {table_name})
            BEGIN
                UPDATE {table_name}
                SET phone_number = CASE
                    WHEN phone_number LIKE '+1%' AND LEN(phone_number) = 12 THEN phone_number
                    WHEN phone_number LIKE '1%' AND LEN(REPLACE(REPLACE(REPLACE(REPLACE(phone_number, ' ', ''), '-', ''), '(', ''), ')', '')) = 11 
                        THEN '+1' + SUBSTRING(REPLACE(REPLACE(REPLACE(REPLACE(phone_number, ' ', ''), '-', ''), '(', ''), ')', ''), 2, 10)
                    WHEN LEN(REPLACE(REPLACE(REPLACE(REPLACE(phone_number, ' ', ''), '-', ''), '(', ''), ')', '')) = 10
                        THEN '+1' + REPLACE(REPLACE(REPLACE(REPLACE(phone_number, ' ', ''), '-', ''), '(', ''), ')', '')
                    ELSE phone_number
                END
                WHERE phone_number NOT {PHONE_E164_CHECK}
                  AND LEN(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(phone_number, ' ', ''), '-', ''), '(', ''), ')', ''), '+', '')) IN (10, 11)
            END
            
            -- Add constraint
            BEGIN TRY
                ALTER TABLE {table_name}
                ADD CONSTRAINT {constraint_name} 
                    CHECK (phone_number {PHONE_E164_CHECK})
            END TRY
            BEGIN CATCH
                PRINT 'WARNING: Could not add CHECK constraint. Some phone numbers may be invalid. Error: ' + ERROR_MESSAGE()
            END CATCH
        END
    """
    try:
        _execute_sql(cursor, sql, f"Add phone constraint to {table_name}")
    except Exception as e:
        logger.warning(f"Could not add CHECK constraint to {table_name}: {e}")


def _add_column_if_not_exists(cursor, table_name: str, column_name: str, column_definition: str):
    """Add a column to a table if it doesn't exist. column_definition is type + optional default (e.g. NVARCHAR(20) DEFAULT 'pending')."""
    sql = f"""
        IF NOT EXISTS (
            SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = '{table_name}' AND COLUMN_NAME = '{column_name}'
        )
        BEGIN
            ALTER TABLE {table_name} ADD [{column_name}] {column_definition}
        END
    """
    _execute_sql(cursor, sql, f"Add column {column_name} to {table_name}")


def _create_stores_table(cursor):
    """Create the stores table."""
    create_sql = """
        CREATE TABLE stores (
            store_id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(255) NOT NULL,
            location NVARCHAR(255),
            is_active BIT DEFAULT 1,
            created_at DATETIME2 DEFAULT GETDATE()
        )
        CREATE INDEX IX_stores_active ON stores(is_active)
    """
    _create_table_if_not_exists(cursor, 'stores', create_sql)


def _create_outbound_leads_table(cursor):
    """Create the OutboundLeads table."""
    create_sql = f"""
        CREATE TABLE OutboundLeads (
            lead_id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(255),
            Address NVARCHAR(255),
            City NVARCHAR(100),
            County NVARCHAR(100),
            State NVARCHAR(50),
            Zip NVARCHAR(20),
            phone_number NVARCHAR(20) UNIQUE NOT NULL,
            priority INT DEFAULT 1,
            call_count INT DEFAULT 0,
            dnc_flag BIT DEFAULT 0,
            sms_verified BIT DEFAULT 0,
            sms_verified_at DATETIME2,
            sms_consent_requested_at DATETIME2,
            sms_from_number NVARCHAR(20),
            created_at DATETIME2 DEFAULT GETDATE(),
            last_called DATETIME2,
            store_id INT,
            FOREIGN KEY (store_id) REFERENCES stores(store_id),
            CONSTRAINT CK_OutboundLeads_Phone_E164 
                CHECK (phone_number {PHONE_E164_CHECK})
        )
        CREATE INDEX IX_OutboundLeads_Phone ON OutboundLeads(phone_number)
        CREATE INDEX IX_OutboundLeads_DNC ON OutboundLeads(dnc_flag)
        CREATE INDEX IX_OutboundLeads_Store ON OutboundLeads(store_id)
        CREATE INDEX IX_OutboundLeads_Priority ON OutboundLeads(priority)
        CREATE INDEX IX_OutboundLeads_sms_from_number ON OutboundLeads(sms_from_number)
    """
    _create_table_if_not_exists(cursor, 'OutboundLeads', create_sql)
    _add_phone_constraint_if_not_exists(cursor, 'OutboundLeads', 'CK_OutboundLeads_Phone_E164')


def _create_twilio_numbers_table(cursor):
    """Create the TwilioNumbers table."""
    create_sql = f"""
        CREATE TABLE TwilioNumbers (
            number_id INT IDENTITY(1,1) PRIMARY KEY,
            phone_number NVARCHAR(20) UNIQUE NOT NULL,
            rotation_weight INT DEFAULT 1,
            is_active BIT DEFAULT 1,
            daily_sms_count INT DEFAULT 0,
            hourly_sms_count INT DEFAULT 0,
            daily_call_count INT DEFAULT 0,
            hourly_call_count INT DEFAULT 0,
            last_batch_sent_at DATETIME2,
            last_call_time DATETIME2,
            last_hourly_reset DATETIME2 DEFAULT GETDATE(),
            last_reset_date DATE DEFAULT CAST(GETDATE() AS DATE),
            store_id INT,
            assigned_at DATETIME2,
            FOREIGN KEY (store_id) REFERENCES stores(store_id),
            CONSTRAINT CK_TwilioNumbers_Phone_E164 
                CHECK (phone_number {PHONE_E164_CHECK})
        )
        CREATE INDEX IX_TwilioNumbers_Phone ON TwilioNumbers(phone_number)
        CREATE INDEX IX_TwilioNumbers_Active ON TwilioNumbers(is_active)
        CREATE INDEX IX_TwilioNumbers_Store ON TwilioNumbers(store_id)
    """
    _create_table_if_not_exists(cursor, 'TwilioNumbers', create_sql)
    _add_phone_constraint_if_not_exists(cursor, 'TwilioNumbers', 'CK_TwilioNumbers_Phone_E164')


def _create_call_results_table(cursor):
    """Create the OutboundCallResults table."""
    create_sql = """
        CREATE TABLE OutboundCallResults (
            result_id INT IDENTITY(1,1) PRIMARY KEY,
            lead_id INT NOT NULL,
            agent_id NVARCHAR(50),
            twilio_number NVARCHAR(20),
            call_sid NVARCHAR(100),
            call_duration INT DEFAULT 0,
            result_type NVARCHAR(50),
            customer_transcript NVARCHAR(MAX),
            agent_transcript NVARCHAR(MAX),
            combined_transcript NVARCHAR(MAX),
            ab_test_variant NVARCHAR(10),
            created_at DATETIME2 DEFAULT GETDATE(),
            FOREIGN KEY (lead_id) REFERENCES OutboundLeads(lead_id)
        )
        CREATE INDEX IX_CallResults_Lead ON OutboundCallResults(lead_id)
        CREATE INDEX IX_CallResults_Agent ON OutboundCallResults(agent_id)
        CREATE INDEX IX_CallResults_Created ON OutboundCallResults(created_at)
    """
    _create_table_if_not_exists(cursor, 'OutboundCallResults', create_sql)


def _create_sms_tables(cursor):
    """Create SMS-related tables."""
    # SMSConversations table
    create_sql = """
        CREATE TABLE SMSConversations (
            sms_id INT IDENTITY(1,1) PRIMARY KEY,
            lead_id INT,
            phone_number NVARCHAR(20),
            message_type NVARCHAR(50),
            message_content NVARCHAR(MAX),
            direction NVARCHAR(20),
            created_at DATETIME2 DEFAULT GETDATE(),
            twilio_sid NVARCHAR(100),
            FOREIGN KEY (lead_id) REFERENCES OutboundLeads(lead_id)
        )
        CREATE INDEX IX_SMS_Lead ON SMSConversations(lead_id)
        CREATE INDEX IX_SMS_Created ON SMSConversations(created_at)
    """
    _create_table_if_not_exists(cursor, 'SMSConversations', create_sql)
    
    # PhotoSubmissions table
    create_sql = """
        CREATE TABLE PhotoSubmissions (
            photo_id INT IDENTITY(1,1) PRIMARY KEY,
            lead_id INT NOT NULL,
            phone_number NVARCHAR(20),
            photo_url NVARCHAR(500),
            status NVARCHAR(20) DEFAULT 'pending',
            created_at DATETIME2 DEFAULT GETDATE(),
            reviewed_at DATETIME2,
            reviewed_by NVARCHAR(100),
            FOREIGN KEY (lead_id) REFERENCES OutboundLeads(lead_id)
        )
        CREATE INDEX IX_Photos_Lead ON PhotoSubmissions(lead_id)
        CREATE INDEX IX_Photos_Status ON PhotoSubmissions(status)
    """
    _create_table_if_not_exists(cursor, 'PhotoSubmissions', create_sql)


def _create_popup_queue_table(cursor):
    """Create the PopupQueue table."""
    create_sql = """
        CREATE TABLE PopupQueue (
            popup_id INT IDENTITY(1,1) PRIMARY KEY,
            lead_id INT FOREIGN KEY REFERENCES OutboundLeads(lead_id) NOT NULL,
            status NVARCHAR(20) DEFAULT 'pending',
            created_at DATETIME2 DEFAULT GETDATE(),
            dialed_at DATETIME2,
            dismissed_at DATETIME2,
            dialed_by NVARCHAR(100),
            call_sid NVARCHAR(100)
        )
        CREATE INDEX IX_PopupQueue_Lead ON PopupQueue(lead_id)
        CREATE INDEX IX_PopupQueue_Status ON PopupQueue(status)
        CREATE INDEX IX_PopupQueue_Created ON PopupQueue(created_at)
    """
    _create_table_if_not_exists(cursor, 'PopupQueue', create_sql)


def _create_sms_campaign_tables(cursor):
    """Create SMS campaign system tables."""
    # sms_campaigns table
    create_sql = """
        CREATE TABLE sms_campaigns (
            campaign_id INT IDENTITY(1,1) PRIMARY KEY,
            store_id INT NOT NULL,
            target_count INT NOT NULL,
            actual_sent INT DEFAULT 0,
            status NVARCHAR(20) DEFAULT 'pending',
            started_at DATETIME2,
            completed_at DATETIME2,
            created_at DATETIME2 DEFAULT GETDATE(),
            FOREIGN KEY (store_id) REFERENCES stores(store_id)
        )
        CREATE INDEX IX_campaigns_store ON sms_campaigns(store_id)
        CREATE INDEX IX_campaigns_status ON sms_campaigns(status)
    """
    _create_table_if_not_exists(cursor, 'sms_campaigns', create_sql)
    
    # sms_batches table
    create_sql = """
        CREATE TABLE sms_batches (
            batch_id INT IDENTITY(1,1) PRIMARY KEY,
            campaign_id INT NOT NULL,
            twilio_number_id INT,
            batch_number INT NOT NULL,
            target_count INT NOT NULL,
            actual_sent INT DEFAULT 0,
            scheduled_at DATETIME2 NOT NULL,
            status NVARCHAR(20) DEFAULT 'pending',
            started_at DATETIME2,
            completed_at DATETIME2,
            error_message NVARCHAR(MAX),
            created_at DATETIME2 DEFAULT GETDATE(),
            FOREIGN KEY (campaign_id) REFERENCES sms_campaigns(campaign_id),
            FOREIGN KEY (twilio_number_id) REFERENCES TwilioNumbers(number_id)
        )
        CREATE INDEX IX_batches_campaign ON sms_batches(campaign_id)
        CREATE INDEX IX_batches_status ON sms_batches(status)
        CREATE INDEX IX_batches_scheduled ON sms_batches(scheduled_at)
    """
    _create_table_if_not_exists(cursor, 'sms_batches', create_sql)
    
    # batch_lead_mapping table
    create_sql = """
        CREATE TABLE batch_lead_mapping (
            mapping_id INT IDENTITY(1,1) PRIMARY KEY,
            batch_id INT NOT NULL,
            lead_id INT NOT NULL,
            assigned_at DATETIME2 DEFAULT GETDATE(),
            status NVARCHAR(20) DEFAULT 'pending',
            sent_at DATETIME2 NULL,
            error_code INT NULL,
            error_message NVARCHAR(500) NULL,
            FOREIGN KEY (batch_id) REFERENCES sms_batches(batch_id),
            FOREIGN KEY (lead_id) REFERENCES OutboundLeads(lead_id),
            UNIQUE(batch_id, lead_id)
        )
        CREATE INDEX IX_mapping_batch ON batch_lead_mapping(batch_id)
        CREATE INDEX IX_mapping_lead ON batch_lead_mapping(lead_id)
        CREATE INDEX IX_mapping_status ON batch_lead_mapping(status)
    """
    _create_table_if_not_exists(cursor, 'batch_lead_mapping', create_sql)
    
    # Add columns to batch_lead_mapping if they don't exist (for existing tables)
    _add_column_if_not_exists(cursor, 'batch_lead_mapping', 'status', "NVARCHAR(20) DEFAULT 'pending'")
    _add_column_if_not_exists(cursor, 'batch_lead_mapping', 'sent_at', 'DATETIME2 NULL')
    _add_column_if_not_exists(cursor, 'batch_lead_mapping', 'error_code', 'INT NULL')
    _add_column_if_not_exists(cursor, 'batch_lead_mapping', 'error_message', 'NVARCHAR(500) NULL')
    
    # sms_templates table
    create_sql = """
        CREATE TABLE sms_templates (
            template_id INT IDENTITY(1,1) PRIMARY KEY,
            template_name NVARCHAR(255) NOT NULL,
            template_content NVARCHAR(MAX) NOT NULL,
            template_type NVARCHAR(50) DEFAULT 'consent',
            is_active BIT DEFAULT 1,
            usage_count INT DEFAULT 0,
            created_at DATETIME2 DEFAULT GETDATE(),
            updated_at DATETIME2 DEFAULT GETDATE()
        )
        CREATE INDEX IX_templates_type ON sms_templates(template_type)
        CREATE INDEX IX_templates_active ON sms_templates(is_active)
    """
    _create_table_if_not_exists(cursor, 'sms_templates', create_sql)
    
    # sms_replies table
    create_sql = """
        CREATE TABLE sms_replies (
            reply_id INT IDENTITY(1,1) PRIMARY KEY,
            lead_id INT NULL,
            from_number NVARCHAR(20) NOT NULL,
            to_number NVARCHAR(20) NOT NULL,
            body NVARCHAR(MAX) NOT NULL,
            classification NVARCHAR(10) NOT NULL CHECK (classification IN ('YES', 'STOP', 'OTHER')),
            twilio_message_sid NVARCHAR(100) NOT NULL UNIQUE,
            received_at DATETIME2 NOT NULL,
            CONSTRAINT FK_sms_replies_lead_id
                FOREIGN KEY (lead_id)
                REFERENCES OutboundLeads(lead_id)
                ON DELETE SET NULL
        )
        CREATE INDEX IX_sms_replies_lead_id ON sms_replies(lead_id)
        CREATE INDEX IX_sms_replies_from_number ON sms_replies(from_number)
        CREATE INDEX IX_sms_replies_classification ON sms_replies(classification)
        CREATE INDEX IX_sms_replies_received_at ON sms_replies(received_at DESC)
    """
    _create_table_if_not_exists(cursor, 'sms_replies', create_sql)


def _create_usage_tracking_table(cursor):
    """Create the OpenAIUsageTracking table."""
    create_sql = """
        CREATE TABLE OpenAIUsageTracking (
            usage_id INT IDENTITY(1,1) PRIMARY KEY,
            agent_id NVARCHAR(10) NOT NULL,
            call_sid NVARCHAR(50),
            lead_id INT,
            session_start DATETIME2 DEFAULT GETDATE(),
            session_end DATETIME2,
            session_duration_seconds INT,
            input_tokens INT DEFAULT 0,
            output_tokens INT DEFAULT 0,
            total_tokens INT DEFAULT 0,
            input_audio_tokens INT DEFAULT 0,
            output_audio_tokens INT DEFAULT 0,
            estimated_cost_usd DECIMAL(10,4) DEFAULT 0,
            model_name NVARCHAR(50) DEFAULT 'gpt-4o-realtime-preview',
            error_count INT DEFAULT 0,
            last_error_message NVARCHAR(MAX),
            status NVARCHAR(20) DEFAULT 'active'
        )
        CREATE INDEX IX_OpenAIUsage_Agent ON OpenAIUsageTracking(agent_id)
        CREATE INDEX IX_OpenAIUsage_CallSid ON OpenAIUsageTracking(call_sid)
        CREATE INDEX IX_OpenAIUsage_Date ON OpenAIUsageTracking(session_start)
    """
    _create_table_if_not_exists(cursor, 'OpenAIUsageTracking', create_sql)


def _create_phone_status_table(cursor):
    """Create the PhoneStatus table."""
    create_sql = f"""
        CREATE TABLE PhoneStatus (
            PhoneNumber NVARCHAR(20) PRIMARY KEY,
            LastSmsStatus NVARCHAR(20),
            LastErrorCode INT NULL,
            CarrierType NVARCHAR(20),
            LastUpdatedAt DATETIME2 DEFAULT GETDATE(),
            Total30003 INT DEFAULT 0,
            Total30005 INT DEFAULT 0,
            Total30006 INT DEFAULT 0,
            Total30007 INT DEFAULT 0,
            Total21610 INT DEFAULT 0,
            IsSmsAllowed BIT DEFAULT 1,
            IsHardBounce BIT DEFAULT 0,
            IsOptedOut BIT DEFAULT 0,
            CONSTRAINT CK_PhoneStatus_Phone_E164 
                CHECK (PhoneNumber {PHONE_E164_CHECK})
        )
        CREATE INDEX IX_PhoneStatus_Allowed ON PhoneStatus(IsSmsAllowed)
        CREATE INDEX IX_PhoneStatus_OptedOut ON PhoneStatus(IsOptedOut)
        CREATE INDEX IX_PhoneStatus_HardBounce ON PhoneStatus(IsHardBounce)
        CREATE INDEX IX_PhoneStatus_LastUpdated ON PhoneStatus(LastUpdatedAt)
    """
    _create_table_if_not_exists(cursor, 'PhoneStatus', create_sql)


def _create_phone_validation_table(cursor):
    """Create the PhoneValidation table."""
    create_sql = f"""
        CREATE TABLE PhoneValidation (
            phone_number NVARCHAR(20) PRIMARY KEY,
            is_valid BIT DEFAULT 0,
            line_type NVARCHAR(50),
            carrier NVARCHAR(255),
            is_prepaid BIT,
            is_commercial BIT,
            owner_name NVARCHAR(255),
            owner_type NVARCHAR(50),
            activity_score INT,
            contact_grade NVARCHAR(5),
            validated_at DATETIME2 DEFAULT GETDATE(),
            api_response NVARCHAR(MAX),
            CONSTRAINT CK_PhoneValidation_Phone_E164 
                CHECK (phone_number {PHONE_E164_CHECK})
        )
        CREATE INDEX IX_PhoneValidation_Valid ON PhoneValidation(is_valid)
        CREATE INDEX IX_PhoneValidation_LineType ON PhoneValidation(line_type)
        CREATE INDEX IX_PhoneValidation_ValidatedAt ON PhoneValidation(validated_at)
        CREATE INDEX IX_PhoneValidation_ActivityScore ON PhoneValidation(activity_score)
    """
    _create_table_if_not_exists(cursor, 'PhoneValidation', create_sql)
    
    # Add columns if they don't exist (for existing tables)
    _add_column_if_not_exists(cursor, 'PhoneValidation', 'activity_score', 'INT')
    _add_column_if_not_exists(cursor, 'PhoneValidation', 'contact_grade', 'NVARCHAR(5)')


def _create_system_settings_table(cursor):
    """Create the SystemSettings table."""
    create_sql = """
        CREATE TABLE SystemSettings (
            setting_key NVARCHAR(100) PRIMARY KEY,
            setting_value NVARCHAR(MAX) NOT NULL,
            updated_at DATETIME2 DEFAULT GETDATE(),
            created_at DATETIME2 DEFAULT GETDATE()
        )
    """
    _create_table_if_not_exists(cursor, 'SystemSettings', create_sql)


def _create_stored_procedures(cursor):
    """Create stored procedures for phone stats management."""
    # Drop and recreate reset_daily_phone_stats
    cursor.execute("""
        IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'reset_daily_phone_stats')
            DROP PROCEDURE reset_daily_phone_stats
    """)
    cursor.execute("""
        CREATE PROCEDURE reset_daily_phone_stats
        AS
        BEGIN
            SET NOCOUNT ON;
            UPDATE TwilioNumbers
            SET daily_sms_count = 0, daily_call_count = 0, 
                hourly_sms_count = 0, hourly_call_count = 0,
                last_hourly_reset = GETDATE()
            WHERE CAST(last_hourly_reset AS DATE) < CAST(GETDATE() AS DATE)
               OR last_hourly_reset IS NULL;
            SELECT @@ROWCOUNT as rows_reset;
        END
    """)
    
    # Drop and recreate reset_hourly_phone_stats
    cursor.execute("""
        IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'reset_hourly_phone_stats')
            DROP PROCEDURE reset_hourly_phone_stats
    """)
    cursor.execute("""
        CREATE PROCEDURE reset_hourly_phone_stats
        AS
        BEGIN
            SET NOCOUNT ON;
            UPDATE TwilioNumbers
            SET hourly_sms_count = 0, hourly_call_count = 0,
                last_hourly_reset = GETDATE()
            WHERE last_hourly_reset < DATEADD(HOUR, -1, GETDATE())
               OR last_hourly_reset IS NULL;
            SELECT @@ROWCOUNT as rows_reset;
        END
    """)


def create_outbound_tables():
    """
    Create all database tables required for the outbound calling system.
    This function is called on application startup.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        logger.info("Initializing database schema...")
        
        # Core tables (must be created in order due to foreign key dependencies)
        _create_stores_table(cursor)
        _create_outbound_leads_table(cursor)
        _create_twilio_numbers_table(cursor)
        _create_call_results_table(cursor)
        
        # SMS and photo management
        _create_sms_tables(cursor)
        _create_popup_queue_table(cursor)
        
        # SMS campaign system
        _create_sms_campaign_tables(cursor)
        
        # Usage tracking
        _create_usage_tracking_table(cursor)
        
        # Phone validation and status
        _create_phone_status_table(cursor)
        _create_phone_validation_table(cursor)
        
        # System settings
        _create_system_settings_table(cursor)
        
        # Stored procedures
        _create_stored_procedures(cursor)
        
        conn.commit()
        logger.info("✅ Database schema initialized successfully")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Error initializing database schema: {e}")
        raise
    finally:
        cursor.close()
        conn.close()
