"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type WSStatus = "connecting" | "connected" | "reconnecting" | "disconnected";

interface UseWebSocketOptions {
  reconnect?: boolean;
  maxRetries?: number;
  filterTypes?: string[];
}

interface WSMessage {
  type: string;
  [key: string]: any;
}

interface UseWebSocketReturn {
  status: WSStatus;
  lastMessage: WSMessage | null;
  messages: WSMessage[];
  sendMessage: (data: any) => void;
}

export function useWebSocket(
  url: string,
  options: UseWebSocketOptions = {}
): UseWebSocketReturn {
  const { reconnect = false, maxRetries = 5, filterTypes } = options;

  const [status, setStatus] = useState<WSStatus>("connecting");
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);
  const [messages, setMessages] = useState<WSMessage[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmountedRef = useRef(false);

  const connect = useCallback(() => {
    if (unmountedRef.current) return;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      if (unmountedRef.current) return;
      setStatus("connected");
      retriesRef.current = 0;
    };

    ws.onmessage = (event: MessageEvent) => {
      if (unmountedRef.current) return;
      try {
        const data = JSON.parse(event.data) as WSMessage;
        if (filterTypes && !filterTypes.includes(data.type)) return;
        setLastMessage(data);
        setMessages((prev) => [...prev, data]);
      } catch {
        // Ignore non-JSON messages
      }
    };

    ws.onclose = () => {
      if (unmountedRef.current) return;
      if (reconnect && retriesRef.current < maxRetries) {
        setStatus("reconnecting");
        const delay = Math.min(1000 * Math.pow(2, retriesRef.current), 30000);
        retriesRef.current += 1;
        reconnectTimerRef.current = setTimeout(() => {
          connect();
        }, delay);
      } else {
        setStatus("disconnected");
      }
    };

    ws.onerror = () => {
      // onclose will fire after onerror
    };
  }, [url, reconnect, maxRetries, filterTypes]);

  useEffect(() => {
    unmountedRef.current = false;
    connect();

    return () => {
      unmountedRef.current = true;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      wsRef.current?.close();
    };
  }, [connect]);

  const sendMessage = useCallback((data: any) => {
    if (wsRef.current?.readyState === 1) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { status, lastMessage, messages, sendMessage };
}
