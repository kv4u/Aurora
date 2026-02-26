import { useEffect, useRef, useMemo } from "react";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  BarChart3,
  Activity,
  Target,
  Shield,
  Zap,
  Wifi,
  WifiOff,
} from "lucide-react";
import api from "../api/client";
import useApi from "../hooks/useApi";
import useWebSocket from "../hooks/useWebSocket";

function fmt(n, decimals = 2) {
  if (n == null) return "\u2014";
  return Number(n).toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function fmtUSD(n) {
  if (n == null) return "\u2014";
  return `$${fmt(n)}`;
}

function fmtPct(n) {
  if (n == null) return "\u2014";
  const sign = n >= 0 ? "+" : "";
  return `${sign}${fmt(n)}%`;
}

const circuitColors = {
  GREEN: "text-profit",
  YELLOW: "text-circuit-yellow",
  ORANGE: "text-circuit-orange",
  RED: "text-loss",
};

export default function Dashboard() {
  const { data, loading, error } = useApi(() => api.getDashboard(), {
    refreshInterval: 30000,
  });

  const { connected, portfolio: wsPortfolio, signals: wsSignals, circuitBreaker } = useWebSocket();

  // Merge: WebSocket data overrides REST data when available
  const portfolio = wsPortfolio || data?.portfolio;
  const recentSignals = wsSignals.length > 0 ? wsSignals : (data?.recent_signals || []);
  const positions = portfolio?.positions || [];
  const cbLevel = circuitBreaker?.level || "GREEN";

  const stats = useMemo(() => [
    {
      label: "Total Equity",
      value: fmtUSD(portfolio?.total_equity),
      change: fmtPct(portfolio?.daily_pnl_pct),
      positive: (portfolio?.daily_pnl_pct ?? 0) >= 0,
      icon: DollarSign,
    },
    {
      label: "Daily P&L",
      value: fmtUSD(portfolio?.daily_pnl),
      change: fmtPct(portfolio?.daily_pnl_pct),
      positive: (portfolio?.daily_pnl ?? 0) >= 0,
      icon: (portfolio?.daily_pnl ?? 0) >= 0 ? TrendingUp : TrendingDown,
    },
    {
      label: "Open Positions",
      value: String(portfolio?.open_positions_count ?? 0),
      change: `of ${data?.max_positions ?? 8} max`,
      positive: true,
      icon: BarChart3,
    },
    {
      label: "Win Rate (30d)",
      value: data?.win_rate != null ? `${fmt(data.win_rate)}%` : "\u2014",
      change: data?.total_trades != null ? `${data.total_trades} trades` : "No trades yet",
      positive: (data?.win_rate ?? 50) >= 50,
      icon: Target,
    },
  ], [portfolio, data]);

  // Equity chart ref
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);

  const { data: equityCurve } = useApi(() => api.getEquityCurve(30), {
    refreshInterval: 60000,
  });

  useEffect(() => {
    if (!chartContainerRef.current || !equityCurve?.length) return;

    let chart;
    const initChart = async () => {
      try {
        const { createChart, LineSeries } = await import("lightweight-charts");
        if (chartRef.current) chartRef.current.remove();

        chart = createChart(chartContainerRef.current, {
          width: chartContainerRef.current.clientWidth,
          height: 256,
          layout: {
            background: { type: "solid", color: "transparent" },
            textColor: "#8892b0",
            fontSize: 12,
          },
          grid: {
            vertLines: { color: "rgba(136,146,176,0.08)" },
            horzLines: { color: "rgba(136,146,176,0.08)" },
          },
          crosshair: { mode: 0 },
          rightPriceScale: { borderColor: "rgba(136,146,176,0.15)" },
          timeScale: { borderColor: "rgba(136,146,176,0.15)" },
        });

        const series = chart.addSeries(LineSeries, {
          color: "#6366f1",
          lineWidth: 2,
          crosshairMarkerRadius: 4,
        });

        const chartData = equityCurve.map((pt) => ({
          time: pt.timestamp?.split("T")[0] || pt.date,
          value: pt.equity || pt.total_equity,
        }));

        series.setData(chartData);
        chart.timeScale().fitContent();
        chartRef.current = chart;
      } catch {
        // lightweight-charts not available yet
      }
    };

    initChart();

    const handleResize = () => {
      if (chartRef.current && chartContainerRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      if (chart) chart.remove();
    };
  }, [equityCurve]);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-aurora-400 animate-pulse">Loading dashboard...</div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="card text-center py-12">
        <Activity className="w-12 h-12 text-loss mx-auto mb-3" />
        <p className="text-loss-light mb-2">Failed to load dashboard</p>
        <p className="text-aurora-500 text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-aurora-400 text-sm mt-1">Real-time system overview</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-aurora-800/50 border border-aurora-700/30">
            {connected ? (
              <>
                <Wifi className="w-3.5 h-3.5 text-profit" />
                <span className="text-xs text-aurora-300">Live</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3.5 h-3.5 text-aurora-500" />
                <span className="text-xs text-aurora-500">Offline</span>
              </>
            )}
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-aurora-800/50 border border-aurora-700/30">
            <Shield className={`w-3.5 h-3.5 ${circuitColors[cbLevel] || "text-profit"}`} />
            <span className="text-xs text-aurora-300">
              Risk: {cbLevel === "GREEN" ? "Normal" : cbLevel}
            </span>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map(({ label, value, change, positive, icon: Icon }) => (
          <div key={label} className="card-hover">
            <div className="flex items-start justify-between">
              <div>
                <p className="stat-label">{label}</p>
                <p className="stat-value mt-2">{value}</p>
                <p className={`text-sm mt-1 ${positive ? "pnl-positive" : "pnl-negative"}`}>
                  {change}
                </p>
              </div>
              <div className="p-2 rounded-lg bg-aurora-800/50">
                <Icon className="w-5 h-5 text-aurora-400" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Equity Chart */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Equity Curve</h2>
        {equityCurve?.length > 0 ? (
          <div ref={chartContainerRef} className="h-64" />
        ) : (
          <div className="h-64 flex items-center justify-center border border-aurora-800/30 rounded-lg bg-aurora-950/50">
            <div className="text-center">
              <Activity className="w-12 h-12 text-aurora-600 mx-auto mb-3" />
              <p className="text-aurora-400">Chart will appear when trading starts</p>
              <p className="text-aurora-600 text-sm mt-1">TradingView Lightweight Charts</p>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Positions */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Active Positions</h2>
          {positions.length > 0 ? (
            <div className="space-y-3">
              {positions.map((pos, idx) => (
                <div key={pos.symbol || idx} className="flex items-center justify-between p-3 bg-aurora-800/20 rounded-lg">
                  <div className="flex items-center gap-3">
                    <span className="font-mono font-bold text-aurora-200">{pos.symbol}</span>
                    <span className={`text-xs px-2 py-0.5 rounded ${pos.side === "long" ? "bg-profit/20 text-profit" : "bg-loss/20 text-loss-light"}`}>
                      {pos.side?.toUpperCase() || "LONG"}
                    </span>
                  </div>
                  <div className="text-right">
                    <p className="font-mono text-sm">{pos.qty} shares</p>
                    <p className={`text-xs ${(pos.unrealized_pl ?? 0) >= 0 ? "pnl-positive" : "pnl-negative"}`}>
                      {fmtUSD(pos.unrealized_pl)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Zap className="w-10 h-10 text-aurora-600 mx-auto mb-3" />
              <p className="text-aurora-400">No active positions</p>
              <p className="text-aurora-600 text-sm">Positions will appear here during trading hours</p>
            </div>
          )}
        </div>

        {/* Recent Signals */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Recent Signals</h2>
          {recentSignals.length > 0 ? (
            <div className="space-y-3">
              {recentSignals.slice(0, 5).map((sig, idx) => (
                <div key={sig.id || idx} className="flex items-center justify-between p-3 bg-aurora-800/20 rounded-lg">
                  <div className="flex items-center gap-3">
                    <span className="font-mono font-bold text-aurora-200">{sig.symbol}</span>
                    <span className={`text-xs px-2 py-0.5 rounded font-bold ${
                      sig.action === "BUY" ? "bg-profit/20 text-profit" :
                      sig.action === "SELL" ? "bg-loss/20 text-loss-light" :
                      "bg-aurora-700/30 text-aurora-400"
                    }`}>
                      {sig.action}
                    </span>
                  </div>
                  <div className="text-right">
                    <p className="font-mono text-sm text-aurora-300">
                      {fmt(sig.confidence ? sig.confidence * 100 : 0, 1)}%
                    </p>
                    <p className="text-xs text-aurora-500">confidence</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Activity className="w-10 h-10 text-aurora-600 mx-auto mb-3" />
              <p className="text-aurora-400">No signals generated yet</p>
              <p className="text-aurora-600 text-sm">ML engine will generate signals during market hours</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
