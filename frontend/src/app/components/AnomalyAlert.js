export default function AnomalyAlert({ anomaly, setAnomaly }) {
  if (!anomaly.visible) return null;
  return (
    <div className="fixed bottom-6 right-6 bg-red-700 text-white p-3 rounded shadow-lg max-w-sm">
      <div className="flex justify-between items-start gap-4">
        <div>
          <div className="font-bold">Anomaly detected</div>
          <div className="text-sm mt-1">{anomaly.reason}</div>
        </div>
        <button onClick={() => setAnomaly({ visible: false, reason: "" })} className="ml-2 text-white/80">
          Dismiss
        </button>
      </div>
    </div>
  );
}
