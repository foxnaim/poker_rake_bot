/**
 * React hook для WebSocket подключения
 */

import { useEffect, useState, useRef } from 'react';

interface WebSocketMessage {
  type: string;
  timestamp: string;
  data?: any;
  metrics?: any;
}

export const useWebSocket = (url: string) => {
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const connect = () => {
      try {
        const ws = new WebSocket(url);

        ws.onopen = () => {
          setIsConnected(true);
          console.log('WebSocket connected');
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setMessages(prev => [...prev, data].slice(-100)); // Храним последние 100 сообщений
          } catch (e) {
            console.error('Error parsing WebSocket message:', e);
          }
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
        };

        ws.onclose = () => {
          setIsConnected(false);
          console.log('WebSocket disconnected');
          
          // Переподключение через 5 секунд
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, 5000);
        };

        wsRef.current = ws;
      } catch (error) {
        console.error('Error creating WebSocket:', error);
      }
    };

    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [url]);

  return { messages, isConnected };
};
