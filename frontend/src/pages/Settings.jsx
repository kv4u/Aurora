import { Settings as SettingsIcon, Shield, AlertTriangle, LogOut } from "lucide-react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";
import useApi from "../hooks/useApi";
import { useAuth } from "../context/AuthContext";

export default function Settings() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const { data: settings, loading } = useApi(() => api.getSettings());

  const mode = settings?.mode || "paper";
  const watchlist = settings?.watchlist || [];

  const riskLimits = [
    { label: "Max Position Size", value: settings?.max_position_pct ? `${settings.max_position_pct}%` : "5%", max: "10%" },
    { label: "Max Daily Loss", value: settings?.max_daily_loss_pct ? `${settings.max_daily_loss_pct}%` : "3%", max: "5%" },
    { label: "Max Weekly Loss", value: settings?.max_weekly_loss_pct ? `${settings.max_weekly_loss_pct}%` : "5%", max: "10%" },
    { label: "Max Monthly Loss", value: settings?.max_monthly_loss_pct ? `${settings.max_monthly_loss_pct}%` : "8%", max: "15%" },
    { label: "Max Drawdown", value: settings?.max_drawdown_pct ? `${settings.max_drawdown_pct}%` : "12%", max: "20%" },
    { label: "Max Open Positions", value: String(settings?.max_open_positions ?? 8), max: "15" },
    { label: "Max Trades/Day", value: String(settings?.max_trades_per_day ?? 10), max: "20" },
    { label: "Min Confidence", value: settings?.min_confidence ? `${settings.min_confidence}%` : "60%", max: "\u2014" },
  ];

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Settings</h1>
          <p className="text-aurora-400 text-sm mt-1">
            System configuration and risk parameters
          </p>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 px-4 py-2 bg-aurora-800/50 text-aurora-400 hover:text-loss-light hover:bg-loss/10 border border-aurora-700/30 hover:border-loss/30 rounded-lg transition-all text-sm"
        >
          <LogOut className="w-4 h-4" />
          Sign Out
        </button>
      </div>

      {/* Mode Toggle */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Shield className="w-5 h-5 text-aurora-400" />
          Trading Mode
        </h2>
        <div className="flex items-center gap-4">
          <button
            className={`px-6 py-3 rounded-lg font-medium border-2 transition-colors ${
              mode === "paper"
                ? "bg-aurora-600 text-white border-aurora-400"
                : "bg-aurora-800/50 text-aurora-400 border-aurora-800/50 hover:border-aurora-600"
            }`}
          >
            Paper Trading
          </button>
          <button
            className={`px-6 py-3 rounded-lg font-medium border-2 transition-colors ${
              mode === "live"
                ? "bg-loss/30 text-loss-light border-loss/50"
                : "bg-aurora-800/50 text-aurora-400 border-aurora-800/50 hover:border-loss/50 hover:text-loss"
            }`}
          >
            Live Trading
          </button>
        </div>
        <p className="text-aurora-500 text-sm mt-3">
          {mode === "paper"
            ? "Currently running in paper mode — no real money at risk"
            : "LIVE MODE ACTIVE — real trades will be executed"}
        </p>
      </div>

      {/* Risk Limits */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-circuit-yellow" />
          Risk Limits
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {riskLimits.map(({ label, value, max }) => (
            <div
              key={label}
              className="flex items-center justify-between p-3 bg-aurora-800/20 rounded-lg"
            >
              <div>
                <p className="text-sm font-medium">{label}</p>
                <p className="text-xs text-aurora-500">Hard max: {max}</p>
              </div>
              <span className="font-mono text-aurora-300 font-semibold">
                {value}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Watchlist */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <SettingsIcon className="w-5 h-5 text-aurora-400" />
          Watchlist
        </h2>
        <div className="flex flex-wrap gap-2">
          {(watchlist.length > 0 ? watchlist : [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META",
            "TSLA", "JPM", "V", "UNH", "SPY", "QQQ",
          ]).map((symbol) => (
            <span
              key={symbol}
              className="px-3 py-1.5 bg-aurora-800/50 border border-aurora-700/30 rounded-lg text-sm font-mono text-aurora-300"
            >
              {symbol}
            </span>
          ))}
        </div>
      </div>

      {/* System Info */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <SettingsIcon className="w-5 h-5 text-aurora-400" />
          System Info
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div className="p-3 bg-aurora-800/20 rounded-lg">
            <p className="text-aurora-500">Version</p>
            <p className="font-mono text-aurora-300 mt-1">1.0.0</p>
          </div>
          <div className="p-3 bg-aurora-800/20 rounded-lg">
            <p className="text-aurora-500">ML Model</p>
            <p className="font-mono text-aurora-300 mt-1">LightGBM v4</p>
          </div>
          <div className="p-3 bg-aurora-800/20 rounded-lg">
            <p className="text-aurora-500">Broker</p>
            <p className="font-mono text-aurora-300 mt-1">Alpaca Markets</p>
          </div>
        </div>
      </div>
    </div>
  );
}
