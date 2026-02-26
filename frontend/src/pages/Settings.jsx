import { Settings as SettingsIcon, Shield, AlertTriangle } from "lucide-react";

export default function Settings() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-aurora-400 text-sm mt-1">
          System configuration and risk parameters
        </p>
      </div>

      {/* Mode Toggle */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Shield className="w-5 h-5 text-aurora-400" />
          Trading Mode
        </h2>
        <div className="flex items-center gap-4">
          <button className="px-6 py-3 bg-aurora-600 text-white rounded-lg font-medium border-2 border-aurora-400">
            Paper Trading
          </button>
          <button className="px-6 py-3 bg-aurora-800/50 text-aurora-400 rounded-lg font-medium border-2 border-aurora-800/50 hover:border-loss/50 hover:text-loss transition-colors">
            Live Trading
          </button>
        </div>
        <p className="text-aurora-500 text-sm mt-3">
          Switch to live trading only after successful paper trading validation
        </p>
      </div>

      {/* Risk Limits */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-circuit-yellow" />
          Risk Limits
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            { label: "Max Position Size", value: "5%", max: "10%" },
            { label: "Max Daily Loss", value: "3%", max: "5%" },
            { label: "Max Weekly Loss", value: "5%", max: "10%" },
            { label: "Max Monthly Loss", value: "8%", max: "15%" },
            { label: "Max Drawdown", value: "12%", max: "20%" },
            { label: "Max Open Positions", value: "8", max: "15" },
            { label: "Max Trades/Day", value: "10", max: "20" },
            { label: "Min Confidence", value: "60%", max: "—" },
          ].map(({ label, value, max }) => (
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
          {[
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META",
            "TSLA", "JPM", "V", "UNH", "SPY", "QQQ",
          ].map((symbol) => (
            <span
              key={symbol}
              className="px-3 py-1.5 bg-aurora-800/50 border border-aurora-700/30 rounded-lg text-sm font-mono text-aurora-300"
            >
              {symbol}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
