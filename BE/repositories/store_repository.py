"""
Store Repository
Handles all database operations for stores.
"""

from typing import Optional, List, Dict, Any
from .base import BaseRepository


class StoreRepository(BaseRepository):
    """Repository for store data access."""
    
    def get_by_id(self, store_id: int) -> Optional[Dict[str, Any]]:
        """Get store by ID."""
        query = """
            SELECT store_id, name, location, is_active, created_at
            FROM stores
            WHERE store_id = ?
        """
        row = self.execute_query(query, (store_id,), fetch_one=True)
        return self._row_to_dict(row) if row else None
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all stores."""
        query = """
            SELECT store_id, name, location, is_active, created_at
            FROM stores
            ORDER BY store_id
        """
        rows = self.execute_query(query, fetch_all=True)
        return [self._row_to_dict(row) for row in rows]
    
    def create(self, store_data: Dict[str, Any]) -> int:
        """Create a new store."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO stores (name, location, is_active)
                    VALUES (?, ?, ?)
                """, (
                    store_data.get('name'),
                    store_data.get('location'),
                    store_data.get('is_active', True)
                ))
                return self.get_last_insert_id(conn)
            finally:
                cursor.close()
    
    def update(self, store_id: int, updates: Dict[str, Any]) -> bool:
        """Update an existing store."""
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            if key in ['name', 'location', 'is_active']:
                set_clauses.append(f"{key} = ?")
                params.append(value)
        
        if not set_clauses:
            return False
        
        params.append(store_id)
        query = f"UPDATE stores SET {', '.join(set_clauses)} WHERE store_id = ?"
        
        rows_affected = self.execute_non_query(query, tuple(params))
        return rows_affected > 0
    
    def delete(self, store_id: int) -> bool:
        """Delete a store."""
        query = "DELETE FROM stores WHERE store_id = ?"
        rows_affected = self.execute_non_query(query, (store_id,))
        return rows_affected > 0
    
    def get_stores_with_statistics(self) -> List[Dict[str, Any]]:
        """Get all stores with basic statistics (leads count, phone numbers count)."""
        query = """
            SELECT 
                s.store_id,
                s.name,
                s.location,
                s.is_active,
                s.created_at,
                COUNT(DISTINCT l.lead_id) as total_leads,
                COUNT(DISTINCT CASE WHEN tn.is_active = 1 OR tn.is_active IS NULL THEN tn.number_id END) as total_phone_numbers
            FROM stores s
            LEFT JOIN OutboundLeads l ON l.store_id = s.store_id
            LEFT JOIN TwilioNumbers tn ON tn.store_id = s.store_id
            GROUP BY s.store_id, s.name, s.location, s.is_active, s.created_at
            ORDER BY s.store_id
        """
        rows = self.execute_query(query, fetch_all=True)
        
        stores = []
        for row in rows:
            stores.append({
                "store_id": row[0],
                "name": row[1],
                "location": row[2],
                "is_active": bool(row[3]),
                "created_at": row[4].isoformat() if row[4] else None,
                "total_leads": row[5] or 0,
                "total_phone_numbers": row[6] or 0
            })
        return stores
    
    def get_store_with_statistics(self, store_id: int) -> Optional[Dict[str, Any]]:
        """Get store by ID with detailed statistics."""
        query = """
            SELECT 
                s.store_id,
                s.name,
                s.location,
                s.is_active,
                s.created_at,
                COUNT(DISTINCT l.lead_id) as total_leads,
                COUNT(DISTINCT CASE WHEN tn.is_active = 1 OR tn.is_active IS NULL THEN tn.number_id END) as total_phone_numbers,
                SUM(CASE WHEN l.sms_verified = 1 THEN 1 ELSE 0 END) as sms_verified_leads,
                SUM(CASE WHEN l.dnc_flag = 1 THEN 1 ELSE 0 END) as dnc_leads
            FROM stores s
            LEFT JOIN OutboundLeads l ON l.store_id = s.store_id
            LEFT JOIN TwilioNumbers tn ON tn.store_id = s.store_id
            WHERE s.store_id = ?
            GROUP BY s.store_id, s.name, s.location, s.is_active, s.created_at
        """
        row = self.execute_query(query, (store_id,), fetch_one=True)
        
        if not row:
            return None
        
        return {
            "store_id": row[0],
            "name": row[1],
            "location": row[2],
            "is_active": bool(row[3]),
            "created_at": row[4].isoformat() if row[4] else None,
            "total_leads": row[5] or 0,
            "total_phone_numbers": row[6] or 0,
            "sms_verified_leads": row[7] or 0,
            "dnc_leads": row[8] or 0
        }
    
    def get_store_usage_today(self, store_id: int) -> Dict[str, int]:
        """Get today's usage statistics for a store (SMS sent, calls made)."""
        query = """
            SELECT 
                COUNT(DISTINCT CASE WHEN l.sms_consent_requested_at >= CAST(GETDATE() AS DATE) 
                    AND l.sms_consent_requested_at < DATEADD(day, 1, CAST(GETDATE() AS DATE)) THEN l.lead_id END) as sms_sent_today,
                COUNT(DISTINCT CASE WHEN r.created_at >= CAST(GETDATE() AS DATE) 
                    AND r.created_at < DATEADD(day, 1, CAST(GETDATE() AS DATE)) THEN r.result_id END) as calls_made_today
            FROM stores s
            LEFT JOIN OutboundLeads l ON l.store_id = s.store_id
            LEFT JOIN OutboundCallResults r ON r.lead_id = l.lead_id
            WHERE s.store_id = ?
        """
        row = self.execute_query(query, (store_id,), fetch_one=True)
        
        if not row:
            return {"sms_sent_today": 0, "calls_made_today": 0}
        
        return {
            "sms_sent_today": row[0] or 0,
            "calls_made_today": row[1] or 0
        }
    
    def get_store_phone_numbers_with_health(self, store_id: int) -> List[Dict[str, Any]]:
        """Get phone numbers for a store with health status."""
        # Check if TwilioNumbers table exists
        table_exists = self.execute_scalar("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'TwilioNumbers'
        """)
        
        if table_exists == 0:
            return []
        
        # Check which columns exist
        columns_query = """
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'TwilioNumbers'
        """
        column_rows = self.execute_query(columns_query, fetch_all=True)
        existing_columns = {row[0].lower() for row in column_rows}
        
        # Build query with only columns that exist
        select_parts = ["number_id", "phone_number", "store_id"]
        
        if 'is_active' in existing_columns:
            select_parts.append("ISNULL(is_active, 1) as is_active")
        else:
            select_parts.append("1 as is_active")
        
        if 'daily_sms_count' in existing_columns:
            select_parts.append("ISNULL(daily_sms_count, 0) as daily_sms_count")
        else:
            select_parts.append("0 as daily_sms_count")
        
        if 'hourly_sms_count' in existing_columns:
            select_parts.append("ISNULL(hourly_sms_count, 0) as hourly_sms_count")
        else:
            select_parts.append("0 as hourly_sms_count")
        
        if 'daily_call_count' in existing_columns:
            select_parts.append("ISNULL(daily_call_count, 0) as daily_call_count")
        else:
            select_parts.append("0 as daily_call_count")
        
        if 'hourly_call_count' in existing_columns:
            select_parts.append("ISNULL(hourly_call_count, 0) as hourly_call_count")
        else:
            select_parts.append("0 as hourly_call_count")
        
        if 'last_batch_sent_at' in existing_columns:
            select_parts.append("last_batch_sent_at")
        else:
            select_parts.append("NULL as last_batch_sent_at")
        
        if 'last_call_time' in existing_columns:
            select_parts.append("last_call_time")
        else:
            select_parts.append("NULL as last_call_time")
        
        if 'last_hourly_reset' in existing_columns:
            select_parts.append("ISNULL(last_hourly_reset, GETDATE()) as last_hourly_reset")
        else:
            select_parts.append("GETDATE() as last_hourly_reset")
        
        query = f"""
            SELECT {', '.join(select_parts)}
            FROM TwilioNumbers
            WHERE store_id = ?
            ORDER BY phone_number
        """
        
        rows = self.execute_query(query, (store_id,), fetch_all=True)
        
        HOURLY_SMS_LIMIT = 25
        DAILY_SMS_LIMIT = 50
        DAILY_CALL_LIMIT = 60
        
        phone_numbers = []
        for row in rows:
            try:
                phone_number_id = row[0]
                phone_number = row[1]
                store_id_val = row[2]
                is_active = bool(row[3]) if row[3] is not None else True
                daily_sms_count = int(row[4]) if row[4] is not None else 0
                hourly_sms_count = int(row[5]) if row[5] is not None else 0
                daily_call_count = int(row[6]) if row[6] is not None else 0
                hourly_call_count = int(row[7]) if row[7] is not None else 0
                last_batch_sent_at = row[8]
                last_call_at = row[9]
                last_hourly_reset = row[10]
                
                # Calculate capacity percentages
                sms_capacity = max(
                    (hourly_sms_count / HOURLY_SMS_LIMIT) * 100 if HOURLY_SMS_LIMIT > 0 else 0,
                    (daily_sms_count / DAILY_SMS_LIMIT) * 100 if DAILY_SMS_LIMIT > 0 else 0
                )
                call_capacity = (daily_call_count / DAILY_CALL_LIMIT) * 100 if DAILY_CALL_LIMIT > 0 else 0
                
                # Determine health status
                if not is_active:
                    health_status = "exhausted"
                elif sms_capacity >= 95 or call_capacity >= 95:
                    health_status = "exhausted"
                elif sms_capacity >= 70 or call_capacity >= 70:
                    health_status = "warning"
                else:
                    health_status = "healthy"
                
                def safe_isoformat(dt):
                    if dt is None:
                        return None
                    try:
                        if hasattr(dt, 'isoformat'):
                            return dt.isoformat()
                        return str(dt)
                    except:
                        return None
                
                phone_numbers.append({
                    "phone_number_id": phone_number_id,
                    "phone_number": phone_number,
                    "store_id": store_id_val,
                    "is_active": is_active,
                    "daily_sms_count": daily_sms_count,
                    "hourly_sms_count": hourly_sms_count,
                    "daily_call_count": daily_call_count,
                    "hourly_call_count": hourly_call_count,
                    "last_batch_sent_at": safe_isoformat(last_batch_sent_at),
                    "last_call_at": safe_isoformat(last_call_at),
                    "last_hourly_reset": safe_isoformat(last_hourly_reset),
                    "health_status": health_status,
                    "sms_capacity_percentage": round(sms_capacity, 1),
                    "call_capacity_percentage": round(call_capacity, 1)
                })
            except Exception as e:
                print(f"Error processing phone number row: {e}")
                continue
        
        return phone_numbers
    
    def get_store_daily_stats(self, store_id: int, date: Optional[str] = None) -> Dict[str, Any]:
        """Get daily statistics for a store."""
        # If no date provided, use today
        date_filter = "CAST(GETDATE() AS DATE)" if not date else f"'{date}'"
        
        # Get store name
        store = self.get_by_id(store_id)
        if not store:
            return None
        
        store_name = store['name']
        
        # Count active phone numbers
        phone_count = self.execute_scalar("""
            SELECT COUNT(*) as phone_count
            FROM TwilioNumbers
            WHERE store_id = ?
              AND (is_active = 1 OR is_active IS NULL)
        """, (store_id,)) or 0
        
        # Get SMS stats
        sms_query = f"""
            SELECT 
                COUNT(*) as sms_sent,
                SUM(CASE WHEN l.sms_verified = 1 THEN 1 ELSE 0 END) as yes_replies,
                SUM(CASE WHEN l.dnc_flag = 1 AND l.sms_consent_requested_at >= {date_filter} THEN 1 ELSE 0 END) as stop_replies
            FROM OutboundLeads l
            WHERE l.store_id = ?
              AND l.sms_consent_requested_at >= {date_filter}
              AND l.sms_consent_requested_at < DATEADD(day, 1, {date_filter})
        """
        sms_row = self.execute_query(sms_query, (store_id,), fetch_one=True)
        sms_sent = sms_row[0] or 0 if sms_row else 0
        yes_replies = sms_row[1] or 0 if sms_row else 0
        stop_replies = sms_row[2] or 0 if sms_row else 0
        
        # Get call stats
        call_query = f"""
            SELECT 
                COUNT(*) as calls_made,
                SUM(CASE WHEN r.result_type = 'interested' THEN 1 ELSE 0 END) as interested,
                SUM(CASE WHEN r.result_type = 'not_interested' THEN 1 ELSE 0 END) as not_interested,
                SUM(CASE WHEN r.result_type = 'callback' THEN 1 ELSE 0 END) as callbacks
            FROM OutboundCallResults r
            INNER JOIN OutboundLeads l ON r.lead_id = l.lead_id
            WHERE l.store_id = ?
              AND r.created_at >= {date_filter}
              AND r.created_at < DATEADD(day, 1, {date_filter})
        """
        call_row = self.execute_query(call_query, (store_id,), fetch_one=True)
        calls_made = call_row[0] or 0 if call_row else 0
        interested = call_row[1] or 0 if call_row else 0
        not_interested = call_row[2] or 0 if call_row else 0
        callbacks = call_row[3] or 0 if call_row else 0
        
        # Get phone number stats
        phone_query = """
            SELECT 
                phone_number,
                ISNULL(daily_sms_count, 0) as daily_sms_count,
                ISNULL(daily_call_count, 0) as daily_call_count,
                is_active
            FROM TwilioNumbers
            WHERE store_id = ?
        """
        phone_rows = self.execute_query(phone_query, (store_id,), fetch_all=True)
        phone_numbers = []
        for row in phone_rows:
            phone_numbers.append({
                "phone_number": row[0],
                "sms_today": row[1] or 0,
                "calls_today": row[2] or 0,
                "status": "active" if row[3] else "inactive"
            })
        
        # Constants
        SMS_PER_NUMBER = 50
        CALLS_PER_NUMBER = 30
        sms_quota = phone_count * SMS_PER_NUMBER
        call_quota = phone_count * CALLS_PER_NUMBER
        
        return {
            "store_id": store_id,
            "store_name": store_name,
            "date": date or "today",
            "sms_sent_today": sms_sent,
            "calls_made_today": calls_made,
            "sms": {
                "sent": sms_sent,
                "quota": sms_quota,
                "remaining": max(0, sms_quota - sms_sent),
                "replies": {
                    "yes": yes_replies,
                    "stop": stop_replies
                }
            },
            "calls": {
                "made": calls_made,
                "quota": call_quota,
                "remaining": max(0, call_quota - calls_made),
                "outcomes": {
                    "interested": interested,
                    "not_interested": not_interested,
                    "callbacks": callbacks
                }
            },
            "phone_numbers": phone_numbers
        }
    
    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert database row to dictionary."""
        if not row:
            return None
        
        return {
            "store_id": row[0],
            "name": row[1],
            "location": row[2],
            "is_active": bool(row[3]),
            "created_at": row[4].isoformat() if row[4] else None
        }


