import { useEffect, useRef, useState, useCallback } from "react";

/**
 * WebSocket hook for real-time AURORA updates.
 */
export default function useWebSocket() {
  const ws = useRef(null);
  const reconnectTimer = useRef(null);
  const [connected, setConnected] = useState(false);
  const [portfolio, setPortfolio] = useState(null);
  const [signals, setSignals] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [circuitBreaker, setCircuitBreaker] = useState(null);

  const connect = useCallback(() => {
    const token = localStorage.getItem("aurora_token");
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/api/v1/ws${token ? `?token=${token}` : ""}`;

    ws.current = new WebSocket(url);

    ws.current.onopen = () => {
      setConnected(true);
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case "portfolio_update":
          setPortfolio(data.payload);
          break;
        case "new_signal":
          setSignals((prev) => [data.payload, ...prev.slice(0, 49)]);
          break;
        case "trade_executed":
          // Could trigger a notification
          break;
        case "risk_alert":
          setAlerts((prev) => [data.payload, ...prev.slice(0, 19)]);
          break;
        case "circuit_breaker":
          setCircuitBreaker(data.payload);
          break;
      }
    };

    ws.current.onclose = () => {
      setConnected(false);
      // Auto-reconnect after 3 seconds
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.current.onerror = () => {
      ws.current?.close();
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      ws.current?.close();
    };
  }, [connect]);

  return { connected, portfolio, signals, alerts, circuitBreaker };
}
