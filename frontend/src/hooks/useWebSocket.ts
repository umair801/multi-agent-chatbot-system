'use client';

import { useCallback, useRef, useEffect, useState } from 'react';

interface StepUpdate {
  type: string;
  timestamp: string;
  step: {
    step_number: number;
    agent_type: string;
    action: string;
    status: string;
    result?: Record<string, unknown>;
    error?: string;
  };
}

export function useWebSocket(sessionId: string, enabled: boolean = false) {
  const ws = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [steps, setSteps] = useState<StepUpdate[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled || !sessionId) {
      return;
    }

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const protocol = backendUrl.startsWith('https') ? 'wss' : 'ws';
    const baseUrl = backendUrl.replace(/^https?:\/\//, '');
    const wsUrl = protocol + '://' + baseUrl + '/ws/execute/' + sessionId;

    try {
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log('WebSocket connected:', sessionId);
        setConnected(true);
        setError(null);
      };

      ws.current.onmessage = (event: MessageEvent<string>) => {
        try {
          const data: StepUpdate = JSON.parse(event.data);
          console.log('Step received:', data.step);
          setSteps((prev) => [...prev, data]);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.current.onerror = () => {
        console.error('WebSocket error');
        setError('WebSocket connection error');
      };

      ws.current.onclose = () => {
        console.log('WebSocket disconnected');
        setConnected(false);
      };
    } catch (err) {
      console.error('Failed to establish WebSocket:', err);
      setError('Failed to connect to real-time updates');
    }

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [sessionId, enabled]);

  const sendMessage = useCallback((message: string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(message);
    }
  }, []);

  return { connected, steps, error, sendMessage };
}
