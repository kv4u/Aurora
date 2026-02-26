import { useState } from "react";
import {
  ClipboardList,
  AlertTriangle,
  Info,
  AlertCircle,
  ChevronRight,
  Link2,
} from "lucide-react";
import api from "../api/client";
import useApi from "../hooks/useApi";

function fmtDate(d) {
  if (!d) return "\u2014";
  return new Date(d).toLocaleString("en-US", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

const severityConfig = {
  INFO: { icon: Info, color: "text-aurora-400", bg: "bg-aurora-700/20" },
  WARNING: { icon: AlertTriangle, color: "text-circuit-yellow", bg: "bg-circuit-yellow/10" },
  ERROR: { icon: AlertCircle, color: "text-loss-light", bg: "bg-loss/10" },
  CRITICAL: { icon: AlertCircle, color: "text-loss", bg: "bg-loss/20" },
};

export default function Audit() {
  const [expandedId, setExpandedId] = useState(null);
  const { data: logs, loading, error } = useApi(
    () => api.getAuditLog({ limit: 100 }),
    { refreshInterval: 15000 }
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Audit Trail</h1>
        <p className="text-aurora-400 text-sm mt-1">
          Complete decision chain tracking and system logs
        </p>
      </div>

      {loading && !logs ? (
        <div className="card text-center py-12">
          <div className="text-aurora-400 animate-pulse">Loading audit log...</div>
        </div>
      ) : error && !logs ? (
        <div className="card text-center py-12">
          <p className="text-loss-light">{error}</p>
        </div>
      ) : logs?.length > 0 ? (
        <div className="space-y-2">
          {logs.map((entry) => {
            const sev = severityConfig[entry.severity] || severityConfig.INFO;
            const SevIcon = sev.icon;
            const isExpanded = expandedId === entry.id;

            return (
              <div key={entry.id} className="card-hover !p-0 overflow-hidden">
                <button
                  onClick={() => setExpandedId(isExpanded ? null : entry.id)}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-aurora-800/10 transition-colors"
                >
                  <div className={`p-1.5 rounded ${sev.bg}`}>
                    <SevIcon className={`w-4 h-4 ${sev.color}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium truncate">{entry.event_type}</span>
                      {entry.decision_chain_id && (
                        <Link2 className="w-3 h-3 text-aurora-600 flex-shrink-0" />
                      )}
                    </div>
                    <p className="text-xs text-aurora-500 truncate">{entry.message}</p>
                  </div>
                  <span className="text-xs text-aurora-600 whitespace-nowrap">{fmtDate(entry.created_at)}</span>
                  <ChevronRight className={`w-4 h-4 text-aurora-600 transition-transform ${isExpanded ? "rotate-90" : ""}`} />
                </button>
                {isExpanded && entry.details && (
                  <div className="px-4 pb-3 border-t border-aurora-800/30">
                    <pre className="text-xs text-aurora-400 overflow-x-auto mt-2 font-mono bg-aurora-950/50 p-3 rounded-lg">
                      {JSON.stringify(entry.details, null, 2)}
                    </pre>
                    {entry.decision_chain_id && (
                      <p className="text-xs text-aurora-600 mt-2">
                        Chain: <span className="font-mono">{entry.decision_chain_id}</span>
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="card">
          <div className="text-center py-16">
            <ClipboardList className="w-12 h-12 text-aurora-600 mx-auto mb-4" />
            <p className="text-aurora-400 text-lg">Audit log is empty</p>
            <p className="text-aurora-600 text-sm mt-1">
              Every decision, trade, and system event will be logged here
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
