import { ClipboardList } from "lucide-react";

export default function Audit() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Audit Trail</h1>
        <p className="text-aurora-400 text-sm mt-1">
          Complete decision chain tracking and system logs
        </p>
      </div>

      <div className="card">
        <div className="text-center py-16">
          <ClipboardList className="w-12 h-12 text-aurora-600 mx-auto mb-4" />
          <p className="text-aurora-400 text-lg">Audit log is empty</p>
          <p className="text-aurora-600 text-sm mt-1">
            Every decision, trade, and system event will be logged here
          </p>
        </div>
      </div>
    </div>
  );
}
