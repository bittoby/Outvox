"""
WebSocket Router
Handles WebSocket connections for real-time updates.
"""

import json
import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from services.websocket_service import get_websocket_manager, EventType

logger = logging.getLogger(__name__)

# Router instance
router = APIRouter(tags=["websocket"])

# Get WebSocket manager
manager = get_websocket_manager()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None, description="Optional client identifier")
):
    """
    WebSocket endpoint for real-time updates.
    
    Clients can subscribe to specific event types by sending messages:
    {
        "action": "subscribe",
        "event_types": ["AGENT_HEALTH_UPDATE", "CALL_STATS_UPDATE", ...]
    }
    
    To unsubscribe:
    {
        "action": "unsubscribe",
        "event_types": ["AGENT_HEALTH_UPDATE"]
    }
    
    Events are broadcast automatically when they occur.
    """
    connection_id = None
    
    try:
        # Accept connection
        connection_id = await manager.connect(websocket, client_id)
        
        # Send welcome message
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "data": {
                "connection_id": connection_id,
                "message": "WebSocket connection established",
                "available_events": [e.value for e in EventType]
            }
        })
        
        # Handle incoming messages with timeout
        while True:
            try:
                # Receive message from client with timeout (30 seconds)
                # This prevents connections from hanging indefinitely
                import asyncio
                try:
                    message = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=30.0
                    )
                except asyncio.TimeoutError:
                    # Send ping to check if connection is alive
                    try:
                        await websocket.send_json({
                            "type": "PING",
                            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
                            "data": {"message": "ping"}
                        })
                        # Continue waiting for next message
                        continue
                    except Exception:
                        # Connection is dead, break to cleanup
                        break
                
                try:
                    data = json.loads(message)
                    action = data.get("action")
                    event_types = data.get("event_types", [])
                    
                    if action == "subscribe":
                        # Subscribe to event types
                        for event_type_str in event_types:
                            try:
                                event_type = EventType(event_type_str)
                                await manager.subscribe(connection_id, event_type)
                            except ValueError:
                                logger.warning(f"Invalid event type: {event_type_str}")
                        
                        await websocket.send_json({
                            "type": "SUBSCRIBED",
                            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
                            "data": {
                                "event_types": event_types,
                                "message": f"Subscribed to {len(event_types)} event type(s)"
                            }
                        })
                    
                    elif action == "unsubscribe":
                        # Unsubscribe from event types
                        for event_type_str in event_types:
                            try:
                                event_type = EventType(event_type_str)
                                await manager.unsubscribe(connection_id, event_type)
                            except ValueError:
                                logger.warning(f"Invalid event type: {event_type_str}")
                        
                        await websocket.send_json({
                            "type": "UNSUBSCRIBED",
                            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
                            "data": {
                                "event_types": event_types,
                                "message": f"Unsubscribed from {len(event_types)} event type(s)"
                            }
                        })
                    
                    elif action == "ping":
                        # Heartbeat/ping
                        await websocket.send_json({
                            "type": "PONG",
                            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
                            "data": {"message": "pong"}
                        })
                    
                    else:
                        await websocket.send_json({
                            "type": "ERROR",
                            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
                            "data": {
                                "message": f"Unknown action: {action}",
                                "valid_actions": ["subscribe", "unsubscribe", "ping"]
                            }
                        })
                
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "ERROR",
                        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
                        "data": {"message": "Invalid JSON format"}
                    })
            
            except WebSocketDisconnect:
                break
            
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                try:
                    # Check if connection is still valid before sending error
                    if hasattr(websocket, 'client_state'):
                        from fastapi.websockets import WebSocketState
                        if websocket.client_state == WebSocketState.CONNECTED:
                            await websocket.send_json({
                                "type": "ERROR",
                                "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
                                "data": {"message": f"Error processing message: {str(e)}"}
                            })
                except Exception as send_error:
                    logger.error(f"Failed to send error message: {send_error}")
                    # Connection is likely closed, break to cleanup
                    break
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    
    finally:
        if connection_id:
            await manager.disconnect(connection_id)

