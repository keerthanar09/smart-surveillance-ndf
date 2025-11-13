export default function CrowdBadges({ crowd }) {
  if (!crowd) return null;
  const badges = [];

  if (crowd.combined_anomaly) badges.push({ text: "Density / Motion Anomaly", color: "orange" });
  if (crowd.motion_anomaly?.is_running) badges.push({ text: "Running Detected", color: "red" });
  if (crowd.density_shift_anomaly?.is_anomaly) badges.push({ text: "Sudden Density Shift", color: "red" });
  if (["chaotic", "extreme", "panic"].includes(crowd.dominant_state))
    badges.push({ text: `State: ${crowd.dominant_state}`, color: "red" });

  if (badges.length === 0) return null;
  return (
    <div className="flex gap-2 mt-3">
      {badges.map((b, i) => (
        <div key={i} className="px-2 py-1 rounded text-white" style={{ backgroundColor: b.color }}>
          {b.text}
        </div>
      ))}
    </div>
  );
}
