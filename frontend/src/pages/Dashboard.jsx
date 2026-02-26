import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  BarChart3,
  Activity,
  Target,
  Shield,
  Zap,
} from "lucide-react";

// Placeholder data — will be connected to real API
const stats = [
  {
    label: "Total Equity",
    value: "$10,000.00",
    change: "+0.00%",
    positive: true,
    icon: DollarSign,
  },
  {
    label: "Daily P&L",
    value: "$0.00",
    change: "0.00%",
    positive: true,
    icon: TrendingUp,
  },
  {
    label: "Open Positions",
    value: "0",
    change: "of 8 max",
    positive: true,
    icon: BarChart3,
  },
  {
    label: "Win Rate (30d)",
    value: "—",
    change: "No trades yet",
    positive: true,
    icon: Target,
  },
];

export default function Dashboard() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-aurora-400 text-sm mt-1">
            Real-time system overview
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-aurora-800/50 border border-aurora-700/30">
            <span className="status-online" />
            <span className="text-xs text-aurora-300">System Online</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-aurora-800/50 border border-aurora-700/30">
            <Shield className="w-3.5 h-3.5 text-profit" />
            <span className="text-xs text-aurora-300">Risk: Normal</span>
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
                <p
                  className={`text-sm mt-1 ${positive ? "pnl-positive" : "pnl-negative"}`}
                >
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

      {/* Chart Placeholder */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Equity Curve</h2>
        <div className="h-64 flex items-center justify-center border border-aurora-800/30 rounded-lg bg-aurora-950/50">
          <div className="text-center">
            <Activity className="w-12 h-12 text-aurora-600 mx-auto mb-3" />
            <p className="text-aurora-400">
              Chart will appear when trading starts
            </p>
            <p className="text-aurora-600 text-sm mt-1">
              Using TradingView Lightweight Charts
            </p>
          </div>
        </div>
      </div>

      {/* Bottom Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Positions */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Active Positions</h2>
          <div className="text-center py-8">
            <Zap className="w-10 h-10 text-aurora-600 mx-auto mb-3" />
            <p className="text-aurora-400">No active positions</p>
            <p className="text-aurora-600 text-sm">
              Positions will appear here during trading hours
            </p>
          </div>
        </div>

        {/* Recent Signals */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Recent Signals</h2>
          <div className="text-center py-8">
            <Activity className="w-10 h-10 text-aurora-600 mx-auto mb-3" />
            <p className="text-aurora-400">No signals generated yet</p>
            <p className="text-aurora-600 text-sm">
              ML engine will generate signals during market hours
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
