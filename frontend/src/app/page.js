
"use client";

import { useState, useRef, useEffect } from "react";
// import Image from "next/image";

export default function Home() {
  const [file, setFile] = useState(null);
  const [context, setContext] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState("");

  const [wellbeing, setWellbeing] = useState(100);
  const [stressHistory, setStressHistory] = useState([]);
  const [peopleHistory, setPeopleHistory] = useState([]);

  const videoRef = useRef(null);
  const controllerRef = useRef(null);
  const [anomaly, setAnomaly] = useState({ visible: false, reason: "" });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file || !context) {
      alert("Please upload a video and enter a context.");
      return;
    }
    const formData = new FormData();
    formData.append("file", file);
    formData.append("context", context);

    if (videoRef.current) {
      const url = URL.createObjectURL(file);
      videoRef.current.src = url;
      videoRef.current.play().catch(() => {});
    }

    setLoading(true);
    const controller = new AbortController();
    controllerRef.current = controller;

    try {
      const res = await fetch("http://127.0.0.1:8000/stream/", {
        method: "POST",
        body: formData,
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        throw new Error("Stream failed to start");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });

        const parts = buf.split("\n\n");
        buf = parts.pop();

        for (const part of parts) {
          const lines = part.split("\n").map((l) => l.trim());
          const dataLine = lines.find((l) => l.startsWith("data:"));
          if (!dataLine) continue;
          const json = dataLine.replace(/^data:\s*/, "");
          try {
            const parsed = JSON.parse(json);
            setResult(parsed);

            if (parsed.alert && parsed.reason) {
              speechSynthesis.speak(new SpeechSynthesisUtterance(parsed.reason));
            }

            if (parsed.alert) {
              const reason = parsed.reason || "Anomaly detected";
              setAnomaly({ visible: true, reason });
              setTimeout(() => setAnomaly({ visible: false, reason: "" }), 8000);
            }
          } catch (e) {
            console.error("Failed to parse SSE JSON", e);
          }
        }
      }
    } catch (err) {
      if (err && (err.name === "AbortError" || err.message?.toLowerCase().includes("abort"))) {
        console.log("Stream aborted by client");
      } else {
        alert("Backend connection failed!");
        console.error(err);
      }
    } finally {
      setLoading(false);
      controllerRef.current = null;
    }
  };

  // update graphs and wellbeing on each result
  useEffect(() => {
    if (!result) return;

    // emotion distribution (backend uses lowercase keys)
    const emoDist = result?.results?.emotion?.emotion_distribution || {};
    const fear = Number(emoDist.fear ?? emoDist.Fear ?? 0) || 0;
    const sad = Number(emoDist.sad ?? emoDist.Sad ?? 0) || 0;
    const disgust = Number(emoDist.disgust ?? emoDist.Disgust ?? 0) || 0;

    const stress = Math.min(100, fear * 0.6 + sad * 0.3 + disgust * 0.1);
    setStressHistory((prev) => [...prev.slice(-19), stress]);

    // people count
    const crowd = result?.results?.crowd || {};
    let avgPeople = 0;
    if (typeof crowd?.overall_crowd_count === "number") {
      avgPeople = crowd.overall_crowd_count;
    } else {
      const aggList = crowd?.aggregated_outputs ?? [];
      if (aggList.length > 0) {
        const aggregate = aggList[0].aggregate ?? {};
        let total = 0;
        for (const k in aggregate) {
          total += aggregate[k].avg_people || 0;
        }
        avgPeople = total;
      }
    }
    setPeopleHistory((prev) => [...prev.slice(-19), avgPeople]);

    // compute wellbeing using anomaly_meta if present (prefer authoritative wellness_score)
    const anomaly_meta = result?.anomaly_meta;
    if (anomaly_meta && typeof anomaly_meta.wellness_score === "number") {
      // scale 0..1 -> 0..100
      setWellbeing(Math.round(anomaly_meta.wellness_score * 100));
    } else {
      // fallback composite
      const emoScore = Math.max(0, 100 - stress * 0.8);
      const crowdScore = Math.max(0, 100 - Math.min(avgPeople * 1.5, 100));
      const post = result?.results?.posture?.frame_results || [];
      let postureScore = 80;
      if (post.length > 0) {
        const negatives = post.filter(p => ["crouching","bent_forward"].includes(p.posture) || ["aggressive","defensive"].includes(p.body_language));
        postureScore = Math.max(20, 100 - negatives.length * 12);
      }
      const env = result?.results?.environment || {};
      let envScore = 75;
      if (env.lighting === "bright" && env.cleanliness === "clean") envScore = 90;
      else if (env.lighting === "night" || env.cleanliness === "messy") envScore = 55;
      const score = Math.max(0, Math.min(100, (emoScore * 0.4 + crowdScore * 0.3 + postureScore * 0.2 + envScore * 0.1)));
      setWellbeing(Math.round(score));
    }
  }, [result]);

  // video end cleanup
  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    const onEnded = () => {
      if (controllerRef.current) controllerRef.current.abort();
      setLoading(false);
    };
    v.addEventListener("ended", onEnded);
    return () => v.removeEventListener("ended", onEnded);
  }, []);

  // small SVG render helpers
  const renderStressSVG = () => {
    const arr = stressHistory;
    const w = 300, h = 60;
    if (!arr.length) return <svg width={w} height={h} />;
    const step = Math.max(1, Math.floor(w / Math.max(1, arr.length)));
    return (
      <svg width={w} height={h}>
        {arr.map((v, i) => {
          const cx = i * step + 6;
          const cy = h - Math.min(h - 6, (v / 100) * (h - 12));
          return <circle key={i} cx={cx} cy={cy} r="3" fill="orange" />;
        })}
      </svg>
    );
  };

  const renderPeopleSVG = () => {
    const arr = peopleHistory;
    const w = 300, h = 60;
    if (!arr.length) return <svg width={w} height={h} />;
    const maxP = Math.max(10, ...arr, 1);
    const step = Math.max(1, Math.floor(w / Math.max(1, arr.length)));
    return (
      <svg width={w} height={h}>
        {arr.map((v, i) => {
          const cx = i * step + 6;
          const cy = h - Math.min(h - 6, (v / maxP) * (h - 12));
          return <circle key={i} cx={cx} cy={cy} r="3" fill="cyan" />;
        })}
      </svg>
    );
  };

  // Environment interactive cards
  const EnvironmentPanel = ({ env }) => {
    if (!env || Object.keys(env).length === 0) {
      return <div className="text-white/60">No environment data</div>;
    }
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
  };

  const CrowdBadges = ({ crowd }) => {
    if (!crowd) return null;
    const badges = [];
    if (crowd.combined_anomaly) badges.push({ text: "Density / Motion Anomaly", color: "orange" });
    if (crowd.motion_anomaly?.is_running) badges.push({ text: "Running Detected", color: "red" });
    if (crowd.density_shift_anomaly?.is_anomaly) badges.push({ text: "Sudden Density Shift", color: "red" });
    if (crowd.dominant_state && ["chaotic", "extreme", "panic"].includes(crowd.dominant_state)) {
      badges.push({ text: `State: ${crowd.dominant_state}`, color: "red" });
    }
    if (badges.length === 0) return null;
    return (
      <div className="flex gap-2 mt-3">
        {badges.map((b, i) => (
          <div key={i} className={`px-2 py-1 rounded text-white`} style={{ backgroundColor: b.color }}>
            {b.text}
          </div>
        ))}
      </div>
    );
  };

  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-black p-8">
      <h1 className="text-3xl font-bold mb-6 text-white">Smart Surveillance Quick Run</h1>

      <form onSubmit={handleSubmit} className="bg-violet-900 p-6 rounded-2xl shadow-lg w-full max-w-4xl flex gap-6">
        <div className="flex-1 flex flex-col gap-3">
          <input type="file" accept="video/*,image/*" onChange={(e) => setFile(e.target.files[0])} className="border rounded-md p-2" />
          <input type="text" placeholder="Enter context (e.g., classroom, road, etc.)" value={context} onChange={(e) => setContext(e.target.value)} className="border rounded-md p-2" />
          <button type="submit" disabled={loading} className="bg-black hover:bg-gray-900 text-white px-4 py-2 rounded-lg transition disabled:opacity-50">
            {loading ? "Processing..." : "Analyze"}
          </button>
        </div>

        <div className="w-1/2 bg-gray-900 rounded-md p-2 flex items-center justify-center">
          <div className="relative">
            <video ref={videoRef} controls className="max-h-48" />
            {anomaly.visible && <div className="absolute top-0 right-0 bg-red-600 text-white px-2 py-1 rounded mt-2 mr-2 text-sm">ALERT</div>}
          </div>
        </div>
      </form>

      {result && (
        <div className="mt-8 bg-gray-900 text-blue-300 p-4 rounded-lg w-full max-w-screen overflow-x-auto">
          <h2 className="text-xl mb-2 text-white">Real-time Analysis</h2>
          <div className="flex gap-6">
            <div className="w-1/2">
              <h3 className="text-white font-semibold">Live Results</h3>
              <pre className="text-sm text-blue-100 bg-black/30 p-2 rounded mt-2 max-h-96 overflow-auto">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>

            <div className="w-1/2">
              <h3 className="text-white font-semibold">Visualizations</h3>

              <div className="mt-6 bg-gray-800 p-4 rounded-xl">
                <div className="flex justify-between items-center">
                  <h3 className="text-lg text-white font-semibold">Public Wellbeing Meter</h3>
                  <div className="text-sm text-blue-200">Wellness Score: {wellbeing}</div>
                </div>

                <div className="w-full bg-red-900/30 h-4 rounded-full mt-2">
                  <div className="h-4 rounded-full" style={{ width: `${wellbeing}%`, backgroundColor: wellbeing > 70 ? "green" : wellbeing > 40 ? "yellow" : "red" }}></div>
                </div>

                <CrowdBadges crowd={result?.results?.crowd} />

                <div className="mt-4">
                  <div className="text-white font-semibold mb-2">Environment Details</div>
                  <EnvironmentPanel env={result?.results?.environment} />
                </div>
              </div>

              <div className="mt-6 bg-gray-800 p-4 rounded-xl">
                <h3 className="text-lg text-white font-semibold mb-2">Real-Time Trends</h3>

                <p className="text-white text-sm mb-1">Stress Trend</p>
                {renderStressSVG()}

                <p className="text-white text-sm mt-4 mb-1">People Count Trend</p>
                {renderPeopleSVG()}
              </div>

              {anomaly.visible && (
                <div className="fixed bottom-6 right-6 bg-red-700 text-white p-3 rounded shadow-lg max-w-sm">
                  <div className="flex justify-between items-start gap-4">
                    <div>
                      <div className="font-bold">Anomaly detected</div>
                      <div className="text-sm mt-1">{anomaly.reason}</div>
                    </div>
                    <button onClick={() => setAnomaly({ visible: false, reason: "" })} className="ml-2 text-white/80">Dismiss</button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
