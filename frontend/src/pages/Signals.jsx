import { useState } from "react";
import { Signal, Brain, CheckCircle, XCircle, Clock } from "lucide-react";
import api from "../api/client";
import useApi from "../hooks/useApi";

function fmt(n, d = 1) {
  if (n == null) return "\u2014";
  return Number(n).toFixed(d);
}

function fmtDate(d) {
  if (!d) return "\u2014";
  return new Date(d).toLocaleString("en-US", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

const actionColors = {
  BUY: "bg-profit/20 text-profit border-profit/30",
  SELL: "bg-loss/20 text-loss-light border-loss/30",
  HOLD: "bg-aurora-700/30 text-aurora-400 border-aurora-700/30",
};

export default function Signals() {
  const [filter, setFilter] = useState({});
  const { data: signals, loading, error } = useApi(
    () => api.getSignals({ limit: 50, ...filter }),
    { deps: [JSON.stringify(filter)], refreshInterval: 15000 }
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Signals</h1>
          <p className="text-aurora-400 text-sm mt-1">
            ML-generated signals and confidence analysis
          </p>
        </div>
        <div className="flex gap-2">
          {["all", "BUY", "SELL", "HOLD"].map((a) => (
            <button
              key={a}
              onClick={() => setFilter(a === "all" ? {} : { action: a })}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                (filter.action || "all") === a
                  ? "bg-aurora-600 text-white"
                  : "bg-aurora-800/50 text-aurora-400 hover:text-aurora-200"
              }`}
            >
              {a}
            </button>
          ))}
        </div>
      </div>

      {loading && !signals ? (
        <div className="card text-center py-12">
          <div className="text-aurora-400 animate-pulse">Loading signals...</div>
        </div>
      ) : error && !signals ? (
        <div className="card text-center py-12">
          <p className="text-loss-light">{error}</p>
        </div>
      ) : signals?.length > 0 ? (
        <div className="space-y-3">
          {signals.map((sig) => (
            <div key={sig.id} className="card-hover">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <span className="font-mono text-lg font-bold text-aurora-200">{sig.symbol}</span>
                  <span className={`px-3 py-1 rounded-lg text-sm font-bold border ${actionColors[sig.action] || ""}`}>
                    {sig.action}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <Brain className="w-4 h-4 text-aurora-500" />
                    <span className="font-mono text-sm text-aurora-300">
                      {fmt(sig.confidence ? sig.confidence * 100 : 0)}% confidence
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {/* Claude review status */}
                  {sig.claude_approved != null && (
                    <div className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs ${
                      sig.claude_approved ? "bg-profit/10 text-profit" : "bg-loss/10 text-loss-light"
                    }`}>
                      {sig.claude_approved ? (
                        <CheckCircle className="w-3.5 h-3.5" />
                      ) : (
                        <XCircle className="w-3.5 h-3.5" />
                      )}
                      Claude {sig.claude_approved ? "Approved" : "Rejected"}
                    </div>
                  )}
                  {/* Risk check */}
                  {sig.risk_approved != null && (
                    <div className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs ${
                      sig.risk_approved ? "bg-profit/10 text-profit" : "bg-loss/10 text-loss-light"
                    }`}>
                      {sig.risk_approved ? (
                        <CheckCircle className="w-3.5 h-3.5" />
                      ) : (
                        <XCircle className="w-3.5 h-3.5" />
                      )}
                      Risk {sig.risk_approved ? "OK" : "Vetoed"}
                    </div>
                  )}
                  <span className="text-xs text-aurora-500">{fmtDate(sig.created_at)}</span>
                </div>
              </div>
              {sig.claude_reasoning && (
                <p className="mt-3 text-sm text-aurora-400 border-t border-aurora-800/30 pt-3">
                  <Brain className="w-3.5 h-3.5 inline mr-1.5 text-aurora-500" />
                  {sig.claude_reasoning}
                </p>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="card">
          <div className="text-center py-16">
            <Signal className="w-12 h-12 text-aurora-600 mx-auto mb-4" />
            <p className="text-aurora-400 text-lg">No signals generated</p>
            <p className="text-aurora-600 text-sm mt-1">
              The signal engine will generate BUY/SELL/HOLD signals during market hours
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
