import { ArrowLeftRight } from "lucide-react";

export default function Trades() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Trades</h1>
        <p className="text-aurora-400 text-sm mt-1">
          Full trade history with P&L and reasoning
        </p>
      </div>

      <div className="card">
        <div className="text-center py-16">
          <ArrowLeftRight className="w-12 h-12 text-aurora-600 mx-auto mb-4" />
          <p className="text-aurora-400 text-lg">No trades yet</p>
          <p className="text-aurora-600 text-sm mt-1">
            Trade history will appear here once the system starts trading
          </p>
        </div>
      </div>
    </div>
  );
}
