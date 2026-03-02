import { useState } from "react";
import {
  Brain,
  TrendingUp,
  TrendingDown,
  Minus,
  Search,
  Loader2,
  Target,
  Shield,
  AlertTriangle,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";
import api from "../api/client";
import useApi from "../hooks/useApi";

function fmt(n, d = 2) {
  if (n == null) return "\u2014";
  return Number(n).toFixed(d);
}

function fmtUSD(n) {
  if (n == null) return "\u2014";
  return `$${Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const directionConfig = {
  bullish: { color: "text-profit", bg: "bg-profit/15", border: "border-profit/30", icon: TrendingUp, label: "Bullish" },
  bearish: { color: "text-loss-light", bg: "bg-loss/15", border: "border-loss/30", icon: TrendingDown, label: "Bearish" },
  neutral: { color: "text-aurora-400", bg: "bg-aurora-700/30", border: "border-aurora-700/30", icon: Minus, label: "Neutral" },
};

const trendColors = {
  bullish: "text-profit",
  bearish: "text-loss-light",
  mixed: "text-circuit-yellow",
  neutral: "text-aurora-400",
};

function ConvictionBar({ score }) {
  const pct = (score / 10) * 100;
  const color =
    score >= 7 ? "bg-profit" : score >= 4 ? "bg-circuit-yellow" : "bg-loss";
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2.5 bg-aurora-800 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono font-bold text-lg">{score}/10</span>
    </div>
  );
}

function KeyLevel({ label, value, type }) {
  if (!value) return null;
  const color = type === "support" ? "text-profit" : "text-loss-light";
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-aurora-400 text-sm">{label}</span>
      <span className={`font-mono text-sm font-medium ${color}`}>{fmtUSD(value)}</span>
    </div>
  );
}

export default function Analysis() {
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [analysisError, setAnalysisError] = useState(null);

  const { data: overview, loading, error } = useApi(
    () => api.getWatchlistOverview(),
    { refreshInterval: 30000 }
  );

  const handleAnalyze = async (symbol) => {
    setSelectedSymbol(symbol);
    setAnalyzing(true);
    setAnalysis(null);
    setAnalysisError(null);

    try {
      const result = await api.analyzeSymbol(symbol);
      setAnalysis(result);
    } catch (err) {
      setAnalysisError(err.message || "Analysis failed");
    } finally {
      setAnalyzing(false);
    }
  };

  const dir = analysis ? directionConfig[analysis.direction] || directionConfig.neutral : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Analysis</h1>
        <p className="text-aurora-400 text-sm mt-1">
          AI-powered deep financial analysis
        </p>
      </div>

      {/* Watchlist Overview */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-aurora-500" />
          Watchlist
        </h2>
        {loading && !overview ? (
          <div className="text-center py-8">
            <div className="text-aurora-400 animate-pulse">Loading watchlist...</div>
          </div>
        ) : error && !overview ? (
          <div className="text-center py-8 text-loss-light">{error}</div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
            {(overview || []).map((item) => (
              <button
                key={item.symbol}
                onClick={() => handleAnalyze(item.symbol)}
                disabled={analyzing}
                className={`flex flex-col items-center p-3 rounded-lg border transition-all duration-200 ${
                  selectedSymbol === item.symbol
                    ? "bg-aurora-700/40 border-aurora-500/50"
                    : "bg-aurora-800/20 border-aurora-800/30 hover:bg-aurora-800/40 hover:border-aurora-700/40"
                }`}
              >
                <span className="font-mono font-bold text-sm text-aurora-200">{item.symbol}</span>
                <span className="text-xs text-aurora-500 mt-0.5">{item.sector}</span>
                {item.price > 0 && (
                  <span className="font-mono text-xs text-aurora-300 mt-1">{fmtUSD(item.price)}</span>
                )}
                <div className="flex items-center gap-1 mt-1">
                  {item.change_pct > 0 ? (
                    <ArrowUpRight className="w-3 h-3 text-profit" />
                  ) : item.change_pct < 0 ? (
                    <ArrowDownRight className="w-3 h-3 text-loss-light" />
                  ) : null}
                  <span className={`text-xs font-mono ${
                    item.change_pct > 0 ? "text-profit" : item.change_pct < 0 ? "text-loss-light" : "text-aurora-500"
                  }`}>
                    {item.change_pct > 0 ? "+" : ""}{fmt(item.change_pct, 1)}%
                  </span>
                </div>
                {item.trend && item.trend !== "neutral" && (
                  <span className={`text-[10px] mt-1 ${trendColors[item.trend] || "text-aurora-500"}`}>
                    {item.trend.toUpperCase()}
                  </span>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Analysis Result */}
      {analyzing && (
        <div className="card">
          <div className="flex flex-col items-center py-16">
            <Loader2 className="w-10 h-10 text-aurora-400 animate-spin mb-4" />
            <p className="text-aurora-300 text-lg">Analyzing {selectedSymbol}...</p>
            <p className="text-aurora-500 text-sm mt-1">Running deep financial analysis</p>
          </div>
        </div>
      )}

      {analysisError && !analyzing && (
        <div className="card">
          <div className="text-center py-12">
            <AlertTriangle className="w-10 h-10 text-loss mx-auto mb-3" />
            <p className="text-loss-light">{analysisError}</p>
          </div>
        </div>
      )}

      {analysis && !analyzing && (
        <div className="space-y-4">
          {/* Header Card */}
          <div className="card">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-xl ${dir.bg} border ${dir.border}`}>
                  <dir.icon className={`w-8 h-8 ${dir.color}`} />
                </div>
                <div>
                  <div className="flex items-center gap-3">
                    <h2 className="text-2xl font-bold">{analysis.symbol}</h2>
                    <span className={`px-3 py-1 rounded-lg text-sm font-bold border ${dir.bg} ${dir.color} ${dir.border}`}>
                      {dir.label}
                    </span>
                    <span className="px-2 py-1 rounded text-xs bg-aurora-800/50 text-aurora-400 border border-aurora-700/30">
                      {analysis.timeframe?.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-aurora-400 text-sm mt-1">
                    {analysis.sector} &middot; {fmtUSD(analysis.price)}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-xs text-aurora-500 mb-1">Conviction</p>
                <div className="w-40">
                  <ConvictionBar score={analysis.conviction} />
                </div>
              </div>
            </div>
          </div>

          {/* Summary */}
          <div className="card">
            <div className="flex items-center gap-2 mb-3">
              <Brain className="w-5 h-5 text-aurora-500" />
              <h3 className="font-semibold">Executive Summary</h3>
            </div>
            <p className="text-aurora-300 leading-relaxed">{analysis.summary}</p>
          </div>

          {/* Grid: Technical + Risk */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Technical Outlook */}
            <div className="card">
              <div className="flex items-center gap-2 mb-3">
                <Target className="w-5 h-5 text-aurora-500" />
                <h3 className="font-semibold">Technical Outlook</h3>
              </div>
              <p className="text-aurora-300 text-sm leading-relaxed">
                {analysis.technical_outlook}
              </p>
            </div>

            {/* Volatility */}
            <div className="card">
              <div className="flex items-center gap-2 mb-3">
                <BarChart3 className="w-5 h-5 text-aurora-500" />
                <h3 className="font-semibold">Volatility Assessment</h3>
              </div>
              <p className="text-aurora-300 text-sm leading-relaxed">
                {analysis.volatility_assessment}
              </p>
            </div>
          </div>

          {/* Grid: Levels + Risk Factors */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Key Levels & Trade Plan */}
            <div className="card">
              <div className="flex items-center gap-2 mb-3">
                <Search className="w-5 h-5 text-aurora-500" />
                <h3 className="font-semibold">Trade Plan</h3>
              </div>
              <div className="space-y-1 divide-y divide-aurora-800/30">
                {analysis.entry_zone && (
                  <div className="flex items-center justify-between py-1.5">
                    <span className="text-aurora-400 text-sm">Entry Zone</span>
                    <span className="font-mono text-sm text-aurora-200">
                      {fmtUSD(analysis.entry_zone.low)} — {fmtUSD(analysis.entry_zone.high)}
                    </span>
                  </div>
                )}
                <KeyLevel label="Stop Loss" value={analysis.stop_loss} type="support" />
                <KeyLevel label="Target 1" value={analysis.take_profit_1} type="resistance" />
                {analysis.take_profit_2 && (
                  <KeyLevel label="Target 2" value={analysis.take_profit_2} type="resistance" />
                )}
                <div className="flex items-center justify-between py-1.5">
                  <span className="text-aurora-400 text-sm">Risk/Reward</span>
                  <span className="font-mono text-sm font-medium text-aurora-200">
                    1:{fmt(analysis.risk_reward_ratio, 1)}
                  </span>
                </div>
              </div>

              {/* Key Levels */}
              {analysis.key_levels && (
                <div className="mt-4 pt-4 border-t border-aurora-800/30">
                  <p className="text-xs text-aurora-500 uppercase tracking-wider mb-2">Key Levels</p>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <p className="text-xs text-profit mb-1">Support</p>
                      {(analysis.key_levels.support || []).map((lvl, i) => (
                        <p key={i} className="font-mono text-xs text-aurora-300">{fmtUSD(lvl)}</p>
                      ))}
                      {(!analysis.key_levels.support?.length) && (
                        <p className="text-xs text-aurora-600">None identified</p>
                      )}
                    </div>
                    <div>
                      <p className="text-xs text-loss-light mb-1">Resistance</p>
                      {(analysis.key_levels.resistance || []).map((lvl, i) => (
                        <p key={i} className="font-mono text-xs text-aurora-300">{fmtUSD(lvl)}</p>
                      ))}
                      {(!analysis.key_levels.resistance?.length) && (
                        <p className="text-xs text-aurora-600">None identified</p>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Risk Factors */}
            <div className="card">
              <div className="flex items-center gap-2 mb-3">
                <Shield className="w-5 h-5 text-aurora-500" />
                <h3 className="font-semibold">Risk Factors</h3>
              </div>
              {analysis.risk_factors?.length > 0 ? (
                <div className="space-y-2">
                  {analysis.risk_factors.map((risk, i) => (
                    <div key={i} className="flex items-start gap-2 p-2 bg-loss/5 rounded-lg border border-loss/10">
                      <AlertTriangle className="w-4 h-4 text-loss-light shrink-0 mt-0.5" />
                      <span className="text-sm text-aurora-300">{risk}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-aurora-400 text-sm">No significant risk factors identified.</p>
              )}

              {/* 52-Week Context */}
              {(analysis.high_52w > 0 || analysis.low_52w > 0) && (
                <div className="mt-4 pt-4 border-t border-aurora-800/30">
                  <p className="text-xs text-aurora-500 uppercase tracking-wider mb-2">52-Week Range</p>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs text-aurora-400">{fmtUSD(analysis.low_52w)}</span>
                    <div className="flex-1 h-2 bg-aurora-800 rounded-full overflow-hidden relative">
                      {analysis.price > 0 && analysis.high_52w > analysis.low_52w && (
                        <div
                          className="absolute h-full w-1 bg-aurora-400 rounded-full"
                          style={{
                            left: `${Math.min(100, Math.max(0, ((analysis.price - analysis.low_52w) / (analysis.high_52w - analysis.low_52w)) * 100))}%`,
                          }}
                        />
                      )}
                    </div>
                    <span className="font-mono text-xs text-aurora-400">{fmtUSD(analysis.high_52w)}</span>
                  </div>
                </div>
              )}

              {/* VIX */}
              {analysis.vix && (
                <div className="mt-4 pt-4 border-t border-aurora-800/30">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-aurora-500 uppercase tracking-wider">Volatility (VIX)</span>
                    <span className={`font-mono text-sm font-bold ${
                      analysis.vix < 15 ? "text-profit" :
                      analysis.vix < 25 ? "text-aurora-300" :
                      analysis.vix < 35 ? "text-circuit-yellow" :
                      "text-loss-light"
                    }`}>
                      {fmt(analysis.vix, 1)}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Timestamp */}
          {analysis.analyzed_at && (
            <p className="text-xs text-aurora-600 text-right">
              Analyzed at {new Date(analysis.analyzed_at).toLocaleString()}
            </p>
          )}
        </div>
      )}

      {/* Empty State */}
      {!analyzing && !analysis && !analysisError && (
        <div className="card">
          <div className="text-center py-16">
            <Brain className="w-16 h-16 text-aurora-600 mx-auto mb-4" />
            <p className="text-aurora-300 text-lg">Select a symbol to analyze</p>
            <p className="text-aurora-500 text-sm mt-1">
              Click any symbol above to get a deep AI-powered financial analysis
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
