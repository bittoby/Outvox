"""
Analytics Service
Business logic for analytics and statistics.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from repositories.call_repository import CallRepository
from repositories.lead_repository import LeadRepository
from repositories.phone_number_repository import PhoneNumberRepository
from repositories.store_repository import StoreRepository
from core.exceptions import ValidationError


class AnalyticsService:
    """Service for analytics business logic."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'AnalyticsService':
        """Get singleton instance of AnalyticsService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize service with repositories."""
        self.call_repository = CallRepository()
        self.lead_repository = LeadRepository()
        self.phone_repository = PhoneNumberRepository()
    
    def get_call_stats(self) -> Dict[str, Any]:
        """
        Get statistics about outbound calling for today.
        
        Returns:
            Dict with call statistics, phone number usage, and pending leads
        """
        # Get today's call stats
        today = datetime.now().date()
        
        query = """
            SELECT 
                COUNT(*) as total_calls,
                SUM(CASE WHEN result_type = 'interested' THEN 1 ELSE 0 END) as interested,
                SUM(CASE WHEN result_type = 'not_interested' THEN 1 ELSE 0 END) as not_interested,
                SUM(CASE WHEN result_type = 'dnc' THEN 1 ELSE 0 END) as dnc,
                SUM(CASE WHEN result_type = 'callback' THEN 1 ELSE 0 END) as callback
            FROM OutboundCallResults 
            WHERE CAST(created_at AS DATE) = CAST(GETDATE() AS DATE)
        """
        
        stats_row = self.call_repository.execute_query(query, fetch_one=True)
        
        # Get phone number usage with store names
        phone_query = """
            SELECT 
                tn.phone_number, 
                tn.daily_call_count, 
                tn.last_call_time, 
                tn.rotation_weight, 
                tn.is_active,
                tn.store_id,
                s.name as store_name
            FROM TwilioNumbers tn
            LEFT JOIN stores s ON tn.store_id = s.store_id
            ORDER BY tn.is_active DESC, tn.rotation_weight DESC, tn.daily_call_count ASC
        """
        
        phone_rows = self.phone_repository.execute_query(phone_query, fetch_all=True)
        
        # Get pending leads count
        pending_query = "SELECT COUNT(*) FROM OutboundLeads WHERE dnc_flag = 0"
        pending = self.lead_repository.execute_scalar(pending_query) or 0
        
        # Calculate active numbers count
        active_numbers = sum(1 for row in phone_rows if row[4] == 1)  # is_active
        
        return {
            'total_calls': stats_row[0] or 0 if stats_row else 0,
            'interested': stats_row[1] or 0 if stats_row else 0,
            'not_interested': stats_row[2] or 0 if stats_row else 0,
            'dnc': stats_row[3] or 0 if stats_row else 0,
            'callback': stats_row[4] or 0 if stats_row else 0,
            'pending_leads': pending,
            'active_twilio_numbers': active_numbers,
            'numbers': [
                {
                    'phone': row[0],
                    'daily_calls': row[1],
                    'last_call': row[2].isoformat() if row[2] else None,
                    'rotation_weight': row[3],
                    'is_active': bool(row[4]),
                    'shop': row[6] if row[6] else 'Unassigned'
                } for row in phone_rows
            ]
        }
    
    def get_priority_stats(self) -> Dict[str, Any]:
        """
        Get lead count by priority level.
        
        Returns:
            Dict with priority distribution
        """
        # Check total leads
        total_query = "SELECT COUNT(*) FROM OutboundLeads"
        total_leads = self.lead_repository.execute_scalar(total_query) or 0
        
        if total_leads == 0:
            return {
                "high_priority": 0,
                "medium_priority": 0,
                "low_priority": 0,
                "total": 0
            }
        
        # Get priority distribution
        priority_query = """
            SELECT 
                COALESCE(priority, 1) as priority,
                COUNT(*) as count
            FROM OutboundLeads 
            WHERE dnc_flag = 0 OR dnc_flag IS NULL
            GROUP BY COALESCE(priority, 1)
            ORDER BY COALESCE(priority, 1)
        """
        
        rows = self.lead_repository.execute_query(priority_query, fetch_all=True)
        
        # Initialize priority stats
        priority_stats = {
            "1": 0,  # High priority
            "2": 0,  # Medium priority  
            "3": 0   # Low priority
        }
        
        for row in rows:
            priority = str(row[0]) if row[0] is not None else "1"
            count = row[1] if row[1] is not None else 0
            
            try:
                priority_num = int(priority)
                if priority_num in [1, 2, 3]:
                    priority_stats[str(priority_num)] = count
                else:
                    priority_stats["1"] += count
            except (ValueError, TypeError):
                priority_stats["1"] += count
        
        return {
            "high_priority": priority_stats["1"],
            "medium_priority": priority_stats["2"], 
            "low_priority": priority_stats["3"],
            "total": sum(priority_stats.values())
        }
    
    def get_store_locations(self) -> Dict[str, Any]:
        """
        Return store locations with today's call counts.

        Data flows from two sources:

        * Store metadata (id/name/address/phone/hours) comes from the configured
          ``STORE_LOCATIONS`` map in ``utils/location_mapper.py``. Operators
          should keep that map in sync with their real footprint, or replace
          this helper with one that reads the ``stores`` table directly.
        * Today's call counts come from ``OutboundCallResults`` joined to
          ``OutboundLeads``, aggregated per store using the lead's
          ``store_id``. Stores with no calls today report ``calls_today=0``.
        """
        from utils.location_mapper import STORE_LOCATIONS

        # Per-store call counts for today.
        per_store_query = """
            SELECT ol.store_id, COUNT(*) AS call_count
            FROM OutboundCallResults ocr
            INNER JOIN OutboundLeads ol ON ocr.lead_id = ol.lead_id
            WHERE CAST(ocr.created_at AS DATE) = CAST(GETDATE() AS DATE)
              AND ol.store_id IS NOT NULL
            GROUP BY ol.store_id
        """
        per_store_rows = self.call_repository.execute_query(per_store_query, fetch_all=True)
        per_store_calls: Dict[int, int] = {
            row[0]: row[1] for row in per_store_rows if row[0] is not None
        }

        # Map STORE_LOCATIONS keys to store_id values from the ``stores`` table
        # when possible, so the analytics page reflects real call activity.
        try:
            store_id_rows = self.call_repository.execute_query(
                "SELECT store_id, name FROM stores WHERE is_active = 1",
                fetch_all=True,
            ) or []
        except Exception:
            store_id_rows = []
        store_id_by_name = {
            (row[1] or '').strip().lower(): row[0] for row in store_id_rows
        }

        locations = []
        for key, store in STORE_LOCATIONS.items():
            store_id = store_id_by_name.get(store['name'].strip().lower())
            calls_today = per_store_calls.get(store_id, 0) if store_id else 0
            locations.append({
                "id": key,
                "name": store['name'],
                "address": store['address'],
                "phone": store.get('phone', ''),
                "hours": ", ".join(filter(None, [
                    store.get('hours_weekdays'),
                    store.get('hours_saturday'),
                    store.get('hours_sunday'),
                ])),
                "status": "open",
                "calls_today": calls_today,
            })

        return {
            "locations": locations,
            "total_calls_today": sum(per_store_calls.values()) if per_store_calls else 0,
        }


    def get_sms_timeline(
        self, 
        store_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get SMS sending timeline for analytics charts.
        
        Args:
            store_id: Optional filter by store ID
            start_date: Start date (default: 7 days ago)
            end_date: End date (default: today)
            
        Returns:
            Dict with timeline data
        """
        # Set defaults
        if end_date is None:
            end_date = datetime.now().date()
        if start_date is None:
            start_date = end_date - timedelta(days=7)
        
        # Build store filter
        store_filter = ""
        params = [start_date, end_date]
        
        if store_id is not None:
            store_filter = "AND ol.store_id = ?"
            params.append(store_id)
        
        # Get SMS sent by date
        sms_query = f"""
            SELECT 
                CAST(sms_consent_requested_at AS DATE) as date,
                COUNT(*) as sms_count
            FROM OutboundLeads ol
            WHERE CAST(sms_consent_requested_at AS DATE) BETWEEN ? AND ?
              AND sms_consent_requested_at IS NOT NULL
              {store_filter}
            GROUP BY CAST(sms_consent_requested_at AS DATE)
            ORDER BY date
        """
        
        sms_rows = self.lead_repository.execute_query(sms_query, tuple(params), fetch_all=True)
        sms_by_date = {row[0]: row[1] for row in sms_rows} if sms_rows else {}
        
        # Get replies by date
        params_replies = [start_date, end_date]
        if store_id is not None:
            params_replies.append(store_id)
        
        replies_by_date = {}
        # Check if sms_replies table exists and get replies
        try:
            replies_query = f"""
                SELECT 
                    CAST(sr.received_at AS DATE) as date,
                    COUNT(*) as reply_count
                FROM sms_replies sr
                JOIN OutboundLeads ol ON sr.lead_id = ol.lead_id
                WHERE CAST(sr.received_at AS DATE) BETWEEN ? AND ?
                  AND sr.classification = 'YES'
                  {store_filter}
                GROUP BY CAST(sr.received_at AS DATE)
                ORDER BY date
            """
            reply_rows = self.lead_repository.execute_query(replies_query, tuple(params_replies), fetch_all=True)
            replies_by_date = {row[0]: row[1] for row in reply_rows} if reply_rows else {}
        except Exception:
            # Table may not exist
            pass
        
        # Get calls by date
        params_calls = [start_date, end_date]
        if store_id is not None:
            params_calls.append(store_id)
        
        calls_query = f"""
            SELECT 
                CAST(ocr.created_at AS DATE) as date,
                COUNT(*) as call_count
            FROM OutboundCallResults ocr
            JOIN OutboundLeads ol ON ocr.lead_id = ol.lead_id
            WHERE CAST(ocr.created_at AS DATE) BETWEEN ? AND ?
              {store_filter}
            GROUP BY CAST(ocr.created_at AS DATE)
            ORDER BY date
        """
        call_rows = self.call_repository.execute_query(calls_query, tuple(params_calls), fetch_all=True)
        calls_by_date = {row[0]: row[1] for row in call_rows} if call_rows else {}
        
        # Build timeline with all dates in range
        timeline = []
        current_date = start_date
        while current_date <= end_date:
            timeline.append({
                'date': str(current_date),
                'sms_sent': sms_by_date.get(current_date, 0),
                'replies_received': replies_by_date.get(current_date, 0),
                'calls_made': calls_by_date.get(current_date, 0)
            })
            current_date += timedelta(days=1)
        
        return {'timeline': timeline}
    
    def get_daily_report(self, target_date: datetime) -> Dict[str, Any]:
        """
        Get daily report for all stores.
        
        Args:
            target_date: Date for the report
            
        Returns:
            Dict with daily report data
        """
        store_repo = StoreRepository()
        
        # Get all active stores
        stores_query = """
            SELECT store_id, name
            FROM stores
            WHERE is_active = 1
            ORDER BY store_id
        """
        store_rows = store_repo.execute_query(stores_query, fetch_all=True)
        
        stores_data = []
        total_sms = 0
        total_calls = 0
        total_replies = 0
        stores_active = 0
        
        for store_row in store_rows or []:
            store_id = store_row[0]
            store_name = store_row[1]
            
            # Count SMS for this store
            sms_query = """
                SELECT COUNT(*) as sms_count
                FROM OutboundLeads
                WHERE store_id = ?
                  AND CAST(sms_consent_requested_at AS DATE) = ?
            """
            sms_row = self.lead_repository.execute_query(sms_query, (store_id, target_date), fetch_one=True)
            sms_count = sms_row[0] or 0 if sms_row else 0
            
            # Count calls for this store
            calls_query = """
                SELECT COUNT(*) as call_count
                FROM OutboundCallResults ocr
                JOIN OutboundLeads ol ON ocr.lead_id = ol.lead_id
                WHERE ol.store_id = ?
                  AND CAST(ocr.created_at AS DATE) = ?
            """
            call_row = self.call_repository.execute_query(calls_query, (store_id, target_date), fetch_one=True)
            call_count = call_row[0] or 0 if call_row else 0
            
            # Count replies by classification
            yes_replies = 0
            stop_replies = 0
            other_replies = 0
            
            try:
                replies_query = """
                    SELECT 
                        SUM(CASE WHEN reply_classification = 'YES' THEN 1 ELSE 0 END) as yes_count,
                        SUM(CASE WHEN reply_classification = 'STOP' THEN 1 ELSE 0 END) as stop_count,
                        SUM(CASE WHEN reply_classification = 'OTHER' THEN 1 ELSE 0 END) as other_count
                    FROM sms_replies sr
                    JOIN OutboundLeads ol ON sr.lead_id = ol.lead_id
                    WHERE ol.store_id = ?
                      AND CAST(sr.received_at AS DATE) = ?
                """
                reply_row = self.lead_repository.execute_query(replies_query, (store_id, target_date), fetch_one=True)
                if reply_row:
                    yes_replies = reply_row[0] or 0
                    stop_replies = reply_row[1] or 0
                    other_replies = reply_row[2] or 0
            except Exception:
                # Table may not exist
                pass
            
            store_total_replies = yes_replies + stop_replies + other_replies
            
            if sms_count > 0 or call_count > 0:
                stores_active += 1
            
            total_sms += sms_count
            total_calls += call_count
            total_replies += store_total_replies
            
            stores_data.append({
                'store_id': store_id,
                'store_name': store_name,
                'sms_sent': sms_count,
                'calls_made': call_count,
                'replies_yes': yes_replies,
                'replies_stop': stop_replies,
                'replies_other': other_replies
            })
        
        # Calculate reply rate
        reply_rate = 0.0
        if total_sms > 0:
            reply_rate = round((total_replies / total_sms) * 100, 1)
        
        return {
            'date': str(target_date),
            'summary': {
                'total_sms_sent': total_sms,
                'total_calls_made': total_calls,
                'total_replies': total_replies,
                'reply_rate': reply_rate,
                'stores_active': stores_active
            },
            'stores': stores_data
        }


def get_analytics_service() -> AnalyticsService:
    """Get singleton instance of AnalyticsService."""
    return AnalyticsService.get_instance()

