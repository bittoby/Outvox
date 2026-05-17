"""
Trestle API Service
Handles phone number validation using Trestle Real Contact API.

API Documentation: https://trestle-api.redoc.ly/Current/tag/Real-Contact-API

Key Fields:
- phone.is_valid: True if phone number is valid
- phone.activity_score: 0-100 (100=active, 0=disconnected)
- phone.line_type: Mobile, Landline, FixedVOIP, NonFixedVOIP, etc.
- phone.contact_grade: A-F grade (A=best, F=bad)
- phone.name_match: True if name matches phone owner

SMS Filtering Rules:
- activity_score > 30: Number is likely active
- line_type = Mobile: Required for SMS (landlines can't receive SMS)
"""

import os
import logging
import aiohttp
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Trestle API Configuration
TRESTLE_API_KEY = os.getenv('TRESTLE_API_KEY', '')
TRESTLE_API_URL = "https://api.trestleiq.com/1.1/real_contact"  # Real Contact API

# Minimum activity score for SMS (0-100, higher = more active)
# Score <= 30 means disconnected/inactive - don't send SMS
MIN_ACTIVITY_SCORE_FOR_SMS = 30

# Line types that can receive SMS (for consent SMS, only Mobile is allowed)
SMS_CAPABLE_LINE_TYPES = ['Mobile']  # Only Mobile for SMS consent

# Line types that can receive calls
CALLABLE_LINE_TYPES = ['Mobile', 'Landline', 'NonFixedVOIP', 'FixedVOIP', 'Other']

# Cache duration for validation results (24 hours)
CACHE_DURATION_HOURS = 24


class TrestleService:
    """
    Service for phone number validation using Trestle Real Contact API.
    
    Features:
    - Validates phone number existence and activity status
    - Returns activity_score (0-100) for reachability prediction
    - Returns line_type (Mobile, Landline, VoIP, etc.)
    - Returns contact_grade (A-F) for lead quality
    - Caches results in database to minimize API calls
    
    SMS Filtering Rules:
    - activity_score > 30: Number is likely active/connected
    - line_type = Mobile: Required for SMS consent messages
    
    Usage:
        service = TrestleService.get_instance()
        result = await service.validate_phone("+12065551234")
        
        if result['is_valid'] and result['is_sms_capable']:
            # Safe to send SMS
            pass
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'TrestleService':
        """Get singleton instance of TrestleService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize Trestle service."""
        self.api_key = TRESTLE_API_KEY
        self.api_url = TRESTLE_API_URL
        
        if not self.api_key:
            logger.warning("TRESTLE_API_KEY not configured - phone validation will be skipped")
    
    def _get_db_connection(self):
        """Get database connection for caching."""
        import pyodbc
        SQL_SERVER = os.getenv('SQLServer')
        SQL_USER = os.getenv('SQLUser')
        SQL_PASSWORD = os.getenv('SQLPassword')
        SQL_DATABASE = os.getenv('SQLDatabase')
        
        connection_string = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};TrustServerCertificate=yes;"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USER};"
            f"PWD={SQL_PASSWORD}"
        )
        return pyodbc.connect(connection_string)
    
    def _normalize_phone(self, phone_number: str) -> str:
        """Normalize phone number to E.164 format for API call."""
        # Remove any non-digit characters except +
        cleaned = ''.join(c for c in phone_number if c.isdigit() or c == '+')
        
        # If starts with +1, remove + for API (API expects without +)
        if cleaned.startswith('+1'):
            return cleaned[1:]  # Return "1XXXXXXXXXX"
        elif cleaned.startswith('+'):
            return cleaned[1:]  # Remove + for other countries
        elif cleaned.startswith('1') and len(cleaned) == 11:
            return cleaned  # Already in correct format
        elif len(cleaned) == 10:
            return '1' + cleaned  # Add country code
        
        return cleaned
    
    def _to_e164(self, phone_number: str) -> str:
        """Convert phone number to E.164 format (+1XXXXXXXXXX)."""
        cleaned = ''.join(c for c in phone_number if c.isdigit())
        
        if len(cleaned) == 10:
            return f"+1{cleaned}"
        elif len(cleaned) == 11 and cleaned.startswith('1'):
            return f"+{cleaned}"
        elif phone_number.startswith('+'):
            return phone_number
        
        return f"+{cleaned}"
    
    def _get_cached_result(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Get cached validation result from database.
        
        Args:
            phone_number: Phone number in E.164 format
            
        Returns:
            Cached result dict or None if not found/expired
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Check if we have a recent cached result
            cursor.execute("""
                SELECT 
                    is_valid, line_type, carrier, is_prepaid, is_commercial,
                    owner_name, owner_type, validated_at, activity_score, contact_grade
                FROM PhoneValidation
                WHERE phone_number = ?
                  AND validated_at > DATEADD(hour, -?, GETDATE())
            """, (phone_number, CACHE_DURATION_HOURS))
            
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if row:
                activity_score = row[8] if len(row) > 8 else None
                line_type = row[1]
                
                # Determine SMS capability based on activity_score and line_type
                is_sms_capable = (
                    line_type == 'Mobile' and 
                    (activity_score is None or activity_score > MIN_ACTIVITY_SCORE_FOR_SMS)
                )
                
                return {
                    'is_valid': bool(row[0]),
                    'line_type': line_type,
                    'carrier': row[2],
                    'is_prepaid': bool(row[3]) if row[3] is not None else None,
                    'is_commercial': bool(row[4]) if row[4] is not None else None,
                    'owner_name': row[5],
                    'owner_type': row[6],
                    'validated_at': row[7],
                    'activity_score': activity_score,
                    'contact_grade': row[9] if len(row) > 9 else None,
                    'is_sms_capable': is_sms_capable,
                    'cached': True
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting cached validation: {e}")
            return None
    
    def _save_to_cache(self, phone_number: str, result: Dict[str, Any]) -> bool:
        """
        Save validation result to database cache.
        
        Args:
            phone_number: Phone number in E.164 format
            result: Validation result dict
            
        Returns:
            bool: Success status
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Upsert the validation result (including activity_score and contact_grade)
            cursor.execute("""
                MERGE PhoneValidation AS target
                USING (SELECT ? AS phone_number) AS source
                ON target.phone_number = source.phone_number
                WHEN MATCHED THEN
                    UPDATE SET 
                        is_valid = ?,
                        line_type = ?,
                        carrier = ?,
                        is_prepaid = ?,
                        is_commercial = ?,
                        owner_name = ?,
                        owner_type = ?,
                        activity_score = ?,
                        contact_grade = ?,
                        validated_at = GETDATE(),
                        api_response = ?
                WHEN NOT MATCHED THEN
                    INSERT (phone_number, is_valid, line_type, carrier, is_prepaid, 
                            is_commercial, owner_name, owner_type, activity_score, contact_grade,
                            validated_at, api_response)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?);
            """, (
                phone_number,
                # UPDATE values
                result.get('is_valid', False),
                result.get('line_type'),
                result.get('carrier'),
                result.get('is_prepaid'),
                result.get('is_commercial'),
                result.get('owner_name'),
                result.get('owner_type'),
                result.get('activity_score'),
                result.get('contact_grade'),
                result.get('api_response'),
                # INSERT values
                phone_number,
                result.get('is_valid', False),
                result.get('line_type'),
                result.get('carrier'),
                result.get('is_prepaid'),
                result.get('is_commercial'),
                result.get('owner_name'),
                result.get('owner_type'),
                result.get('activity_score'),
                result.get('contact_grade'),
                result.get('api_response')
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving validation to cache: {e}")
            return False
    
    async def validate_phone(
        self, 
        phone_number: str, 
        skip_cache: bool = False,
        name: str = None
    ) -> Dict[str, Any]:
        """
        Validate a phone number using Trestle Real Contact API.
        
        Args:
            phone_number: Phone number to validate
            skip_cache: If True, bypass cache and make fresh API call
            name: Optional name to pass to API for better matching
            
        Returns:
            Dict with validation results:
            {
                'phone_number': str,
                'is_valid': bool,
                'is_sms_capable': bool,
                'is_callable': bool,
                'line_type': str,
                'activity_score': int,
                'contact_grade': str,
                'warnings': list,
                'error': str (if failed),
                'cached': bool
            }
        """
        # Normalize to E.164 for storage
        e164_phone = self._to_e164(phone_number)
        
        # Check if API key is configured
        if not self.api_key:
            logger.warning(f"Trestle API key not configured, skipping validation for {e164_phone}")
            return {
                'phone_number': e164_phone,
                'is_valid': True,  # Assume valid if no API key
                'is_sms_capable': True,
                'is_callable': True,
                'line_type': 'Unknown',
                'carrier': None,
                'warnings': ['Trestle API key not configured - validation skipped'],
                'cached': False
            }
        
        # Check cache first (unless skip_cache is True)
        if not skip_cache:
            cached = self._get_cached_result(e164_phone)
            if cached:
                logger.info(f"Using cached validation for {e164_phone}: activity_score={cached.get('activity_score')}, line_type={cached.get('line_type')}")
                # Add computed fields
                cached['phone_number'] = e164_phone
                cached['is_callable'] = cached.get('line_type') in CALLABLE_LINE_TYPES
                cached['warnings'] = []
                return cached
        
        # Make API call to Real Contact API
        try:
            api_phone = self._normalize_phone(phone_number)
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'x-api-key': self.api_key,
                    'Accept': 'application/json'
                }
                # Real Contact API requires name parameter for phone validation
                params = {
                    'phone': api_phone,
                    'name': name or 'Unknown'  # API requires name parameter
                }
                
                logger.info(f"Calling Trestle Real Contact API: {self.api_url} with phone={api_phone}, name={name or 'Unknown'}")
                
                async with session.get(
                    self.api_url,
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_text = await response.text()
                    logger.info(f"Trestle API response status={response.status}, body={response_text[:500]}")
                    
                    if response.status == 200:
                        import json
                        data = json.loads(response_text)
                        return self._parse_response(e164_phone, data)
                    
                    elif response.status == 400:
                        error_text = await response.text()
                        logger.warning(f"Trestle API bad request for {e164_phone}: {error_text}")
                        return {
                            'phone_number': e164_phone,
                            'is_valid': False,
                            'is_sms_capable': False,
                            'is_callable': False,
                            'line_type': None,
                            'carrier': None,
                            'error': f"Invalid phone number: {error_text}",
                            'warnings': ['API returned bad request'],
                            'cached': False
                        }
                    
                    elif response.status == 429:
                        logger.error("Trestle API rate limit exceeded")
                        return {
                            'phone_number': e164_phone,
                            'is_valid': True,  # Don't block on rate limit
                            'is_sms_capable': True,
                            'is_callable': True,
                            'line_type': 'Unknown',
                            'carrier': None,
                            'error': 'Rate limit exceeded',
                            'warnings': ['Rate limit exceeded - validation skipped'],
                            'cached': False
                        }
                    
                    else:
                        error_text = await response.text()
                        logger.error(f"Trestle API error {response.status}: {error_text}")
                        return {
                            'phone_number': e164_phone,
                            'is_valid': True,  # Don't block on API error
                            'is_sms_capable': True,
                            'is_callable': True,
                            'line_type': 'Unknown',
                            'carrier': None,
                            'error': f"API error: {response.status}",
                            'warnings': [f'API error {response.status} - validation skipped'],
                            'cached': False
                        }
                        
        except asyncio.TimeoutError:
            logger.error(f"Trestle API timeout for {e164_phone}")
            return {
                'phone_number': e164_phone,
                'is_valid': True,  # Don't block on timeout
                'is_sms_capable': True,
                'is_callable': True,
                'line_type': 'Unknown',
                'carrier': None,
                'error': 'API timeout',
                'warnings': ['API timeout - validation skipped'],
                'cached': False
            }
            
        except Exception as e:
            logger.error(f"Trestle API error for {e164_phone}: {e}")
            return {
                'phone_number': e164_phone,
                'is_valid': True,  # Don't block on error
                'is_sms_capable': True,
                'is_callable': True,
                'line_type': 'Unknown',
                'carrier': None,
                'error': str(e),
                'warnings': [f'Validation error: {e}'],
                'cached': False
            }
    
    def _parse_response(self, phone_number: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Trestle Real Contact API response and save to cache.
        
        Real Contact API Response Format:
        {
            "phone.is_valid": true,
            "phone.activity_score": 57,
            "phone.line_type": "Mobile",
            "phone.name_match": true,
            "phone.contact_grade": "A",
            ...
        }
        
        Args:
            phone_number: Phone number in E.164 format
            data: Raw API response
            
        Returns:
            Parsed validation result
        """
        import json
        
        # Real Contact API uses dot notation for phone fields
        # Note: API returns 'phone.linetype' (lowercase), not 'phone.line_type'
        is_valid = data.get('phone.is_valid')
        activity_score = data.get('phone.activity_score')  # 0-100
        line_type = data.get('phone.linetype', 'Unknown')  # lowercase 'linetype'
        contact_grade = data.get('phone.contact_grade')  # A-F
        name_match = data.get('phone.name_match')
        
        # Handle None values - if is_valid is None, treat as unknown
        if is_valid is None:
            is_valid = False
        
        # Parse warnings
        warnings = data.get('warnings', [])
        if warnings is None:
            warnings = []
        
        # Determine SMS capability based on activity_score AND line_type
        # SMS is only allowed for Mobile numbers with activity_score > 30
        is_sms_capable = (
            line_type == 'Mobile' and 
            (activity_score is None or activity_score > MIN_ACTIVITY_SCORE_FOR_SMS)
        )
        
        is_callable = line_type in CALLABLE_LINE_TYPES
        
        # Add warnings based on validation results
        if not is_valid:
            warnings.append('Phone number is invalid')
        
        if activity_score is not None and activity_score <= MIN_ACTIVITY_SCORE_FOR_SMS:
            warnings.append(f'Low activity score ({activity_score}) - number may be disconnected/inactive')
        
        if line_type == 'Landline':
            warnings.append('Landline number - cannot receive SMS')
        elif line_type == 'NonFixedVOIP':
            warnings.append('NonFixedVOIP number - not allowed for SMS consent')
        elif line_type == 'FixedVOIP':
            warnings.append('FixedVOIP number - not allowed for SMS consent')
        elif line_type != 'Mobile':
            warnings.append(f'{line_type} number - only Mobile allowed for SMS consent')
        
        if contact_grade in ['E', 'F']:
            warnings.append(f'Low contact grade ({contact_grade}) - lead quality is poor')
        
        result = {
            'phone_number': phone_number,
            'is_valid': is_valid,
            'is_sms_capable': is_sms_capable,
            'is_callable': is_callable,
            'line_type': line_type,
            'activity_score': activity_score,
            'contact_grade': contact_grade,
            'name_match': name_match,
            'carrier': None,  # Real Contact API doesn't return carrier
            'is_prepaid': None,
            'is_commercial': None,
            'owner_name': None,
            'owner_type': None,
            'warnings': warnings,
            'cached': False,
            'api_response': json.dumps(data)  # Store raw response for debugging
        }
        
        # Log validation result
        logger.info(f"Trestle Real Contact validation for {phone_number}: "
                   f"valid={is_valid}, activity_score={activity_score}, "
                   f"line_type={line_type}, contact_grade={contact_grade}, "
                   f"is_sms_capable={is_sms_capable}")
        
        # Save to cache
        self._save_to_cache(phone_number, result)
        
        return result
    
    async def validate_phones_bulk(
        self, 
        phone_numbers: List[str],
        skip_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Validate multiple phone numbers.
        
        Args:
            phone_numbers: List of phone numbers to validate
            skip_cache: If True, bypass cache
            
        Returns:
            Dict with bulk validation results
        """
        results = []
        valid_count = 0
        invalid_count = 0
        sms_capable_count = 0
        
        for phone in phone_numbers:
            result = await self.validate_phone(phone, skip_cache)
            results.append(result)
            
            if result.get('is_valid'):
                valid_count += 1
            else:
                invalid_count += 1
            
            if result.get('is_sms_capable'):
                sms_capable_count += 1
        
        return {
            'success': True,
            'total': len(phone_numbers),
            'valid_count': valid_count,
            'invalid_count': invalid_count,
            'sms_capable_count': sms_capable_count,
            'results': results
        }
    
    def validate_phone_sync(self, phone_number: str, skip_cache: bool = False, name: str = None) -> Dict[str, Any]:
        """
        Synchronous wrapper for validate_phone.
        Use this when calling from synchronous code.
        
        Args:
            phone_number: Phone number to validate
            skip_cache: If True, bypass cache
            name: Optional name to pass to API for better matching
            
        Returns:
            Validation result dict
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, create a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run, 
                        self.validate_phone(phone_number, skip_cache, name)
                    )
                    return future.result(timeout=15)
            else:
                return loop.run_until_complete(self.validate_phone(phone_number, skip_cache, name))
        except Exception as e:
            logger.error(f"Sync validation error: {e}")
            # Return permissive result on error
            return {
                'phone_number': self._to_e164(phone_number),
                'is_valid': True,
                'is_sms_capable': True,
                'is_callable': True,
                'line_type': 'Unknown',
                'carrier': None,
                'error': str(e),
                'warnings': [f'Sync validation error: {e}'],
                'cached': False
            }


def get_trestle_service() -> TrestleService:
    """Get singleton instance of TrestleService."""
    return TrestleService.get_instance()
