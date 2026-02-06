/**
 * useWebSocket Hook - WebSocket connection management
 * 
 * React hook for managing WebSocket connections with reconnection support.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { websocketService } from '../services/websocket.service';

export interface UseWebSocketReturn {
  isConnected: boolean;
  lastMessage: unknown | null;
  sendMessage: (data: unknown) => boolean;
  connect: () => void;
  disconnect: () => void;
  connectionState: string;
}

export interface UseWebSocketOptions {
  autoConnect?: boolean;
  onMessage?: (data: unknown) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
}

export const useWebSocket = (options: UseWebSocketOptions = {}): UseWebSocketReturn => {
  const {
    autoConnect = false,
    onMessage,
    onConnect,
    onDisconnect,
    onError,
  } = options;

  const [isConnected, setIsConnected] = useState(websocketService.isConnected);
  const [lastMessage, setLastMessage] = useState<unknown | null>(null);
  const [connectionState, setConnectionState] = useState(websocketService.connectionState);

  // Store callbacks in refs to avoid re-subscribing
  const onMessageRef = useRef(onMessage);
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);
  const onErrorRef = useRef(onError);

  // Update refs when callbacks change
  useEffect(() => {
    onMessageRef.current = onMessage;
    onConnectRef.current = onConnect;
    onDisconnectRef.current = onDisconnect;
    onErrorRef.current = onError;
  }, [onMessage, onConnect, onDisconnect, onError]);

  // Subscribe to WebSocket events
  useEffect(() => {
    const unsubMessage = websocketService.onMessage((data) => {
      setLastMessage(data);
      onMessageRef.current?.(data);
    });

    const unsubConnect = websocketService.onConnect(() => {
      setIsConnected(true);
      setConnectionState('OPEN');
      onConnectRef.current?.();
    });

    const unsubDisconnect = websocketService.onDisconnect(() => {
      setIsConnected(false);
      setConnectionState('CLOSED');
      onDisconnectRef.current?.();
    });

    const unsubError = websocketService.onError((error) => {
      onErrorRef.current?.(error);
    });

    // Auto-connect if enabled
    if (autoConnect) {
      websocketService.connect();
    }

    return () => {
      unsubMessage();
      unsubConnect();
      unsubDisconnect();
      unsubError();
    };
  }, [autoConnect]);

  const connect = useCallback(() => {
    websocketService.connect();
  }, []);

  const disconnect = useCallback(() => {
    websocketService.disconnect();
  }, []);

  const sendMessage = useCallback((data: unknown): boolean => {
    return websocketService.send(data);
  }, []);

  return {
    isConnected,
    lastMessage,
    sendMessage,
    connect,
    disconnect,
    connectionState,
  };
};


