"""
SMS and Photo Management Router (Refactored)
Handles SMS conversations and photo submissions using service layer.
"""

import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import Response

from models import SMSMessageCreate, PhotoSubmissionCreate, PhotoStatusUpdate
from services.sms_service import get_sms_service, SMSService
from core.exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)

# Router instance
router = APIRouter(prefix="/api/sms", tags=["sms"])


# Dependency injection
def get_service() -> SMSService:
    """Dependency injection for SMSService."""
    return get_sms_service()


# ============================================================================
# GET ENDPOINTS
# ============================================================================

@router.get("/conversations/{lead_id}", summary="Get SMS conversation details by lead ID")
async def get_sms_conversation(
    lead_id: int,
    service: SMSService = Depends(get_service)
):
    """Get SMS conversation details including lead info and all messages."""
    # Let exceptions bubble up to global handler
    return service.get_conversation(lead_id)


@router.get("/conversations/phone/{phone_number:path}", summary="Get SMS conversation details by phone number")
async def get_sms_conversation_by_phone(
    phone_number: str,
    service: SMSService = Depends(get_service)
):
    """
    Get SMS conversation details by phone number (for conversations without lead_id).
    
    This endpoint is used when a customer sends SMS first before a lead is created.
    """
    # Let exceptions bubble up to global handler
    return service.get_conversation_by_phone(phone_number)


@router.get("/all-conversations", summary="Get all SMS conversations")
async def get_all_sms_conversations(
    limit: int = 100,
    offset: int = 0,
    direction: Optional[str] = None,
    store_id: Optional[int] = None,
    service: SMSService = Depends(get_service)
):
    """Get all SMS conversations from SMSConversations table with lead info."""
    # Let exceptions bubble up to global handler
    return service.get_all_conversations(
        limit=limit,
        offset=offset,
        direction=direction,
        store_id=store_id
    )


# ============================================================================
# Photo Submissions
# ============================================================================

@router.get("/photos/all-submissions", summary="Get all photo submissions")
async def get_all_photo_submissions(
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    service: SMSService = Depends(get_service)
):
    """Get all photo submissions with optional status filter."""
    # Let exceptions bubble up to global handler
    return service.get_all_photo_submissions(
        limit=limit,
        offset=offset,
        status=status
    )


# ============================================================================
# DELETE ENDPOINTS
# ============================================================================

# IMPORTANT: More specific routes must come BEFORE parameterized routes
# Otherwise FastAPI will match /conversations/clear-all to /conversations/{lead_id}

@router.delete("/conversations/clear-all", summary="Delete all SMS conversations")
async def clear_all_conversations(service: SMSService = Depends(get_service)):
    """Delete all SMS conversations (does NOT touch photos)."""
    # Let exceptions bubble up to global handler
    return service.clear_all_conversations()


@router.delete("/photos/clear-all", summary="Delete all photo submissions")
async def clear_all_photos(service: SMSService = Depends(get_service)):
    """Delete all photo submissions (does NOT touch conversations)."""
    # Let exceptions bubble up to global handler
    return service.clear_all_photos()


@router.delete("/conversations/{lead_id}", summary="Delete SMS conversation")
async def delete_sms_conversation(
    lead_id: int,
    service: SMSService = Depends(get_service)
):
    """Delete all SMS conversations for a specific lead."""
    # Let exceptions bubble up to global handler
    return service.delete_conversation(lead_id)


@router.delete("/photos/{photo_id}", summary="Delete photo submission")
async def delete_photo_submission(
    photo_id: int,
    service: SMSService = Depends(get_service)
):
    """Delete a photo submission."""
    # Let exceptions bubble up to global handler
    return service.delete_photo_submission(photo_id)


# ============================================================================
# SMS SEND/RECEIVE ENDPOINTS
# ============================================================================

@router.post("/send", summary="Log outbound SMS message")
async def send_sms(
    sms: SMSMessageCreate,
    service: SMSService = Depends(get_service)
):
    """Log an outbound SMS message to the database."""
    # Let exceptions bubble up to global handler
    return service.send_sms(sms.dict())


@router.post("/receive", summary="Log inbound SMS message")
async def receive_sms(
    sms: SMSMessageCreate,
    service: SMSService = Depends(get_service)
):
    """Log an inbound SMS message to the database."""
    # Let exceptions bubble up to global handler
    return service.receive_sms(sms.dict())


# ============================================================================
# PHOTO SUBMISSION ENDPOINTS
# ============================================================================

@router.post("/photos/submit", summary="Submit photo for appraisal")
async def submit_photo(
    photo: PhotoSubmissionCreate,
    service: SMSService = Depends(get_service)
):
    """Submit a photo for appraisal."""
    # Let exceptions bubble up to global handler
    return service.submit_photo(photo.dict())


@router.get("/photos/pending", summary="Get pending photo submissions")
async def get_pending_photos(
    service: SMSService = Depends(get_service)
):
    """Get all pending photo submissions."""
    # Let exceptions bubble up to global handler
    return service.get_pending_photos()


@router.put("/photos/{photo_id}/status", summary="Update photo status")
async def update_photo_status(
    photo_id: int,
    status_update: PhotoStatusUpdate,
    service: SMSService = Depends(get_service)
):
    """Update photo submission status."""
    # Let exceptions bubble up to global handler
    return service.update_photo_status(
        photo_id,
        status_update.status,
        status_update.reviewed_by
    )


# ============================================================================
# WEBHOOK ENDPOINTS (Twilio Integration)
# ============================================================================

@router.api_route("/twilio-sms", methods=["GET", "POST"], summary="Handle incoming SMS webhooks from Twilio (legacy endpoint)")
async def handle_twilio_sms_webhook(request: Request):
    """
    Handle incoming SMS webhooks from Twilio (legacy endpoint name).
    
    This endpoint accepts webhooks sent to /twilio-sms and processes them
    using ConsentTracker. This maintains compatibility with existing Twilio
    webhook configurations that use /twilio-sms.
    
    Classification:
    - YES replies → Mark lead as consented (sms_verified=true)
    - STOP replies → Mark lead as DNC (dnc_flag=true)
    - OTHER replies → Log for manual review
    
    Idempotency: Uses Twilio's MessageSid to prevent duplicate processing.
    
    Twilio Webhook Configuration:
    - Set webhook URL to: http://your-domain:8000/sms/twilio-sms
    - Method: POST (or GET for compatibility)
    
    Request Body (from Twilio):
        From=+15551234567&To=+15559876543&Body=YES&MessageSid=SM1234...
    """
    try:
        # Twilio sends form data, not JSON
        form_data = await request.form()
        
        # Extract Twilio webhook parameters
        from_number = form_data.get('From', '')
        to_number = form_data.get('To', '')
        body = form_data.get('Body', '')
        message_sid = form_data.get('MessageSid', '')
        received_at_str = form_data.get('DateCreated')
        
        # Check for MMS (photos) - Twilio sends NumMedia field for MMS
        num_media = form_data.get('NumMedia', '0')
        has_media = int(num_media) > 0 if num_media.isdigit() else False
        
        logger.info(f"[Twilio SMS Webhook] Processing message from {from_number}: {body[:50] if body else 'MMS'}, Media: {num_media}")
        
        # Validate required fields (MessageSid is always required, but Body may be empty for MMS-only)
        if not from_number or not message_sid:
            logger.error(f"[Twilio SMS Webhook] Missing required fields: From={from_number}, MessageSid={message_sid}")
            raise HTTPException(
                status_code=400, 
                detail="Missing required fields: From or MessageSid"
            )
        
        # Process MMS (photos) if present
        if has_media:
            logger.info(f"[Twilio SMS Webhook] Processing MMS with {num_media} media file(s)")
            try:
                from services.sms_service import get_sms_service
                from repositories.lead_repository import LeadRepository
                from utils.phone_validator import normalize_phone_number
                
                sms_service = get_sms_service()
                lead_repo = LeadRepository()
                
                # Normalize phone number for matching (same as ConsentTracker)
                normalized_phone = normalize_phone_number(from_number)
                
                if not normalized_phone:
                    logger.warning(f"[Twilio SMS Webhook] Invalid phone number format: {from_number}, skipping photo submission")
                else:
                    # Find lead by phone number (using normalized format)
                    lead = lead_repo.get_by_phone(normalized_phone)
                    if not lead:
                        logger.warning(f"[Twilio SMS Webhook] No lead found for phone number {normalized_phone} (original: {from_number}), skipping photo submission")
                    else:
                        lead_id = lead['lead_id']
                        logger.info(f"[Twilio SMS Webhook] Found lead {lead_id} for phone {normalized_phone}")
                        
                        # Process each media file
                        for i in range(int(num_media)):
                            media_url = form_data.get(f'MediaUrl{i}', '')
                            media_content_type = form_data.get(f'MediaContentType{i}', 'image/jpeg')
                            
                            if media_url and media_content_type.startswith('image/'):
                                logger.info(f"[Twilio SMS Webhook] Processing photo {i+1}/{num_media}: {media_url}")
                                
                                # Submit photo to database
                                photo_data = {
                                    'lead_id': lead_id,
                                    'phone_number': normalized_phone,  # Use normalized phone
                                    'photo_url': media_url,
                                    'status': 'pending'
                                }
                                photo_result = sms_service.submit_photo(photo_data)
                                logger.info(f"[Twilio SMS Webhook] ✅ Photo submitted: photo_id={photo_result.get('photo_id')}, lead_id={lead_id}")
                            else:
                                logger.warning(f"[Twilio SMS Webhook] Skipping non-image media {i+1}: {media_content_type}")
            except Exception as photo_error:
                logger.error(f"[Twilio SMS Webhook] Error processing MMS: {photo_error}")
                import traceback
                traceback.print_exc()
        
        # Process text message (if body exists) using ConsentTracker
        if body:
        
            # Parse received_at timestamp if provided
            received_at = None
            if received_at_str:
                try:
                    from dateutil import parser
                    received_at = parser.parse(received_at_str)
                except:
                    received_at = datetime.now()
            else:
                received_at = datetime.now()
            
            # Process reply using ConsentTracker
            from services.consent_tracker import ConsentTracker
            tracker = ConsentTracker()
            result = tracker.process_reply(
                from_number=from_number,
                body=body,
                twilio_message_sid=message_sid,
                from_phone_number=to_number,
                received_at=received_at
            )
            
            # Log the result
            if result['duplicate']:
                logger.warning(f"[Twilio SMS Webhook] Duplicate webhook detected: {message_sid}")
            elif result['error']:
                logger.error(f"[Twilio SMS Webhook] Error: {result['error']}")
            else:
                logger.info(f"[Twilio SMS Webhook] Reply processed: {result['classification']}, Lead ID: {result['lead_id']}, Updated: {result['lead_updated']}")
        elif has_media:
            # MMS-only message (no text body) - already processed above
            logger.info(f"[Twilio SMS Webhook] MMS-only message processed (no text body)")
        
        # Return TwiML XML response to Twilio (required format to prevent 12300 errors)
        return Response(
            content="<Response></Response>",
            media_type="text/xml"
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"[Twilio SMS Webhook] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        # Still return TwiML XML to Twilio to avoid retries and 12300 errors
        return Response(
            content="<Response></Response>",
            media_type="text/xml"
        )


@router.post("/inbound", summary="Handle incoming SMS consent replies from Twilio")
async def handle_sms_inbound(request: Request):
    """
    Handle incoming SMS consent replies from Twilio webhook.
    
    This endpoint processes SMS replies from leads to determine consent status.
    Twilio sends a POST request to this endpoint when a lead replies to our SMS.
    
    Classification:
    - YES replies → Mark lead as consented (sms_verified=true)
    - STOP replies → Mark lead as DNC (dnc_flag=true)
    - OTHER replies → Log for manual review
    
    Idempotency: Uses Twilio's MessageSid to prevent duplicate processing.
    
    Twilio Webhook Configuration:
    - Set webhook URL to: http://your-domain:8000/sms/inbound
    - Method: POST
    
    Request Body (from Twilio):
        From=+15551234567&To=+15559876543&Body=YES&MessageSid=SM1234...
    """
    try:
        # Twilio sends form data, not JSON
        form_data = await request.form()
        
        # Extract Twilio webhook parameters
        from_number = form_data.get('From', '')
        to_number = form_data.get('To', '')
        body = form_data.get('Body', '')
        message_sid = form_data.get('MessageSid', '')
        received_at_str = form_data.get('DateCreated')  # Twilio timestamp
        
        # Check for MMS (photos) - Twilio sends NumMedia field for MMS
        num_media = form_data.get('NumMedia', '0')
        has_media = int(num_media) > 0 if num_media.isdigit() else False
        
        logger.info(f"[SMS Inbound] Processing message from {from_number}: {body[:50] if body else 'MMS'}, Media: {num_media}")
        
        # Validate required fields (MessageSid is always required, but Body may be empty for MMS-only)
        if not from_number or not message_sid:
            logger.error(f"[SMS Inbound] Missing required fields: From={from_number}, MessageSid={message_sid}")
            raise HTTPException(
                status_code=400, 
                detail="Missing required fields: From or MessageSid"
            )
        
        # Process MMS (photos) if present
        if has_media:
            logger.info(f"[SMS Inbound] Processing MMS with {num_media} media file(s)")
            try:
                from services.sms_service import get_sms_service
                from repositories.lead_repository import LeadRepository
                from utils.phone_validator import normalize_phone_number
                
                sms_service = get_sms_service()
                lead_repo = LeadRepository()
                
                # Normalize phone number for matching (same as ConsentTracker)
                normalized_phone = normalize_phone_number(from_number)
                
                if not normalized_phone:
                    logger.warning(f"[SMS Inbound] Invalid phone number format: {from_number}, skipping photo submission")
                else:
                    # Find lead by phone number (using normalized format)
                    lead = lead_repo.get_by_phone(normalized_phone)
                    if not lead:
                        logger.warning(f"[SMS Inbound] No lead found for phone number {normalized_phone} (original: {from_number}), skipping photo submission")
                    else:
                        lead_id = lead['lead_id']
                        logger.info(f"[SMS Inbound] Found lead {lead_id} for phone {normalized_phone}")
                        
                        # Process each media file
                        for i in range(int(num_media)):
                            media_url = form_data.get(f'MediaUrl{i}', '')
                            media_content_type = form_data.get(f'MediaContentType{i}', 'image/jpeg')
                            
                            if media_url and media_content_type.startswith('image/'):
                                logger.info(f"[SMS Inbound] Processing photo {i+1}/{num_media}: {media_url}")
                                
                                # Submit photo to database
                                photo_data = {
                                    'lead_id': lead_id,
                                    'phone_number': normalized_phone,  # Use normalized phone
                                    'photo_url': media_url,
                                    'status': 'pending'
                                }
                                photo_result = sms_service.submit_photo(photo_data)
                                logger.info(f"[SMS Inbound] ✅ Photo submitted: photo_id={photo_result.get('photo_id')}, lead_id={lead_id}")
                            else:
                                logger.warning(f"[SMS Inbound] Skipping non-image media {i+1}: {media_content_type}")
            except Exception as photo_error:
                logger.error(f"[SMS Inbound] Error processing MMS: {photo_error}")
                import traceback
                traceback.print_exc()
        
        # Process text message (if body exists) using ConsentTracker
        if body:
        
            # Parse received_at timestamp if provided
            received_at = None
            if received_at_str:
                try:
                    from dateutil import parser
                    received_at = parser.parse(received_at_str)
                except:
                    received_at = datetime.now()
            else:
                received_at = datetime.now()
            
            # Process reply using ConsentTracker
            from services.consent_tracker import ConsentTracker
            tracker = ConsentTracker()
            result = tracker.process_reply(
                from_number=from_number,
                body=body,
                twilio_message_sid=message_sid,
                from_phone_number=to_number,
                received_at=received_at
            )
            
            # Build response
            response = {
                'success': True,
                'classification': result['classification'],
                'lead_id': result['lead_id'],
                'lead_updated': result['lead_updated'],
                'auto_reply_sent': result['auto_reply_sent'],
                'duplicate': result['duplicate']
            }
            
            if result['duplicate']:
                response['message'] = "Duplicate webhook - already processed"
                logger.warning(f"[SMS Inbound] Duplicate webhook detected: {message_sid}")
            elif result['error']:
                response['success'] = False
                response['message'] = result['error']
                logger.error(f"[SMS Inbound] Error: {result['error']}")
            else:
                response['message'] = f"Reply classified as {result['classification']} and processed successfully"
                logger.info(f"[SMS Inbound] Reply processed: {result['classification']}, Lead ID: {result['lead_id']}, Updated: {result['lead_updated']}")
            
            return response
        elif has_media:
            # MMS-only message (no text body) - already processed above
            return {
                'success': True,
                'message': f'MMS with {num_media} photo(s) processed successfully',
                'photos_received': int(num_media)
            }
        else:
            # No body and no media - invalid message
            logger.warning(f"[SMS Inbound] Message with no body and no media: {message_sid}")
            raise HTTPException(
                status_code=400,
                detail="Message must have either Body or Media content"
            )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(f"[SMS Inbound] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process SMS reply: {str(e)}"
        )
