import { useState } from "react";
import { ArrowLeftRight, ChevronDown, ExternalLink } from "lucide-react";
import api from "../api/client";
import useApi from "../hooks/useApi";

function fmtUSD(n) {
  if (n == null) return "\u2014";
  return `$${Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtDate(d) {
  if (!d) return "\u2014";
  return new Date(d).toLocaleString("en-US", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

const statusColors = {
  filled: "bg-profit/20 text-profit",
  closed: "bg-aurora-700/30 text-aurora-400",
  pending: "bg-circuit-yellow/20 text-circuit-yellow",
  cancelled: "bg-loss/20 text-loss-light",
};

export default function Trades() {
  const [filter, setFilter] = useState({});
  const { data: trades, loading, error } = useApi(
    () => api.getTrades({ limit: 50, ...filter }),
    { deps: [JSON.stringify(filter)], refreshInterval: 30000 }
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Trades</h1>
          <p className="text-aurora-400 text-sm mt-1">
            Full trade history with P&L and reasoning
          </p>
        </div>
        <div className="flex gap-2">
          {["all", "filled", "closed", "pending"].map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s === "all" ? {} : { status: s })}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                (filter.status || "all") === s
                  ? "bg-aurora-600 text-white"
                  : "bg-aurora-800/50 text-aurora-400 hover:text-aurora-200"
              }`}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {loading && !trades ? (
        <div className="card text-center py-12">
          <div className="text-aurora-400 animate-pulse">Loading trades...</div>
        </div>
      ) : error && !trades ? (
        <div className="card text-center py-12">
          <p className="text-loss-light">{error}</p>
        </div>
      ) : trades?.length > 0 ? (
        <div className="card overflow-hidden p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-aurora-800/50 text-left text-xs text-aurora-500 uppercase tracking-wider">
                <th className="px-4 py-3">Symbol</th>
                <th className="px-4 py-3">Side</th>
                <th className="px-4 py-3">Qty</th>
                <th className="px-4 py-3">Entry</th>
                <th className="px-4 py-3">Exit</th>
                <th className="px-4 py-3">P&L</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-aurora-800/30">
              {trades.map((trade) => (
                <tr key={trade.id} className="hover:bg-aurora-800/10 transition-colors">
                  <td className="px-4 py-3 font-mono font-bold text-aurora-200">{trade.symbol}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      trade.side === "buy" ? "bg-profit/20 text-profit" : "bg-loss/20 text-loss-light"
                    }`}>
                      {trade.side?.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-sm">{trade.quantity}</td>
                  <td className="px-4 py-3 font-mono text-sm">{fmtUSD(trade.entry_price)}</td>
                  <td className="px-4 py-3 font-mono text-sm">{fmtUSD(trade.exit_price)}</td>
                  <td className={`px-4 py-3 font-mono text-sm font-semibold ${
                    (trade.realized_pnl ?? 0) >= 0 ? "pnl-positive" : "pnl-negative"
                  }`}>
                    {fmtUSD(trade.realized_pnl)}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded ${statusColors[trade.status] || ""}`}>
                      {trade.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-aurora-400">{fmtDate(trade.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="card">
          <div className="text-center py-16">
            <ArrowLeftRight className="w-12 h-12 text-aurora-600 mx-auto mb-4" />
            <p className="text-aurora-400 text-lg">No trades yet</p>
            <p className="text-aurora-600 text-sm mt-1">
              Trade history will appear here once the system starts trading
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
