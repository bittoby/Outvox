#!/usr/bin/env python3
"""
Simple script to delete all database tables.
Usage: python BE/delete_all_tables.py
"""

import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER = os.getenv('SQLServer')
SQL_USER = os.getenv('SQLUser')
SQL_PASSWORD = os.getenv('SQLPassword')
SQL_DATABASE = os.getenv('SQLDatabase')


def get_db_connection():
    """Get database connection."""
    connection_string = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};TrustServerCertificate=yes;"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={SQL_DATABASE};"
        f"UID={SQL_USER};"
        f"PWD={SQL_PASSWORD}"
    )
    return pyodbc.connect(connection_string)


def delete_all_tables():
    """Delete all tables from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Step 1: Drop all foreign key constraints
        print("Dropping foreign key constraints...")
        cursor.execute("""
            DECLARE @sql NVARCHAR(MAX) = ''
            SELECT @sql += 'ALTER TABLE [' + OBJECT_SCHEMA_NAME(parent_object_id) + '].[' + OBJECT_NAME(parent_object_id) + '] DROP CONSTRAINT [' + name + '];'
            FROM sys.foreign_keys
            EXEC sp_executesql @sql
        """)
        conn.commit()
        
        # Step 2: Get all tables
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            print("No tables found.")
            return
        
        # Step 3: Drop all tables
        print(f"Dropping {len(tables)} table(s)...")
        for table in tables:
            cursor.execute(f"DROP TABLE [{table}]")
            conn.commit()
            print(f"  ✓ {table}")
        
        print("Done. All tables deleted.")
        
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    delete_all_tables()
