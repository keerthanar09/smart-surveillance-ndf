export default function EnvironmentPanel({ env }) {
  if (!env || Object.keys(env).length === 0)
    return <div className="text-white/60">No environment data</div>;

  const items = [
    { key: "weather", label: "Weather", hint: env.weather || "unknown" },
    { key: "lighting", label: "Lighting", hint: env.lighting || "unknown" },
    { key: "location", label: "Location", hint: env.location || "unknown" },
    { key: "cleanliness", label: "Cleanliness", hint: env.cleanliness || "unknown" },
  ];

  return (
    <div className="grid grid-cols-2 gap-3">
      {items.map((it) => (
        <div key={it.key} className="bg-gray-800 p-3 rounded-md flex items-center gap-3">
          <div className="w-12 h-12 bg-black/30 rounded flex items-center justify-center text-sm">
            {it.label[0]}
          </div>
          <div>
            <div className="text-white font-semibold">{it.label}</div>
            <div className="text-sm text-blue-200">{it.hint}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
