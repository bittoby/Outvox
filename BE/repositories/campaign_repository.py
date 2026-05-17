"""
Campaign Repository
Handles all database operations for SMS campaigns and batches.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from .base import BaseRepository


class CampaignRepository(BaseRepository):
    """Repository for campaign data access."""
    
    def get_by_id(self, campaign_id: int) -> Optional[Dict[str, Any]]:
        """Get campaign by ID with store information."""
        query = """
            SELECT 
                c.campaign_id,
                c.store_id,
                s.name as store_name,
                c.target_count,
                c.actual_sent,
                c.status,
                c.started_at,
                c.completed_at,
                c.created_at
            FROM sms_campaigns c
            INNER JOIN stores s ON c.store_id = s.store_id
            WHERE c.campaign_id = ?
        """
        row = self.execute_query(query, (campaign_id,), fetch_one=True)
        return self._row_to_campaign_dict(row) if row else None
    
    def get_all(
        self,
        store_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get all campaigns with optional filtering and batch summary."""
        where_clauses = []
        params = []
        
        if store_id is not None:
            where_clauses.append("c.store_id = ?")
            params.append(store_id)
        
        if status:
            where_clauses.append("c.status = ?")
            params.append(status)
        
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)
        
        # Enhanced query with batch counts and progress
        query = f"""
            SELECT TOP ({limit})
                c.campaign_id,
                c.store_id,
                s.name as store_name,
                c.target_count,
                c.actual_sent,
                c.status,
                c.started_at,
                c.completed_at,
                c.created_at,
                COUNT(b.batch_id) as batch_count,
                ISNULL(SUM(CASE WHEN b.status = 'completed' THEN 1 ELSE 0 END), 0) as completed_batches,
                ISNULL(SUM(CASE WHEN b.status = 'pending' THEN 1 ELSE 0 END), 0) as pending_batches,
                ISNULL(SUM(CASE WHEN b.status = 'executing' THEN 1 ELSE 0 END), 0) as running_batches,
                ISNULL(SUM(CASE WHEN b.status = 'failed' THEN 1 ELSE 0 END), 0) as failed_batches
            FROM sms_campaigns c
            INNER JOIN stores s ON c.store_id = s.store_id
            LEFT JOIN sms_batches b ON c.campaign_id = b.campaign_id
            {where_sql}
            GROUP BY c.campaign_id, c.store_id, s.name, c.target_count, c.actual_sent,
                     c.status, c.started_at, c.completed_at, c.created_at
            ORDER BY c.created_at DESC
        """
        
        print(f"[CampaignRepository] Query: {query}")
        print(f"[CampaignRepository] Params: {params}")
        rows = self.execute_query(query, tuple(params) if params else None, fetch_all=True)
        print(f"[CampaignRepository] Rows returned: {len(rows) if rows else 0}")
        return [self._row_to_campaign_dict_with_batches(row) for row in rows]
    
    def get_batches_by_campaign(self, campaign_id: int) -> List[Dict[str, Any]]:
        """Get all batches for a campaign."""
        query = """
            SELECT 
                b.batch_id,
                b.campaign_id,
                b.twilio_number_id,
                tn.phone_number,
                b.batch_number,
                b.target_count,
                b.actual_sent,
                b.scheduled_at,
                b.status,
                b.started_at,
                b.completed_at,
                b.error_message
            FROM sms_batches b
            LEFT JOIN TwilioNumbers tn ON b.twilio_number_id = tn.number_id
            WHERE b.campaign_id = ?
            ORDER BY b.batch_number
        """
        rows = self.execute_query(query, (campaign_id,), fetch_all=True)
        return [self._row_to_batch_dict(row) for row in rows]
    
    def get_campaign_with_batches(self, campaign_id: int) -> Optional[Dict[str, Any]]:
        """Get campaign with batch summary."""
        query = """
            SELECT 
                c.campaign_id,
                c.store_id,
                s.name as store_name,
                c.target_count,
                c.actual_sent,
                c.status,
                c.started_at,
                c.completed_at,
                c.created_at,
                COUNT(b.batch_id) as total_batches,
                SUM(CASE WHEN b.status = 'completed' THEN 1 ELSE 0 END) as completed_batches
            FROM sms_campaigns c
            INNER JOIN stores s ON c.store_id = s.store_id
            LEFT JOIN sms_batches b ON c.campaign_id = b.campaign_id
            WHERE c.campaign_id = ?
            GROUP BY c.campaign_id, c.store_id, s.name, c.target_count, c.actual_sent,
                     c.status, c.started_at, c.completed_at, c.created_at
        """
        row = self.execute_query(query, (campaign_id,), fetch_one=True)
        if not row:
            return None
        
        campaign = self._row_to_campaign_dict(row[:9])
        campaign['total_batches'] = row[9] or 0
        campaign['completed_batches'] = row[10] or 0
        return campaign
    
    def update_status(
        self,
        campaign_id: int,
        status: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ) -> bool:
        """Update campaign status."""
        set_clauses = ["status = ?"]
        params = [status]
        
        if started_at:
            set_clauses.append("started_at = ?")
            params.append(started_at)
        
        if completed_at:
            set_clauses.append("completed_at = ?")
            params.append(completed_at)
        
        params.append(campaign_id)
        query = f"UPDATE sms_campaigns SET {', '.join(set_clauses)} WHERE campaign_id = ?"
        
        rows_affected = self.execute_non_query(query, tuple(params))
        return rows_affected > 0
    
    def update_actual_sent(self, campaign_id: int, additional_sent: int) -> bool:
        """Increment actual_sent count for a campaign."""
        query = """
            UPDATE sms_campaigns
            SET actual_sent = actual_sent + ?
            WHERE campaign_id = ?
        """
        rows_affected = self.execute_non_query(query, (additional_sent, campaign_id))
        return rows_affected > 0
    
    def delete(self, campaign_id: int) -> bool:
        """Delete campaign and related batches."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Delete batch_lead_mapping records
                cursor.execute("""
                    DELETE FROM batch_lead_mapping
                    WHERE batch_id IN (
                        SELECT batch_id FROM sms_batches WHERE campaign_id = ?
                    )
                """, (campaign_id,))
                
                # Delete sms_batches records
                cursor.execute("DELETE FROM sms_batches WHERE campaign_id = ?", (campaign_id,))
                
                # Delete sms_campaigns record
                cursor.execute("DELETE FROM sms_campaigns WHERE campaign_id = ?", (campaign_id,))
                
                return cursor.rowcount > 0
            finally:
                cursor.close()
    
    def _row_to_campaign_dict(self, row) -> Dict[str, Any]:
        """Convert campaign row to dictionary."""
        if not row:
            return None
        
        return {
            "campaign_id": row[0],
            "store_id": row[1],
            "store_name": row[2],
            "target_count": row[3],
            "actual_sent": row[4],
            "status": row[5],
            "started_at": row[6].isoformat() if row[6] else None,
            "completed_at": row[7].isoformat() if row[7] else None,
            "created_at": row[8].isoformat() if row[8] else None
        }
    
    def _row_to_campaign_dict_with_batches(self, row) -> Dict[str, Any]:
        """Convert campaign row with batch counts to dictionary."""
        if not row:
            return None
        
        target_count = row[3] or 0
        actual_sent = row[4] or 0
        batch_count = row[9] or 0
        completed_batches = row[10] or 0
        
        # Calculate progress percentage
        progress_percentage = round((actual_sent / target_count * 100), 1) if target_count > 0 else 0
        
        return {
            "campaign_id": row[0],
            "store_id": row[1],
            "store_name": row[2],
            "target_count": target_count,
            "actual_sent": actual_sent,
            "status": row[5],
            "started_at": row[6].isoformat() if row[6] else None,
            "completed_at": row[7].isoformat() if row[7] else None,
            "created_at": row[8].isoformat() if row[8] else None,
            "batch_count": batch_count,
            "completed_batches": completed_batches,
            "pending_batches": row[11] or 0,
            "running_batches": row[12] or 0,
            "failed_batches": row[13] or 0,
            "progress_percentage": progress_percentage
        }
    
    def _row_to_batch_dict(self, row) -> Dict[str, Any]:
        """Convert batch row to dictionary."""
        if not row:
            return None
        
        return {
            "batch_id": row[0],
            "campaign_id": row[1],
            "twilio_number_id": row[2],
            "phone_number": row[3],
            "batch_number": row[4],
            "target_count": row[5],
            "actual_sent": row[6],
            "scheduled_at": row[7].isoformat() if row[7] else None,
            "status": row[8],
            "started_at": row[9].isoformat() if row[9] else None,
            "completed_at": row[10].isoformat() if row[10] else None,
            "error_message": row[11]
        }
    
    def get_batch_leads(self, batch_id: int) -> List[Dict[str, Any]]:
        """Get all leads for a batch with their send status and failure reasons."""
        query = """
            SELECT 
                blm.mapping_id,
                blm.batch_id,
                blm.lead_id,
                blm.status,
                blm.sent_at,
                blm.error_code,
                blm.error_message,
                l.Name,
                l.phone_number
            FROM batch_lead_mapping blm
            JOIN OutboundLeads l ON blm.lead_id = l.lead_id
            WHERE blm.batch_id = ?
            ORDER BY blm.status DESC, blm.mapping_id
        """
        rows = self.execute_query(query, (batch_id,), fetch_all=True)
        return [self._row_to_lead_mapping_dict(row) for row in rows]
    
    def _row_to_lead_mapping_dict(self, row) -> Dict[str, Any]:
        """Convert batch_lead_mapping row to dictionary."""
        if not row:
            return None
        
        return {
            "mapping_id": row[0],
            "batch_id": row[1],
            "lead_id": row[2],
            "status": row[3] or 'pending',
            "sent_at": row[4].isoformat() if row[4] else None,
            "error_code": row[5],
            "error_message": row[6],
            "lead_name": row[7],
            "phone_number": row[8]
        }
