/**
 * WebSocket Client
 * Manages WebSocket connection and message handling.
 */

import { WebSocketEvent, WebSocketMessage, EventHandler } from './types';
import { API_CONFIG } from '../config';

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 1000; // Start with 1 second
  private maxReconnectDelay = 30000; // Max 30 seconds
  private reconnectTimer: NodeJS.Timeout | null = null;
  private pingInterval: NodeJS.Timeout | null = null;
  private eventHandlers: Map<string, Set<EventHandler>> = new Map();
  private subscriptions: Set<string> = new Set();
  private messageQueue: WebSocketEvent[] = [];
  private connectionStateListeners: Set<(connected: boolean) => void> = new Set();
  private clientId: string | null = null;

  constructor(url?: string) {
    // Convert http:// to ws:// or https:// to wss://
    const baseUrl = url || API_CONFIG.DB_SERVICE;
    this.url = baseUrl.replace(/^http/, 'ws') + '/ws';
  }

  connect(clientId?: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('[WebSocket] Already connected');
      return;
    }

    if (this.ws?.readyState === WebSocket.CONNECTING) {
      console.log('[WebSocket] Connection in progress');
      return;
    }

    this.clientId = clientId || null;
    console.log(`[WebSocket] Connecting to ${this.url}...`);

    try {
      const wsUrl = this.clientId ? `${this.url}?client_id=${this.clientId}` : this.url;
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected');
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        this.notifyConnectionState(true);
        
        // Resubscribe to all previous subscriptions
        if (this.subscriptions.size > 0) {
          this.subscribe(Array.from(this.subscriptions));
        }
        
        // Send queued messages
        this.flushMessageQueue();
        
        // Start ping interval (every 30 seconds)
        this.startPingInterval();
      };

      this.ws.onmessage = (event) => {
        try {
          const data: WebSocketEvent = JSON.parse(event.data);
          this.handleMessage(data);
        } catch (error) {
          console.error('[WebSocket] Error parsing message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        this.notifyConnectionState(false);
      };

      this.ws.onclose = () => {
        console.log('[WebSocket] Disconnected');
        this.notifyConnectionState(false);
        this.stopPingInterval();
        this.attemptReconnect();
      };
    } catch (error) {
      console.error('[WebSocket] Connection error:', error);
      this.attemptReconnect();
    }
  }

  disconnect(): void {
    this.stopPingInterval();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.subscriptions.clear();
  }

  subscribe(eventTypes: string[]): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      // Queue subscription for when connected
      eventTypes.forEach(type => this.subscriptions.add(type));
      return;
    }

    const message: WebSocketMessage = {
      action: 'subscribe',
      event_types: eventTypes,
    };

    try {
      this.ws.send(JSON.stringify(message));
      eventTypes.forEach(type => this.subscriptions.add(type));
      console.log(`[WebSocket] Subscribed to: ${eventTypes.join(', ')}`);
    } catch (error) {
      console.error('[WebSocket] Error subscribing:', error);
    }
  }

  unsubscribe(eventTypes: string[]): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      eventTypes.forEach(type => this.subscriptions.delete(type));
      return;
    }

    const message: WebSocketMessage = {
      action: 'unsubscribe',
      event_types: eventTypes,
    };

    try {
      this.ws.send(JSON.stringify(message));
      eventTypes.forEach(type => this.subscriptions.delete(type));
      console.log(`[WebSocket] Unsubscribed from: ${eventTypes.join(', ')}`);
    } catch (error) {
      console.error('[WebSocket] Error unsubscribing:', error);
    }
  }

  on(eventType: string, handler: EventHandler): () => void {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, new Set());
    }
    this.eventHandlers.get(eventType)!.add(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.eventHandlers.get(eventType);
      if (handlers) {
        handlers.delete(handler);
        if (handlers.size === 0) {
          this.eventHandlers.delete(eventType);
        }
      }
    };
  }

  onConnectionStateChange(listener: (connected: boolean) => void): () => void {
    this.connectionStateListeners.add(listener);
    return () => {
      this.connectionStateListeners.delete(listener);
    };
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  private handleMessage(event: WebSocketEvent): void {
    // Handle system messages
    if (event.type === 'CONNECTION_ESTABLISHED') {
      console.log('[WebSocket] Connection established:', event.data);
      if (event.data.connection_id) {
        this.clientId = event.data.connection_id;
      }
      return;
    }

    if (event.type === 'SUBSCRIBED' || event.type === 'UNSUBSCRIBED' || event.type === 'PONG') {
      // System messages, no need to handle
      return;
    }

    if (event.type === 'ERROR') {
      console.error('[WebSocket] Server error:', event.data);
      return;
    }

    // Handle event broadcasts
    const handlers = this.eventHandlers.get(event.type);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(event);
        } catch (error) {
          console.error(`[WebSocket] Error in handler for ${event.type}:`, error);
        }
      });
    }

    // Also call handlers for 'all' if registered
    const allHandlers = this.eventHandlers.get('*');
    if (allHandlers) {
      allHandlers.forEach(handler => {
        try {
          handler(event);
        } catch (error) {
          console.error('[WebSocket] Error in "all" handler:', error);
        }
      });
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WebSocket] Max reconnect attempts reached');
      return;
    }

    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++;
      this.reconnectDelay = Math.min(
        this.reconnectDelay * 2,
        this.maxReconnectDelay
      );
      console.log(`[WebSocket] Reconnecting (attempt ${this.reconnectAttempts})...`);
      this.connect(this.clientId || undefined);
    }, this.reconnectDelay);
  }

  private startPingInterval(): void {
    this.stopPingInterval();
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        try {
          this.ws.send(JSON.stringify({ action: 'ping' }));
        } catch (error) {
          console.error('[WebSocket] Error sending ping:', error);
        }
      }
    }, 30000); // Every 30 seconds
  }

  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0) {
      const event = this.messageQueue.shift();
      if (event) {
        this.handleMessage(event);
      }
    }
  }

  private notifyConnectionState(connected: boolean): void {
    this.connectionStateListeners.forEach(listener => {
      try {
        listener(connected);
      } catch (error) {
        console.error('[WebSocket] Error in connection state listener:', error);
      }
    });
  }
}

