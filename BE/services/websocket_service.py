"""
WebSocket Service
Manages WebSocket connections and event broadcasting for real-time updates.
"""

import json
import asyncio
import logging
from typing import Dict, Set, Optional, Any, List
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from enum import Enum

logger = logging.getLogger(__name__)

# Fix for asyncio.get_event_loop() deprecation
def get_or_create_event_loop():
    """Get or create event loop, handling both sync and async contexts."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


class EventType(str, Enum):
    """WebSocket event types."""
    AGENT_HEALTH_UPDATE = "AGENT_HEALTH_UPDATE"
    CALL_STATS_UPDATE = "CALL_STATS_UPDATE"
    CAMPAIGN_PROGRESS = "CAMPAIGN_PROGRESS"
    CAMPAIGN_CREATED = "CAMPAIGN_CREATED"
    CAMPAIGN_UPDATED = "CAMPAIGN_UPDATED"
    POPUP_ADDED = "POPUP_ADDED"
    POPUP_UPDATED = "POPUP_UPDATED"
    POPUP_DISMISSED = "POPUP_DISMISSED"
    SMS_RECEIVED = "SMS_RECEIVED"
    SMS_SENT = "SMS_SENT"
    PHOTO_SUBMITTED = "PHOTO_SUBMITTED"
    PHOTO_UPDATED = "PHOTO_UPDATED"
    LEAD_UPDATED = "LEAD_UPDATED"
    LEAD_CREATED = "LEAD_CREATED"
    STORE_STATS_UPDATE = "STORE_STATS_UPDATE"
    PHONE_NUMBER_UPDATE = "PHONE_NUMBER_UPDATE"


class WebSocketManager:
    """
    Manages WebSocket connections and event broadcasting.
    
    This is a singleton pattern to ensure all services use the same connection manager.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'WebSocketManager':
        """Get singleton instance of WebSocketManager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize the WebSocket manager."""
        # Active connections: {websocket_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Subscriptions: {event_type: Set[websocket_id]}
        self.subscriptions: Dict[EventType, Set[str]] = {}
        
        # Connection metadata: {websocket_id: {client_id, connected_at, subscriptions}}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, client_id: Optional[str] = None) -> str:
        """
        Accept a new WebSocket connection.
        
        Args:
            websocket: FastAPI WebSocket connection
            client_id: Optional client identifier
            
        Returns:
            str: Connection ID
        """
        await websocket.accept()
        
        # Generate connection ID
        connection_id = client_id or f"client_{len(self.active_connections)}_{datetime.now().timestamp()}"
        
        async with self._lock:
            self.active_connections[connection_id] = websocket
            self.connection_metadata[connection_id] = {
                "client_id": client_id,
                "connected_at": datetime.utcnow().isoformat(),
                "subscriptions": set()
            }
        
        logger.info(f"WebSocket connected: {connection_id} (total: {len(self.active_connections)})")
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """
        Disconnect a WebSocket connection.
        
        Args:
            connection_id: Connection ID to disconnect
        """
        async with self._lock:
            if connection_id in self.active_connections:
                # Remove from all subscriptions
                metadata = self.connection_metadata.get(connection_id, {})
                subscriptions = metadata.get("subscriptions", set())
                
                for event_type in subscriptions:
                    if event_type in self.subscriptions:
                        self.subscriptions[event_type].discard(connection_id)
                
                # Remove connection
                del self.active_connections[connection_id]
                if connection_id in self.connection_metadata:
                    del self.connection_metadata[connection_id]
                
                logger.info(f"WebSocket disconnected: {connection_id} (total: {len(self.active_connections)})")
    
    async def subscribe(self, connection_id: str, event_type: EventType) -> bool:
        """
        Subscribe a connection to an event type.
        
        Args:
            connection_id: Connection ID
            event_type: Event type to subscribe to
            
        Returns:
            bool: Success status
        """
        if connection_id not in self.active_connections:
            logger.warning(f"Subscription failed: Connection {connection_id} not found")
            return False
        
        async with self._lock:
            if event_type not in self.subscriptions:
                self.subscriptions[event_type] = set()
            
            self.subscriptions[event_type].add(connection_id)
            
            # Update metadata
            if connection_id in self.connection_metadata:
                self.connection_metadata[connection_id]["subscriptions"].add(event_type)
        
        logger.debug(f"Connection {connection_id} subscribed to {event_type.value}")
        return True
    
    async def unsubscribe(self, connection_id: str, event_type: EventType) -> bool:
        """
        Unsubscribe a connection from an event type.
        
        Args:
            connection_id: Connection ID
            event_type: Event type to unsubscribe from
            
        Returns:
            bool: Success status
        """
        async with self._lock:
            if event_type in self.subscriptions:
                self.subscriptions[event_type].discard(connection_id)
            
            # Update metadata
            if connection_id in self.connection_metadata:
                self.connection_metadata[connection_id]["subscriptions"].discard(event_type)
        
        logger.debug(f"Connection {connection_id} unsubscribed from {event_type.value}")
        return True
    
    async def broadcast(self, event_type: EventType, data: Any, exclude: Optional[Set[str]] = None):
        """
        Broadcast an event to all subscribed connections.
        
        Args:
            event_type: Type of event to broadcast
            data: Event data (will be JSON serialized)
            exclude: Optional set of connection IDs to exclude
        """
        exclude = exclude or set()
        
        # Get subscribers for this event type
        subscribers = self.subscriptions.get(event_type, set()) - exclude
        
        if not subscribers:
            logger.debug(f"No subscribers for event type {event_type.value}")
            return
        
        # Create event message
        event_message = {
            "type": event_type.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": data
        }
        
        # Broadcast to all subscribers
        disconnected = []
        for connection_id in list(subscribers):
            if connection_id in self.active_connections:
                try:
                    websocket = self.active_connections[connection_id]
                    
                    # Check connection state before sending
                    # FastAPI WebSocket state: CONNECTED, DISCONNECTED, CONNECTING
                    if hasattr(websocket, 'client_state'):
                        from fastapi.websockets import WebSocketState
                        if websocket.client_state != WebSocketState.CONNECTED:
                            logger.debug(f"Connection {connection_id} not in CONNECTED state: {websocket.client_state}")
                            disconnected.append(connection_id)
                            continue
                    
                    await websocket.send_json(event_message)
                except (WebSocketDisconnect, ConnectionError, RuntimeError) as e:
                    # Connection is closed or invalid
                    logger.debug(f"Connection {connection_id} closed/disconnected: {e}")
                    disconnected.append(connection_id)
                except Exception as e:
                    # Other errors (serialization, etc.)
                    logger.error(f"Error sending event to {connection_id}: {e}")
                    disconnected.append(connection_id)
            else:
                disconnected.append(connection_id)
        
        # Clean up disconnected connections (non-blocking)
        if disconnected:
            for conn_id in disconnected:
                try:
                    await self.disconnect(conn_id)
                except Exception as e:
                    logger.error(f"Error disconnecting {conn_id}: {e}")
        
        if len(subscribers) > 0:
            logger.info(f"✅ Broadcasted {event_type.value} to {len(subscribers)} connection(s)")
        else:
            logger.debug(f"No subscribers for {event_type.value}")
    
    async def send_to_connection(self, connection_id: str, event_type: EventType, data: Any) -> bool:
        """
        Send an event to a specific connection.
        
        Args:
            connection_id: Connection ID
            event_type: Type of event
            data: Event data
            
        Returns:
            bool: Success status
        """
        if connection_id not in self.active_connections:
            return False
        
        try:
            websocket = self.active_connections[connection_id]
            
            # Check connection state before sending
            if hasattr(websocket, 'client_state'):
                from fastapi.websockets import WebSocketState
                if websocket.client_state != WebSocketState.CONNECTED:
                    logger.debug(f"Connection {connection_id} not in CONNECTED state: {websocket.client_state}")
                    await self.disconnect(connection_id)
                    return False
            
            event_message = {
                "type": event_type.value,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data": data
            }
            
            await websocket.send_json(event_message)
            return True
        except (WebSocketDisconnect, ConnectionError, RuntimeError) as e:
            # Connection is closed
            logger.debug(f"Connection {connection_id} closed: {e}")
            await self.disconnect(connection_id)
            return False
        except Exception as e:
            logger.error(f"Error sending to {connection_id}: {e}")
            await self.disconnect(connection_id)
            return False
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)
    
    def get_subscription_count(self, event_type: EventType) -> int:
        """Get the number of subscribers for an event type."""
        return len(self.subscriptions.get(event_type, set()))


# Store reference to the FastAPI app's event loop for sync broadcasts
_app_event_loop: Optional[asyncio.AbstractEventLoop] = None


def set_app_event_loop(loop: asyncio.AbstractEventLoop):
    """Set the FastAPI app's event loop for use in sync broadcasts."""
    global _app_event_loop
    _app_event_loop = loop
    logger.info("WebSocket service: App event loop registered")


def get_websocket_manager() -> WebSocketManager:
    """Get singleton instance of WebSocketManager."""
    return WebSocketManager.get_instance()


async def broadcast_event(event_type: EventType, data: Any, exclude: Optional[Set[str]] = None):
    """
    Convenience function to broadcast an event.
    
    Args:
        event_type: Type of event to broadcast
        data: Event data
        exclude: Optional set of connection IDs to exclude
    """
    manager = get_websocket_manager()
    await manager.broadcast(event_type, data, exclude)


def broadcast_event_sync(event_type: EventType, data: Any, exclude: Optional[Set[str]] = None):
    """
    Synchronous wrapper for broadcasting events.
    Safely creates background task regardless of calling context.
    
    Args:
        event_type: Type of event to broadcast
        data: Event data
        exclude: Optional set of connection IDs to exclude
    """
    try:
        # Try to get current event loop (if we're in an async context)
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context with running loop
            # Create task (fire and forget)
            loop.create_task(broadcast_event(event_type, data, exclude))
            logger.debug(f"Broadcasting {event_type.value} via running event loop")
        except RuntimeError:
            # No running event loop - we're in sync context
            # Try to use the FastAPI app's event loop if available
            global _app_event_loop
            if _app_event_loop is not None and not _app_event_loop.is_closed():
                # Schedule broadcast on the app's event loop (thread-safe)
                _app_event_loop.call_soon_threadsafe(
                    lambda: _app_event_loop.create_task(broadcast_event(event_type, data, exclude))
                )
                logger.debug(f"Broadcasting {event_type.value} via app event loop (thread-safe)")
            else:
                # Fallback: Use asyncio.run() in a thread (creates new loop - may not work for WebSockets)
                logger.warning(f"No app event loop available for {event_type.value}, using fallback thread")
                import threading
                def run_broadcast():
                    try:
                        # Try to use the app's event loop if we can access it
                        if _app_event_loop is not None and not _app_event_loop.is_closed():
                            future = asyncio.run_coroutine_threadsafe(
                                broadcast_event(event_type, data, exclude),
                                _app_event_loop
                            )
                            future.result(timeout=5)  # Wait up to 5 seconds
                        else:
                            # Last resort: create new loop (won't have WebSocket connections)
                            asyncio.run(broadcast_event(event_type, data, exclude))
                    except Exception as e:
                        logger.error(f"Error in broadcast thread: {e}")
                        import traceback
                        logger.debug(f"Broadcast thread error: {traceback.format_exc()}")
                
                # Start thread (fire and forget)
                thread = threading.Thread(target=run_broadcast, daemon=True)
                thread.start()
    except Exception as e:
        logger.warning(f"Failed to broadcast event {event_type.value}: {e}")
        import traceback
        logger.debug(f"Broadcast error traceback: {traceback.format_exc()}")

