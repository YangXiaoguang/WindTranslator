import { useEffect, useRef, useCallback } from "react";
import type { WsEvent } from "@/types";

interface UseWebSocketOptions {
  projectId: string;
  enabled?: boolean;
  onMessage?: (event: WsEvent) => void;
}

const MAX_RETRIES = 10;
const BASE_DELAY = 1000;

export function useWebSocket({
  projectId,
  enabled = true,
  onMessage,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const enabledRef = useRef(enabled);
  enabledRef.current = enabled;

  const connect = useCallback(() => {
    if (!enabledRef.current) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws/projects/${projectId}/progress`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      retriesRef.current = 0;
    };

    ws.onmessage = (e) => {
      try {
        const parsed = JSON.parse(e.data) as WsEvent;
        onMessage?.(parsed);
        if (parsed.event === "completed" || parsed.event === "error") {
          ws.close();
        }
      } catch {
        /* ignore malformed messages */
      }
    };

    ws.onclose = () => {
      if (!enabledRef.current) return;
      if (retriesRef.current < MAX_RETRIES) {
        const delay = BASE_DELAY * Math.pow(2, retriesRef.current);
        retriesRef.current += 1;
        setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [projectId, onMessage]);

  useEffect(() => {
    if (enabled) {
      connect();
    }
    return () => {
      enabledRef.current = false;
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [enabled, connect]);
}
