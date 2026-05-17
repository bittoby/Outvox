"""
Phone Number Repository
Handles all database operations for Twilio phone numbers.
"""

from typing import Optional, List, Dict, Any
from .base import BaseRepository


class PhoneNumberRepository(BaseRepository):
    """Repository for phone number data access."""
    
    def get_by_id(self, number_id: int) -> Optional[Dict[str, Any]]:
        """Get phone number by ID."""
        query = """
            SELECT 
                tn.number_id,
                tn.phone_number,
                tn.store_id,
                s.name as store_name,
                tn.is_active,
                ISNULL(tn.daily_sms_count, 0) as daily_sms_count,
                ISNULL(tn.hourly_sms_count, 0) as hourly_sms_count,
                ISNULL(tn.daily_call_count, 0) as daily_call_count,
                ISNULL(tn.hourly_call_count, 0) as hourly_call_count,
                tn.last_batch_sent_at,
                tn.last_call_time,
                tn.last_hourly_reset
            FROM TwilioNumbers tn
            LEFT JOIN stores s ON tn.store_id = s.store_id
            WHERE tn.number_id = ?
        """
        row = self.execute_query(query, (number_id,), fetch_one=True)
        return self._row_to_dict(row) if row else None
    
    def get_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get phone number by phone number string."""
        query = """
            SELECT 
                tn.number_id,
                tn.phone_number,
                tn.store_id,
                s.name as store_name,
                tn.is_active,
                ISNULL(tn.daily_sms_count, 0) as daily_sms_count,
                ISNULL(tn.hourly_sms_count, 0) as hourly_sms_count,
                ISNULL(tn.daily_call_count, 0) as daily_call_count,
                ISNULL(tn.hourly_call_count, 0) as hourly_call_count,
                tn.last_batch_sent_at,
                tn.last_call_time,
                tn.last_hourly_reset
            FROM TwilioNumbers tn
            LEFT JOIN stores s ON tn.store_id = s.store_id
            WHERE tn.phone_number = ?
        """
        row = self.execute_query(query, (phone_number,), fetch_one=True)
        return self._row_to_dict(row) if row else None
    
    def get_all(self, store_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all phone numbers with optional store filter."""
        where_clause = ""
        params = []
        
        if store_id is not None:
            where_clause = "WHERE tn.store_id = ?"
            params.append(store_id)
        
        query = f"""
            SELECT 
                tn.number_id,
                tn.phone_number,
                tn.store_id,
                s.name as store_name,
                tn.is_active,
                ISNULL(tn.daily_sms_count, 0) as daily_sms_count,
                ISNULL(tn.hourly_sms_count, 0) as hourly_sms_count,
                ISNULL(tn.daily_call_count, 0) as daily_call_count,
                ISNULL(tn.hourly_call_count, 0) as hourly_call_count,
                tn.last_batch_sent_at,
                tn.last_call_time,
                tn.last_hourly_reset
            FROM TwilioNumbers tn
            LEFT JOIN stores s ON tn.store_id = s.store_id
            {where_clause}
            ORDER BY tn.phone_number
        """
        
        rows = self.execute_query(query, tuple(params) if params else None, fetch_all=True)
        return [self._row_to_dict(row) for row in rows]
    
    def assign_to_store(self, number_id: int, store_id: Optional[int]) -> bool:
        """Assign phone number to a store (or unassign if store_id is None)."""
        query = """
            UPDATE TwilioNumbers
            SET store_id = ?, assigned_at = GETDATE()
            WHERE number_id = ?
        """
        rows_affected = self.execute_non_query(query, (store_id, number_id))
        return rows_affected > 0
    
    def update_active_status(self, number_id: int, is_active: bool) -> bool:
        """Update phone number active status."""
        query = """
            UPDATE TwilioNumbers
            SET is_active = ?
            WHERE number_id = ?
        """
        rows_affected = self.execute_non_query(query, (is_active, number_id))
        return rows_affected > 0
    
    def delete(self, number_id: int) -> bool:
        """Delete a phone number."""
        query = "DELETE FROM TwilioNumbers WHERE number_id = ?"
        rows_affected = self.execute_non_query(query, (number_id,))
        return rows_affected > 0
    
    def count_by_store(self, store_id: int) -> int:
        """Count phone numbers assigned to a store."""
        query = """
            SELECT COUNT(*)
            FROM TwilioNumbers
            WHERE store_id = ? AND (is_active = 1 OR is_active IS NULL)
        """
        return self.execute_scalar(query, (store_id,)) or 0
    
    def count_active_numbers(self, store_id: Optional[int] = None) -> int:
        """
        Count active phone numbers.
        
        Args:
            store_id: Optional store ID filter. If None, counts unassigned active numbers.
            
        Returns:
            Count of active phone numbers
        """
        try:
            if store_id is not None:
                query = """
                    SELECT COUNT(*)
                    FROM TwilioNumbers
                    WHERE store_id = ? AND ISNULL(is_active, 1) = 1
                """
                result = self.execute_scalar(query, (store_id,))
                return int(result) if result is not None else 0
            else:
                # Count unassigned active numbers
                query = """
                    SELECT COUNT(*)
                    FROM TwilioNumbers
                    WHERE store_id IS NULL AND ISNULL(is_active, 1) = 1
                """
                result = self.execute_scalar(query)
                return int(result) if result is not None else 0
        except Exception as e:
            print(f"Error counting active numbers (store_id={store_id}): {e}")
            return 0
    
    def get_available_numbers(self, store_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get available phone numbers (under limits).
        
        CRITICAL: When store_id is provided, ONLY returns numbers assigned to that store.
        When store_id is None, this method should NOT be used for consent SMS.
        """
        # CRITICAL: Use explicit query structure that absolutely prevents NULL store_id
        if store_id is not None:
            # When store_id is provided, use explicit WHERE clause that filters by store_id
            # AND excludes NULL values in a way that SQL Server cannot bypass
            query = """
                SELECT 
                    number_id,
                    phone_number,
                    store_id,
                    ISNULL(daily_sms_count, 0) as daily_sms_count,
                    ISNULL(daily_call_count, 0) as daily_call_count
                FROM TwilioNumbers
                WHERE is_active = 1
                  AND (daily_sms_count < 50 OR daily_sms_count IS NULL)
                  AND (daily_call_count < 30 OR daily_call_count IS NULL)
                  AND store_id IS NOT NULL
                  AND store_id = ?
                ORDER BY daily_sms_count ASC, daily_call_count ASC
            """
            params = (store_id,)
        else:
            # When store_id is None, still exclude unassigned numbers
            query = """
                SELECT 
                    number_id,
                    phone_number,
                    store_id,
                    ISNULL(daily_sms_count, 0) as daily_sms_count,
                    ISNULL(daily_call_count, 0) as daily_call_count
                FROM TwilioNumbers
                WHERE is_active = 1
                  AND (daily_sms_count < 50 OR daily_sms_count IS NULL)
                  AND (daily_call_count < 30 OR daily_call_count IS NULL)
                  AND store_id IS NOT NULL
                ORDER BY daily_sms_count ASC, daily_call_count ASC
            """
            params = None
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[PhoneNumberRepo] Executing query with store_id={store_id} (type: {type(store_id)})")
        logger.info(f"[PhoneNumberRepo] Query: {query}")
        logger.info(f"[PhoneNumberRepo] Params: {params}")
        
        rows = self.execute_query(query, params, fetch_all=True)
        
        # Log results and validate
        logger.info(f"[PhoneNumberRepo] Query returned {len(rows) if rows else 0} rows")
        if rows:
            for row in rows[:10]:  # Log first 10 rows
                row_store_id = row[2]  # store_id is 3rd column (index 2)
                logger.info(f"[PhoneNumberRepo] Row: phone={row[1]}, store_id={row_store_id} (type: {type(row_store_id)})")
                
                # CRITICAL: Validate each row before returning
                if store_id is not None:
                    if row_store_id is None:
                        logger.error(f"[PhoneNumberRepo] ❌ CRITICAL: Query returned NULL store_id for phone {row[1]} when filtering by store_id={store_id}")
                    elif row_store_id != store_id:
                        logger.error(f"[PhoneNumberRepo] ❌ CRITICAL: Query returned wrong store_id={row_store_id} for phone {row[1]} when filtering by store_id={store_id}")
        
        # Build result list with explicit validation
        result = []
        for row in rows:
            row_store_id = row[2]
            # CRITICAL: Filter out any rows with NULL or wrong store_id
            if store_id is not None:
                if row_store_id is None or row_store_id != store_id:
                    logger.error(f"[PhoneNumberRepo] ❌ FILTERING OUT: phone={row[1]}, store_id={row_store_id} (expected: {store_id})")
                    continue  # Skip this row
            
            result.append({
                "phone_number_id": row[0],
                "number_id": row[0],
                "phone_number": row[1],
                "store_id": row_store_id,
                "daily_sms_count": row[3] or 0,
                "daily_call_count": row[4] or 0
            })
        
        logger.info(f"[PhoneNumberRepo] Returning {len(result)} validated numbers (filtered from {len(rows) if rows else 0} rows)")
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics for all phone numbers."""
        query = """
            SELECT 
                COUNT(*) as total_numbers,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_numbers,
                SUM(ISNULL(daily_sms_count, 0)) as total_sms_today,
                SUM(ISNULL(daily_call_count, 0)) as total_calls_today,
                AVG(CAST(ISNULL(daily_sms_count, 0) as FLOAT)) as avg_sms_per_number,
                AVG(CAST(ISNULL(daily_call_count, 0) as FLOAT)) as avg_calls_per_number
            FROM TwilioNumbers
        """
        row = self.execute_query(query, fetch_one=True)
        
        if not row:
            return {
                "total_numbers": 0,
                "active_numbers": 0,
                "total_sms_today": 0,
                "total_calls_today": 0,
                "avg_sms_per_number": 0,
                "avg_calls_per_number": 0
            }
        
        return {
            "total_numbers": row[0] or 0,
            "active_numbers": row[1] or 0,
            "total_sms_today": row[2] or 0,
            "total_calls_today": row[3] or 0,
            "avg_sms_per_number": round(row[4], 2) if row[4] else 0,
            "avg_calls_per_number": round(row[5], 2) if row[5] else 0
        }
    
    def create(self, phone_number: str, rotation_weight: int = 1, store_id: Optional[int] = None) -> int:
        """Create a new phone number."""
        query = """
            INSERT INTO TwilioNumbers (phone_number, rotation_weight, is_active, store_id)
            VALUES (?, ?, 1, ?)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO TwilioNumbers (phone_number, rotation_weight, is_active, store_id) VALUES (?, ?, 1, ?)",
                    (phone_number, rotation_weight, store_id)
                )
                return self.get_last_insert_id(conn)
            finally:
                cursor.close()
    
    def update_usage(self, phone_number: str) -> bool:
        """
        Update usage count and timestamp for a phone number.
        
        This increments:
        - daily_call_count (resets daily)
        - hourly_call_count (resets hourly)
        - last_call_time (timestamp)
        
        Note: total_calls_made column does not exist in the schema
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"[PhoneNumberRepo] Executing update_usage for {phone_number}")
            
            # NOTE: total_calls_made column does NOT exist in the schema
            # Only update columns that actually exist: daily_call_count, hourly_call_count, last_call_time
            query = """
                UPDATE TwilioNumbers 
                SET daily_call_count = ISNULL(daily_call_count, 0) + 1, 
                    hourly_call_count = ISNULL(hourly_call_count, 0) + 1,
                    last_call_time = GETDATE()
                WHERE phone_number = ?
            """
            
            logger.info(f"[PhoneNumberRepo] Query: {query}")
            logger.info(f"[PhoneNumberRepo] Parameters: ({phone_number},)")
            
            rows_affected = self.execute_non_query(query, (phone_number,))
            
            # Log the update for debugging
            if rows_affected > 0:
                logger.info(f"[PhoneNumberRepo] ✅ Updated usage for {phone_number} (rows affected: {rows_affected})")
            else:
                logger.warning(f"[PhoneNumberRepo] ⚠️ No rows updated for {phone_number} - number may not exist")
                # Try to check if the number exists
                check_query = "SELECT phone_number FROM TwilioNumbers WHERE phone_number = ?"
                check_result = self.execute_query(check_query, (phone_number,), fetch_one=True)
                if check_result:
                    logger.warning(f"[PhoneNumberRepo] ⚠️ Number exists but UPDATE didn't affect any rows - possible database issue")
                else:
                    logger.warning(f"[PhoneNumberRepo] ⚠️ Number does not exist in database")
            
            return rows_affected > 0
        except Exception as e:
            logger.error(f"[PhoneNumberRepo] ❌ Error in update_usage for {phone_number}: {e}")
            import traceback
            logger.error(f"[PhoneNumberRepo] Traceback: {traceback.format_exc()}")
            raise
    
    def set_rotation_weight(self, phone_number: str, weight: int) -> bool:
        """Set rotation weight for a phone number."""
        query = """
            UPDATE TwilioNumbers 
            SET rotation_weight = ?
            WHERE phone_number = ?
        """
        rows_affected = self.execute_non_query(query, (weight, phone_number))
        return rows_affected > 0
    
    def delete_by_phone(self, phone_number: str) -> bool:
        """Delete a phone number by phone number string."""
        query = "DELETE FROM TwilioNumbers WHERE phone_number = ?"
        rows_affected = self.execute_non_query(query, (phone_number,))
        return rows_affected > 0
    
    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert database row to dictionary."""
        if not row:
            return None
        
        return {
            "phone_number_id": row[0],  # Keep as phone_number_id for frontend compatibility
            "number_id": row[0],  # Also include as number_id
            "phone_number": row[1],
            "store_id": row[2] if row[2] is not None else None,
            "store_name": row[3] if row[3] is not None else None,
            "is_active": bool(row[4]),
            "daily_sms_count": row[5] or 0,
            "hourly_sms_count": row[6] or 0,
            "daily_call_count": row[7] or 0,
            "hourly_call_count": row[8] or 0,
            "last_batch_sent_at": row[9].isoformat() if row[9] else None,
            "last_call_time": row[10].isoformat() if row[10] else None,
            "last_hourly_reset": row[11].isoformat() if row[11] else None
        }


