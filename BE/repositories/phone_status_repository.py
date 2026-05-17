"""
Phone Status Repository
Handles all database operations for phone number status tracking.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from .base import BaseRepository


class PhoneStatusRepository(BaseRepository):
    """Repository for phone status data access."""
    
    def get_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Get phone status by phone number.
        
        Args:
            phone_number: Phone number in E.164 format
            
        Returns:
            Phone status dictionary or None if not found
        """
        query = """
            SELECT 
                PhoneNumber,
                LastSmsStatus,
                LastErrorCode,
                CarrierType,
                LastUpdatedAt,
                Total30003,
                Total30005,
                Total30006,
                Total30007,
                Total21610,
                IsSmsAllowed,
                IsHardBounce,
                IsOptedOut
            FROM PhoneStatus
            WHERE PhoneNumber = ?
        """
        row = self.execute_query(query, (phone_number,), fetch_one=True)
        return self._row_to_dict(row) if row else None
    
    def create_or_update(
        self,
        phone_number: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Create or update phone status record.
        
        Args:
            phone_number: Phone number in E.164 format
            data: Dictionary with fields to update
            
        Returns:
            True if successful
        """
        # Check if record exists
        existing = self.get_by_phone(phone_number)
        
        if existing:
            # Update existing record
            update_fields = []
            update_params = []
            
            if 'last_sms_status' in data:
                update_fields.append("LastSmsStatus = ?")
                update_params.append(data['last_sms_status'])
            
            if 'last_error_code' in data:
                update_fields.append("LastErrorCode = ?")
                update_params.append(data['last_error_code'])
            
            if 'carrier_type' in data:
                update_fields.append("CarrierType = ?")
                update_params.append(data['carrier_type'])
            
            if 'is_sms_allowed' in data:
                update_fields.append("IsSmsAllowed = ?")
                update_params.append(1 if data['is_sms_allowed'] else 0)
            
            if 'is_hard_bounce' in data:
                update_fields.append("IsHardBounce = ?")
                update_params.append(1 if data['is_hard_bounce'] else 0)
            
            if 'is_opted_out' in data:
                update_fields.append("IsOptedOut = ?")
                update_params.append(1 if data['is_opted_out'] else 0)
            
            # Always update LastUpdatedAt
            update_fields.append("LastUpdatedAt = GETDATE()")
            
            if update_fields:
                query = f"""
                    UPDATE PhoneStatus
                    SET {', '.join(update_fields)}
                    WHERE PhoneNumber = ?
                """
                update_params.append(phone_number)
                self.execute_non_query(query, tuple(update_params))
        else:
            # Create new record
            query = """
                INSERT INTO PhoneStatus (
                    PhoneNumber,
                    LastSmsStatus,
                    LastErrorCode,
                    CarrierType,
                    IsSmsAllowed,
                    IsHardBounce,
                    IsOptedOut,
                    LastUpdatedAt
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, GETDATE())
            """
            params = (
                phone_number,
                data.get('last_sms_status'),
                data.get('last_error_code'),
                data.get('carrier_type'),
                1 if data.get('is_sms_allowed', True) else 0,
                1 if data.get('is_hard_bounce', False) else 0,
                1 if data.get('is_opted_out', False) else 0
            )
            self.execute_non_query(query, params)
        
        return True
    
    def update_error(
        self,
        phone_number: str,
        error_code: int
    ) -> bool:
        """
        Update error tracking for a phone number.
        Increments the appropriate error counter and updates LastErrorCode.
        
        Args:
            phone_number: Phone number in E.164 format
            error_code: Twilio error code (30003, 30005, 30006, 30007, 21610)
            
        Returns:
            True if successful
        """
        # Map error codes to column names
        error_columns = {
            30003: 'Total30003',
            30005: 'Total30005',
            30006: 'Total30006',
            30007: 'Total30007',
            21610: 'Total21610'
        }
        
        column_name = error_columns.get(error_code)
        if not column_name:
            # Unknown error code, just update LastErrorCode
            return self.create_or_update(phone_number, {
                'last_error_code': error_code
            })
        
        # Create or update with error increment
        existing = self.get_by_phone(phone_number)
        
        if existing:
            # Update existing record - increment error counter
            query = f"""
                UPDATE PhoneStatus
                SET {column_name} = {column_name} + 1,
                    LastErrorCode = ?,
                    LastUpdatedAt = GETDATE()
                WHERE PhoneNumber = ?
            """
            self.execute_non_query(query, (error_code, phone_number))
        else:
            # Create new record with initial error count
            data = {
                'last_error_code': error_code,
                'is_sms_allowed': True
            }
            # Set the specific error counter to 1
            self.create_or_update(phone_number, data)
            
            # Now increment the counter
            query = f"""
                UPDATE PhoneStatus
                SET {column_name} = 1,
                    LastErrorCode = ?,
                    LastUpdatedAt = GETDATE()
                WHERE PhoneNumber = ?
            """
            self.execute_non_query(query, (error_code, phone_number))
        
        return True
    
    def set_suppressed(
        self,
        phone_number: str,
        reason: str,
        is_hard_bounce: bool = False,
        is_opted_out: bool = False
    ) -> bool:
        """
        Suppress a phone number (block SMS sending).
        
        Args:
            phone_number: Phone number in E.164 format
            reason: Reason for suppression ('invalid_number', 'landline', 'hard_bounce', 'opted_out', etc.)
            is_hard_bounce: Whether this is a hard bounce
            is_opted_out: Whether user opted out
            
        Returns:
            True if successful
        """
        data = {
            'is_sms_allowed': False,
            'last_sms_status': f'suppressed_{reason}'
        }
        
        if is_hard_bounce:
            data['is_hard_bounce'] = True
        
        if is_opted_out:
            data['is_opted_out'] = True
        
        return self.create_or_update(phone_number, data)
    
    def check_allowed(self, phone_number: str) -> bool:
        """
        Check if SMS is allowed for a phone number.
        
        Args:
            phone_number: Phone number in E.164 format
            
        Returns:
            True if SMS is allowed, False if blocked
        """
        status = self.get_by_phone(phone_number)
        
        if not status:
            # No record exists, allow by default
            return True
        
        # Check if SMS is explicitly not allowed
        if not status.get('is_sms_allowed', True):
            return False
        
        # Check if opted out
        if status.get('is_opted_out', False):
            return False
        
        # Check if hard bounce
        if status.get('is_hard_bounce', False):
            return False
        
        return True
    
    def _row_to_dict(self, row) -> Optional[Dict[str, Any]]:
        """Convert database row to dictionary."""
        if not row:
            return None
        
        return {
            'phone_number': row[0],
            'last_sms_status': row[1],
            'last_error_code': row[2],
            'carrier_type': row[3],
            'last_updated_at': row[4].isoformat() if row[4] else None,
            'total30003': row[5] or 0,
            'total30005': row[6] or 0,
            'total30006': row[7] or 0,
            'total30007': row[8] or 0,
            'total21610': row[9] or 0,
            'is_sms_allowed': bool(row[10]) if row[10] is not None else True,
            'is_hard_bounce': bool(row[11]) if row[11] is not None else False,
            'is_opted_out': bool(row[12]) if row[12] is not None else False
        }
    
    def get_error_counts(self, phone_number: str) -> Dict[str, int]:
        """
        Get error counts for a phone number.
        
        Args:
            phone_number: Phone number in E.164 format
            
        Returns:
            Dictionary with error counts
        """
        status = self.get_by_phone(phone_number)
        
        if not status:
            return {
                'total30003': 0,
                'total30005': 0,
                'total30006': 0,
                'total30007': 0,
                'total21610': 0
            }
        
        return {
            'total30003': status.get('total30003', 0),
            'total30005': status.get('total30005', 0),
            'total30006': status.get('total30006', 0),
            'total30007': status.get('total30007', 0),
            'total21610': status.get('total21610', 0)
        }



