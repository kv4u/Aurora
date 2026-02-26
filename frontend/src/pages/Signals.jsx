import { Signal } from "lucide-react";

export default function Signals() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Signals</h1>
        <p className="text-aurora-400 text-sm mt-1">
          ML-generated signals and confidence analysis
        </p>
      </div>

      <div className="card">
        <div className="text-center py-16">
          <Signal className="w-12 h-12 text-aurora-600 mx-auto mb-4" />
          <p className="text-aurora-400 text-lg">No signals generated</p>
          <p className="text-aurora-600 text-sm mt-1">
            The signal engine will generate BUY/SELL/HOLD signals during market
            hours
          </p>
        </div>
      </div>
    </div>
  );
}
