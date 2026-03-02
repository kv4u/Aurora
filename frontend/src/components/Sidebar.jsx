import { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  ArrowLeftRight,
  Signal,
  Brain,
  ClipboardList,
  Settings as SettingsIcon,
  Activity,
  ShieldAlert,
  Loader2,
} from "lucide-react";
import clsx from "clsx";
import api from "../api/client";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/trades", icon: ArrowLeftRight, label: "Trades" },
  { to: "/signals", icon: Signal, label: "Signals" },
  { to: "/analysis", icon: Brain, label: "Analysis" },
  { to: "/audit", icon: ClipboardList, label: "Audit" },
  { to: "/settings", icon: SettingsIcon, label: "Settings" },
];

export default function Sidebar() {
  const [stopping, setStopping] = useState(false);
  const [stopConfirm, setStopConfirm] = useState(false);

  const handleEmergencyStop = async () => {
    if (!stopConfirm) {
      setStopConfirm(true);
      setTimeout(() => setStopConfirm(false), 3000);
      return;
    }

    setStopping(true);
    try {
      await api.emergencyStop();
    } catch {
      // Still complete — emergency stops should always "feel" responsive
    } finally {
      setStopping(false);
      setStopConfirm(false);
    }
  };

  return (
    <aside className="w-64 bg-aurora-950 border-r border-aurora-800/50 flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-aurora-800/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aurora-400 to-aurora-600 flex items-center justify-center">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold gradient-text">AURORA</h1>
            <p className="text-xs text-aurora-400">Trading System</p>
          </div>
        </div>
      </div>

      {/* System Status */}
      <div className="px-6 py-4 border-b border-aurora-800/50">
        <div className="flex items-center gap-2">
          <span className="status-online" />
          <span className="text-xs text-aurora-300 uppercase tracking-wider">
            Paper Mode
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200",
                isActive
                  ? "bg-aurora-800/60 text-aurora-300 border-l-2 border-aurora-400"
                  : "text-aurora-400 hover:text-aurora-200 hover:bg-aurora-800/30"
              )
            }
          >
            <Icon className="w-5 h-5" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Emergency Stop */}
      <div className="p-4 border-t border-aurora-800/50">
        <button
          onClick={handleEmergencyStop}
          disabled={stopping}
          className={clsx(
            "w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg transition-all duration-200 active:scale-95",
            stopConfirm
              ? "bg-loss text-white border-2 border-loss animate-pulse"
              : "bg-loss/20 hover:bg-loss/40 text-loss-light border border-loss/30"
          )}
        >
          {stopping ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <ShieldAlert className="w-5 h-5" />
          )}
          <span className="text-sm font-bold uppercase tracking-wider">
            {stopConfirm ? "CONFIRM STOP" : "Emergency Stop"}
          </span>
        </button>
      </div>
    </aside>
  );
}
