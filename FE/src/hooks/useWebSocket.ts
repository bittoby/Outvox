/**
 * useWebSocket Hook
 * React hook for WebSocket connection management.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { WebSocketClient } from '../services/websocket/client';
import { EventType, EventHandler } from '../services/websocket/types';

let globalClient: WebSocketClient | null = null;

function getWebSocketClient(): WebSocketClient {
  if (!globalClient) {
    globalClient = new WebSocketClient();
  }
  return globalClient;
}

export interface UseWebSocketOptions {
  autoConnect?: boolean;
  clientId?: string;
}

export interface UseWebSocketReturn {
  connected: boolean;
  connecting: boolean;
  error: string | null;
  subscribe: (eventTypes: string[]) => void;
  unsubscribe: (eventTypes: string[]) => void;
  on: (eventType: string, handler: EventHandler) => () => void;
  connect: () => void;
  disconnect: () => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const { autoConnect = true, clientId } = options;
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const clientRef = useRef<WebSocketClient | null>(null);
  const handlersRef = useRef<Map<string, () => void>>(new Map());

  useEffect(() => {
    const client = getWebSocketClient();
    clientRef.current = client;

    // Listen to connection state changes
    const unsubscribeState = client.onConnectionStateChange((isConnected) => {
      setConnected(isConnected);
      setConnecting(false);
      if (!isConnected) {
        setError('Disconnected from server');
      } else {
        setError(null);
      }
    });

    // Connect if auto-connect is enabled
    if (autoConnect && !client.isConnected()) {
      setConnecting(true);
      client.connect(clientId);
    }

    return () => {
      unsubscribeState();
      // Don't disconnect here - let it stay connected for other components
    };
  }, [autoConnect, clientId]);

  const subscribe = useCallback((eventTypes: string[]) => {
    const client = clientRef.current || getWebSocketClient();
    client.subscribe(eventTypes);
  }, []);

  const unsubscribe = useCallback((eventTypes: string[]) => {
    const client = clientRef.current || getWebSocketClient();
    client.unsubscribe(eventTypes);
  }, []);

  const on = useCallback((eventType: string, handler: EventHandler): (() => void) => {
    const client = clientRef.current || getWebSocketClient();
    const unsubscribe = client.on(eventType, handler);
    
    // Store unsubscribe function
    const key = `${eventType}-${handler.toString()}`;
    handlersRef.current.set(key, unsubscribe);
    
    return () => {
      unsubscribe();
      handlersRef.current.delete(key);
    };
  }, []);

  const connect = useCallback(() => {
    const client = clientRef.current || getWebSocketClient();
    setConnecting(true);
    client.connect(clientId);
  }, [clientId]);

  const disconnect = useCallback(() => {
    const client = clientRef.current || getWebSocketClient();
    client.disconnect();
    setConnected(false);
  }, []);

  return {
    connected,
    connecting,
    error,
    subscribe,
    unsubscribe,
    on,
    connect,
    disconnect,
  };
}

// Export EventType for convenience
export { EventType };

