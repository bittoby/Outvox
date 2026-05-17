"""
Lead Management Router
Handles all lead-related API endpoints using service layer.
"""

import os
import pyodbc
import csv
import io
import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Response, Query

from models import (
    LeadCreate, LeadUpdate, BulkAssignRequest, DNCARequest,
    CSVImportRequest, BulkLeadRequest, ConsentSMSRequest,
    ConsentSMSBatchRequest, SMSVerificationRequest
)
from services.lead_service import get_lead_service, LeadService
from core.exceptions import ResourceNotFoundError, ValidationError, DatabaseError

logger = logging.getLogger(__name__)

# Router instance
# Main router with /leads prefix
router = APIRouter(prefix="/api/leads", tags=["leads"])

# Database connection helper
def get_db_connection():
    """Get database connection."""
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


# Dependency injection
def get_service() -> LeadService:
    """Dependency injection for LeadService."""
    return get_lead_service()


# ============================================================================
# GET ENDPOINTS
# ============================================================================

@router.get("", summary="Get all leads")
async def get_all_leads(
    limit: int = 100,
    offset: int = 0,
    dnc_only: Optional[bool] = None,
    filter: Optional[str] = None,
    store_id: Optional[int] = None,
    service: LeadService = Depends(get_service)
):
    """
    Get all leads with pagination and filtering.
    
    Filters:
    - dnc_only: Filter by DNC status
    - filter='unassigned': Get leads with no store_id assigned
    - filter='store_id': Get leads by specific store (requires store_id param)
    - store_id: The store ID to filter by
    """
    unassigned_only = filter == "unassigned"
    
    if filter == "store_id" and store_id is None:
        raise ValidationError("store_id required when filter='store_id'")
    
    # Let exceptions bubble up to global handler
    return service.get_leads(
        limit=limit,
        offset=offset,
        dnc_only=dnc_only,
        store_id=store_id,
        unassigned_only=unassigned_only
    )


@router.get("/next", summary="Get next lead to call")
async def get_next_lead(service: LeadService = Depends(get_service)):
    """Get the next available lead for calling (not DNC, not called today)."""
    # Let exceptions bubble up to global handler
    return service.get_next_lead()


@router.get("/export-csv", summary="Export leads to CSV format")
async def export_leads_to_csv_endpoint(
    dnc_only: Optional[str] = Query(default=None, description="Filter by DNC status (true/false)"),
    limit: Optional[int] = Query(default=None, description="Maximum number of leads to export"),
    service: LeadService = Depends(get_service)
):
    """Export leads to CSV format."""
    # Convert string boolean to bool if provided
    dnc_only_bool = None
    if dnc_only is not None and dnc_only.strip():
        dnc_only_lower = dnc_only.lower().strip()
        dnc_only_bool = dnc_only_lower in ('true', '1', 'yes', 'on')
    
    leads = service.export_leads_to_csv(dnc_only=dnc_only_bool, limit=limit)
    
    # Convert to CSV
    csv_content = _export_leads_to_csv(leads)
    
    # Return as CSV response
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=leads-export-{datetime.now().strftime('%Y-%m-%d')}.csv"
        }
    )


@router.get("/{lead_id}", summary="Get lead by ID")
async def get_lead_by_id(lead_id: int, service: LeadService = Depends(get_service)):
    """Get a specific lead by ID."""
    # Let exceptions bubble up to global handler
    lead = service.get_lead(lead_id)
    return {"success": True, "lead": lead}


@router.get("/by-phone/{phone_number}", summary="Get lead by phone number")
async def get_lead_by_phone(phone_number: str, service: LeadService = Depends(get_service)):
    """Get a lead by phone number."""
    # Let exceptions bubble up to global handler
    lead = service.get_lead_by_phone(phone_number)
    if lead:
        return {"success": True, "lead": lead}
    else:
        return {"success": False, "message": "Lead not found", "lead": None}


@router.get("/multiple", summary="Get multiple leads for parallel calling")
async def get_multiple_leads(count: int = 10, service: LeadService = Depends(get_service)):
    """Get multiple different leads for parallel calling."""
    # Let exceptions bubble up to global handler
    return service.get_multiple_leads(count)


# ============================================================================
# POST ENDPOINTS
# ============================================================================

@router.post("", summary="Create new lead")
async def create_lead(lead: LeadCreate, service: LeadService = Depends(get_service)):
    """Create a new lead."""
    # Let exceptions bubble up to global handler
    return service.create_lead(lead.dict())


@router.post("/add", summary="Add lead (alternative endpoint)")
async def add_lead(lead: LeadCreate, service: LeadService = Depends(get_service)):
    """Add a new lead (alternative endpoint for compatibility)."""
    return await create_lead(lead, service)


@router.post("/{lead_id}/mark-called", summary="Mark lead as called")
async def mark_lead_called(lead_id: int, service: LeadService = Depends(get_service)):
    """
    Mark a lead as called (update last_called timestamp only).
    
    ⚠️ NOTE: This does NOT increment call_count.
    call_count is incremented when the call result is saved via save_call_result().
    This prevents double-counting.
    """
    # Let exceptions bubble up to global handler
    return service.mark_lead_called(lead_id)


@router.post("/{lead_id}/update", summary="Update lead")
async def update_lead(lead_id: int, lead: LeadUpdate, service: LeadService = Depends(get_service)):
    """Update an existing lead."""
    # Let exceptions bubble up to global handler
    updates = {k: v for k, v in lead.dict().items() if v is not None}
    return service.update_lead(lead_id, updates)


@router.post("/{lead_id}/delete", summary="Delete lead")
async def delete_lead(lead_id: int, service: LeadService = Depends(get_service)):
    """Delete a lead."""
    # Let exceptions bubble up to global handler
    return service.delete_lead(lead_id)


# ============================================================================
# DELETE ENDPOINTS
# ============================================================================

@router.delete("/all", summary="Delete all leads")
async def delete_all_leads():
    """Delete all leads from the database. Use with caution!"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Delete related data first (in order to respect foreign key constraints)
        # Order matters: delete child records before parent records
        
        # 1. Delete call results (references lead_id)
        cursor.execute("DELETE FROM OutboundCallResults")
        call_results_deleted = cursor.rowcount
        
        # 2. Delete photo submissions (references lead_id)
        cursor.execute("DELETE FROM PhotoSubmissions")
        photos_deleted = cursor.rowcount
        
        # 3. Delete popup queue entries (references lead_id)
        cursor.execute("DELETE FROM PopupQueue")
        popup_deleted = cursor.rowcount
        
        # 4. Delete batch lead mappings (references lead_id)
        cursor.execute("DELETE FROM batch_lead_mapping")
        batch_mapping_deleted = cursor.rowcount
        
        # 5. Delete SMS conversations with lead_id (lead_id can be NULL, so only delete where it's not NULL)
        cursor.execute("DELETE FROM SMSConversations WHERE lead_id IS NOT NULL")
        sms_deleted = cursor.rowcount
        
        # 6. Finally, delete all leads
        cursor.execute("DELETE FROM OutboundLeads")
        deleted_count = cursor.rowcount
        
        conn.commit()
        
        return {
            "success": True,
            "message": f"Deleted {deleted_count} lead(s) and related data",
            "deleted_count": deleted_count,
            "related_data_deleted": {
                "call_results": call_results_deleted,
                "photo_submissions": photos_deleted,
                "popup_queue": popup_deleted,
                "batch_mappings": batch_mapping_deleted,
                "sms_conversations": sms_deleted
            }
        }
    except Exception as e:
        conn.rollback()
        raise DatabaseError(f"Error deleting all leads: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@router.post("/mark-dnc", summary="Mark lead as Do Not Call")
async def mark_lead_dnc(dnc_request: DNCARequest, service: LeadService = Depends(get_service)):
    """Mark a lead as Do Not Call."""
    # Let exceptions bubble up to global handler
    return service.mark_lead_dnc(dnc_request.phone_number)


@router.post("/{lead_id}/request-consent", summary="Send consent SMS to a specific lead")
async def request_consent_for_lead(
    lead_id: int,
    payload: ConsentSMSRequest = ConsentSMSRequest(),
    service: LeadService = Depends(get_service)
):
    """Send consent SMS to a specific lead."""
    return service.send_consent_sms(lead_id, payload.message, payload.force)


@router.post("/request-consent-batch", summary="Send consent SMS to a batch of eligible leads")
async def request_consent_batch(
    payload: ConsentSMSBatchRequest,
    service: LeadService = Depends(get_service)
):
    """
    Send consent SMS to a batch of eligible leads.
    
    Eligibility criteria (matching campaign logic):
    - dnc_flag = 0
    - sms_verified = 0 (unless force=True)
    - sms_consent_requested_at IS NULL OR sms_consent_requested_at < DATEADD(day, -7, GETDATE())
    - store_id matches (if provided)
    - Ordered by priority, then created_at
    """
    return service.send_consent_sms_batch(
        limit=payload.limit or 100,
        store_id=payload.store_id,
        message=payload.message,
        force=payload.force
    )


@router.post("/sms-verify", summary="Update SMS verification status for a lead")
async def update_sms_verification(
    payload: SMSVerificationRequest,
    service: LeadService = Depends(get_service)
):
    """Update SMS verification status for a lead."""
    return service.update_sms_verification(
        lead_id=payload.lead_id,
        phone_number=payload.phone_number,
        verified=payload.verified,
        mark_dnc=payload.mark_dnc,
        source=payload.source or "manual"
    )


@router.post("/bulk", summary="Bulk import leads")
async def bulk_import_leads(
    request: BulkLeadRequest,
    service: LeadService = Depends(get_service)
):
    """Bulk import leads."""
    # Convert leads to dict format if needed
    leads = []
    for lead in request.leads:
        if isinstance(lead, dict):
            leads.append(lead)
        else:
            leads.append({
                'name': getattr(lead, 'name', None),
                'Address': getattr(lead, 'Address', None),
                'City': getattr(lead, 'City', None),
                'County': getattr(lead, 'County', None),
                'State': getattr(lead, 'State', None),
                'Zip': getattr(lead, 'Zip', None),
                'phone_number': getattr(lead, 'phone_number', None),
                'priority': getattr(lead, 'priority', 1)
            })
    
    return service.bulk_create_leads(leads)


@router.post("/import-csv", summary="Import leads from CSV content")
async def import_leads_from_csv(
    request: CSVImportRequest,
    service: LeadService = Depends(get_service)
):
    """
    Import leads from CSV content.
    
    ⚠️ CRITICAL: NO SMS IS SENT DURING IMPORT ⚠️
    - Leads are saved with sms_verified=FALSE
    - store_id is set to NULL (assigned in Milestone 4)
    - NO Twilio API calls are made
    
    Returns validation summary with success/failed/duplicate counts.
    """
    logger.info("=" * 70)
    logger.info("LEAD IMPORT STARTED - NO SMS WILL BE SENT")
    logger.info("=" * 70)
    
    result = service.import_leads_from_csv(request.csv_content)
    
    logger.info("=" * 70)
    logger.info(f"✅ LEAD IMPORT COMPLETED - NO SMS SENT")
    logger.info(f"  - Successfully imported: {result['success']}")
    logger.info(f"  - Failed: {result['failed']}")
    logger.info(f"  - Duplicates skipped: {result['duplicates']}")
    
    # Log detailed errors if any
    if result.get('errors'):
        logger.warning(f"  - Errors: {result['errors']}")
    if result.get('invalid_rows'):
        for invalid_row in result['invalid_rows']:
            logger.warning(f"  - Row {invalid_row.get('row', '?')}: {invalid_row.get('error', 'Unknown error')} (Phone: {invalid_row.get('phone', 'N/A')})")
    
    logger.info("=" * 70)
    
    return result


@router.put("/bulk-assign", summary="Bulk assign leads to a store")
async def bulk_assign_leads_to_store(
    request: BulkAssignRequest,
    service: LeadService = Depends(get_service)
):
    """
    Bulk assign leads to a store.
    
    Milestone 4: Lead Store Assignment
    
    Safety:
    - Validates store_id exists
    - Validates all lead_ids exist
    - Skips leads with dnc_flag=1 (DNC list)
    - NO SMS SENT during assignment
    """
    result = service.bulk_assign_leads(request.lead_ids, request.store_id)
    
    # Logging (CRITICAL: No SMS sent)
    logger.info("=" * 70)
    logger.info(f"✅ BULK LEAD ASSIGNMENT COMPLETED - NO SMS SENT")
    logger.info(f"  - Requested assignments: {len(request.lead_ids)}")
    logger.info(f"  - Successfully assigned: {result.get('assigned', 0)}")
    logger.info(f"  - Store ID: {request.store_id}")
    logger.info("=" * 70)
    
    return result


@router.get("/safe-call-eligible", summary="Get leads eligible for safe calling")
async def get_safe_call_eligible_leads(
    store_id: Optional[int] = Query(None, description="Filter by specific store"),
    limit: int = Query(100, description="Maximum number of leads to return"),
    service: LeadService = Depends(get_service)
):
    """
    Get leads that are eligible for safe calling (24 hours after SMS with no reply).
    
    Uses dynamic query instead of call_eligible flag columns.
    
    Response:
    [
        {
            "lead_id": 123,
            "name": "John Doe",
            "phone_number": "+15551234567",
            "store_id": 1,
            "call_eligible_reason": "safe_call_24h",
            "sms_consent_requested_at": "2025-11-13T10:00:00",
            "sms_verified": false,
            "hours_since_sms": 26
        },
        ...
    ]
    """
    leads = service.get_safe_call_eligible_leads(store_id=store_id, limit=limit)
    
    logger.info(f"✅ Found {len(leads)} safe-call eligible leads" + 
               (f" for store {store_id}" if store_id else ""))
    
    return leads


@router.post("/auto-assign", summary="Auto-assign unassigned leads to stores")
async def auto_assign_leads():
    """
    Automatically assign unassigned leads to stores based on City/State/County.
    
    Logic:
    - Matches leads to stores by City, State, or County
    - Distributes leads evenly across stores if multiple matches
    - Returns assignment summary
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get all unassigned leads
        cursor.execute("""
            SELECT lead_id, City, State, County
            FROM OutboundLeads
            WHERE store_id IS NULL
              AND (dnc_flag = 0 OR dnc_flag IS NULL)
        """)
        
        unassigned_leads = cursor.fetchall()
        
        # Get all stores with their locations
        cursor.execute("""
            SELECT store_id, name, location
            FROM stores
            WHERE is_active = 1
        """)
        
        stores = cursor.fetchall()
        store_map = {store[0]: {'name': store[1], 'location': store[2]} for store in stores}
        
        # Create mapping: City/State/County -> Store IDs
        location_to_stores = {}
        for store_id, store_data in store_map.items():
            location_lower = store_data['location'].lower()
            # Add location variations
            location_to_stores[location_lower] = location_to_stores.get(location_lower, []) + [store_id]
            
            # Also index each token in the store's address as an alias, so a
            # lead whose city/county matches any token of the store's location
            # can be routed. Operators with non-US locations should adapt the
            # split rules if their addresses use different conventions.
            for token in location_lower.replace(',', ' ').split():
                token = token.strip()
                if len(token) < 3 or token.isdigit():
                    continue
                location_to_stores.setdefault(token, []).append(store_id)
        
        assigned_count = 0
        skipped_count = 0
        assignment_log = []
        
        # Distribute leads evenly across stores
        store_lead_counts = {store_id: 0 for store_id in store_map.keys()}
        
        for lead_row in unassigned_leads:
            lead_id = lead_row[0]
            city = (lead_row[1] or '').lower().strip()
            state = (lead_row[2] or '').lower().strip()
            county = (lead_row[3] or '').lower().strip()
            
            # Find matching store
            matched_store_id = None
            
            # Try City first
            if city:
                for loc_key, store_ids in location_to_stores.items():
                    if city in loc_key or loc_key in city:
                        # Use store with fewest leads for even distribution
                        matched_store_id = min(store_ids, key=lambda sid: store_lead_counts[sid])
                        break
            
            # Try State
            if not matched_store_id and state:
                for loc_key, store_ids in location_to_stores.items():
                    if state in loc_key or loc_key in state:
                        matched_store_id = min(store_ids, key=lambda sid: store_lead_counts[sid])
                        break
            
            # Try County
            if not matched_store_id and county:
                for loc_key, store_ids in location_to_stores.items():
                    if county in loc_key or loc_key in county:
                        matched_store_id = min(store_ids, key=lambda sid: store_lead_counts[sid])
                        break
            
            if matched_store_id:
                cursor.execute("""
                    UPDATE OutboundLeads
                    SET store_id = ?
                    WHERE lead_id = ?
                """, (matched_store_id, lead_id))
                assigned_count += 1
                store_lead_counts[matched_store_id] += 1
                assignment_log.append({
                    'lead_id': lead_id,
                    'store_id': matched_store_id,
                    'store_name': store_map[matched_store_id]['name'],
                    'match_reason': f"Matched by {city or state or county}"
                })
            else:
                skipped_count += 1
                assignment_log.append({
                    'lead_id': lead_id,
                    'store_id': None,
                    'store_name': None,
                    'match_reason': 'No location match found'
                })
        
        conn.commit()
        
        return {
            "success": True,
            "assigned_count": assigned_count,
            "skipped_count": skipped_count,
            "total_processed": len(unassigned_leads),
            "message": f"Auto-assigned {assigned_count} leads to stores. {skipped_count} leads skipped (no location match).",
            "assignments": assignment_log[:50]  # Return first 50 for preview
        }
        
    except Exception as e:
        conn.rollback()
        raise DatabaseError(f"Error auto-assigning leads: {str(e)}")
    finally:
        cursor.close()
        conn.close()


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def _export_leads_to_csv(leads: list[dict]) -> str:
    """Convert leads to CSV format."""
    if not leads:
        return "FirstName,LastName,Address,City,countyname,State,Zip,Phone,Phone_DNC,CellPhone,Cellphone_DNC,MIXPHONE,MIXPHONE_TYPE,MIXPHONE_DNC,DNC\n"
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'FirstName', 'LastName', 'Address', 'City', 'countyname', 'State', 'Zip',
        'Phone', 'Phone_DNC', 'CellPhone', 'Cellphone_DNC', 'MIXPHONE', 'MIXPHONE_TYPE', 'MIXPHONE_DNC', 'DNC'
    ])
    
    # Write data rows
    for lead in leads:
        # Split name into first and last
        name_parts = lead.get('name', '').split(' ', 1)
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        writer.writerow([
            first_name,
            last_name,
            lead.get('Address', ''),
            lead.get('City', ''),
            lead.get('County', ''),
            lead.get('State', ''),
            lead.get('Zip', ''),
            lead.get('phone_number', ''),  # Phone
            'N',  # Phone_DNC
            '',   # CellPhone
            'N',  # Cellphone_DNC
            lead.get('phone_number', ''),  # MIXPHONE
            'W',  # MIXPHONE_TYPE (W = Wireless)
            'N',  # MIXPHONE_DNC
            'Y' if lead.get('dnc_flag') else 'N'  # DNC
        ])
    
    return output.getvalue()

