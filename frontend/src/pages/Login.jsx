import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Activity, Lock, User } from "lucide-react";
import api from "../api/client";

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const data = await api.login(username, password);
      api.setToken(data.access_token);
      navigate("/");
    } catch (err) {
      setError("Invalid credentials");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-aurora-950">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-aurora-400 to-aurora-600 flex items-center justify-center mx-auto mb-4 animate-glow">
            <Activity className="w-9 h-9 text-white" />
          </div>
          <h1 className="text-3xl font-bold gradient-text">AURORA</h1>
          <p className="text-aurora-400 text-sm mt-2">
            Automated Unified Real-time Orchestrated Analytics
          </p>
        </div>

        {/* Login Form */}
        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-aurora-300 mb-2">
                Username
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-aurora-500" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-aurora-800/50 border border-aurora-700/30 rounded-lg text-white placeholder-aurora-600 focus:outline-none focus:border-aurora-500 focus:ring-1 focus:ring-aurora-500 transition-colors"
                  placeholder="admin"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-aurora-300 mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-aurora-500" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-aurora-800/50 border border-aurora-700/30 rounded-lg text-white placeholder-aurora-600 focus:outline-none focus:border-aurora-500 focus:ring-1 focus:ring-aurora-500 transition-colors"
                  placeholder="Enter password"
                  required
                />
              </div>
            </div>

            {error && (
              <div className="p-3 bg-loss/10 border border-loss/30 rounded-lg text-loss-light text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-aurora-500 to-aurora-600 hover:from-aurora-400 hover:to-aurora-500 text-white font-semibold rounded-lg transition-all duration-300 disabled:opacity-50 active:scale-[0.98]"
            >
              {loading ? "Authenticating..." : "Sign In"}
            </button>
          </form>
        </div>

        <p className="text-center text-aurora-600 text-xs mt-6">
          Single-user system — Create account via CLI
        </p>
      </div>
    </div>
  );
}
