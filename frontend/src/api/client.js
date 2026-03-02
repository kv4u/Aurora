/**
 * AURORA API Client — handles all backend communication.
 */

const BASE_URL = "/api/v1";

class AuroraClient {
  constructor() {
    this.token = localStorage.getItem("aurora_token");
  }

  get headers() {
    const h = { "Content-Type": "application/json" };
    if (this.token) h["Authorization"] = `Bearer ${this.token}`;
    return h;
  }

  setToken(token) {
    this.token = token;
    localStorage.setItem("aurora_token", token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem("aurora_token");
  }

  async request(method, path, body = null) {
    const opts = { method, headers: this.headers };
    if (body) opts.body = JSON.stringify(body);

    const res = await fetch(`${BASE_URL}${path}`, opts);

    if (res.status === 401) {
      this.clearToken();
      window.location.href = "/login";
      throw new Error("Unauthorized");
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Request failed: ${res.status}`);
    }

    return res.json();
  }

  // Auth
  login(username, password) {
    return this.request("POST", "/auth/login", { username, password });
  }

  // Dashboard
  getDashboard() {
    return this.request("GET", "/dashboard");
  }

  // Portfolio
  getPortfolio() {
    return this.request("GET", "/portfolio");
  }

  getEquityCurve(days = 30) {
    return this.request("GET", `/portfolio/equity-curve?days=${days}`);
  }

  // Trades
  getTrades(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this.request("GET", `/trades?${qs}`);
  }

  getTrade(id) {
    return this.request("GET", `/trades/${id}`);
  }

  // Signals
  getSignals(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this.request("GET", `/signals?${qs}`);
  }

  // Audit
  getAuditLog(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this.request("GET", `/audit?${qs}`);
  }

  getDecisionChain(chainId) {
    return this.request("GET", `/audit/chain/${chainId}`);
  }

  // Settings
  getSettings() {
    return this.request("GET", "/settings");
  }

  updateSettings(settings) {
    return this.request("PUT", "/settings", settings);
  }

  // Analysis
  getWatchlistOverview() {
    return this.request("GET", "/analysis");
  }

  analyzeSymbol(symbol) {
    return this.request("GET", `/analysis/${symbol}`);
  }

  // Emergency
  emergencyStop() {
    return this.request("POST", "/emergency-stop");
  }
}

export const api = new AuroraClient();
export default api;
