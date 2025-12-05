"use client";

import { useState, useRef, useEffect } from "react";
import AnalyzeForm from "./components/AnalyzeForm";
import VideoPlayer from "./components/VideoPlayer";
import WellbeingMeter from "./components/WellbeingMeter";
import StressTrend from "./components/StressTrend";
import PeopleTrend from "./components/PeopleTrend";
import AnomalyAlert from "./components/AnomalyAlert";

export default function Home() {
  const [file, setFile] = useState(null);
  const [context, setContext] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [wellbeing, setWellbeing] = useState(100);
  const [stressHistory, setStressHistory] = useState([]);
  const [peopleHistory, setPeopleHistory] = useState([]);
  const [anomaly, setAnomaly] = useState({ visible: false, reason: "" });

  const videoRef = useRef(null);
  const controllerRef = useRef(null);

  const lastPeopleRef = useRef(0);

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

      if (!res.ok || !res.body) throw new Error("Stream failed to start");

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

          try {
            const parsed = JSON.parse(dataLine.replace(/^data:\s*/, ""));
            setResult(parsed);

            if (parsed.alert) {
              const reason = parsed.reason || "Anomaly detected";
              setAnomaly({ visible: true, reason });
              speechSynthesis.speak(new SpeechSynthesisUtterance(reason));
              setTimeout(() => setAnomaly({ visible: false, reason: "" }), 8000);
              console.log("Anomaly detected:", reason);
            }
          } catch (err) {
            console.error("Failed to parse stream JSON:", err);
          }
        }
      }
    } catch (err) {
      if (err.name === "AbortError") console.log("Stream aborted");
      else console.error("Stream error:", err);
      alert("Backend connection failed!");
    } finally {
      setLoading(false);
      controllerRef.current = null;
    }
  };

  useEffect(() => {
    if (!result) return;

    const emoDist = result?.results?.emotion?.emotion_distribution || {};
    const fear = Number(emoDist.fear ?? 0);
    const sad = Number(emoDist.sad ?? 0);
    const disgust = Number(emoDist.disgust ?? 0);
    const anger = Number(emoDist.anger ?? 0);

    const hasNegativeEmotions =
      fear > 0 || sad > 0 || disgust > 0 || anger > 0;

    let stress = 0;
    const crowd = result?.results?.crowd || {};

    if (hasNegativeEmotions) {
      stress = Math.min(
        100,
        anger * 0.4 + fear * 0.3 + sad * 0.2 + disgust * 0.1
      );
    } else{
      const panic = crowd.panic_detected ? 1 : 0;
      const anomalyFlag = result?.alert ? 1 : 0;

      const suddenChange =
        Math.abs(
          (crowd.overall_crowd_count ?? 0) - lastPeopleRef.current
        ) > 10
          ? 1
          : 0;

      stress = Math.min(100, panic * 70 + suddenChange * 40 + anomalyFlag * 80);
    }

    console.log("Calculated stress:", stress);
    setStressHistory((prev) => [...prev.slice(-19), stress]);

    const avgPeople = Math.floor(crowd.overall_crowd_count ?? 0);

    setPeopleHistory((prev) => {
      const newHist = [...prev.slice(-19), avgPeople];
      return newHist;
    });
    lastPeopleRef.current = avgPeople;
    const anomaly_meta = result?.anomaly_meta;
    if (anomaly_meta?.wellness_score !== undefined)
      setWellbeing(Math.round(anomaly_meta.wellness_score * 100));
  }, [result]);

  return (
    <main className="min-h-screen bg-black text-white p-8 flex justify-center">
      <div className="max-w-7xl w-full grid grid-cols-2 gap-8">
        <div className="flex flex-col gap-6">
          <h1 className="text-3xl font-bold mb-2 text-white">
            Smart Surveillance System Demo
          </h1>
          <AnalyzeForm
            file={file}
            setFile={setFile}
            context={context}
            setContext={setContext}
            loading={loading}
            handleSubmit={handleSubmit}
          />
          <VideoPlayer videoRef={videoRef} anomaly={anomaly} />
        </div>

        {result && (
          <div className="flex flex-col gap-6">
            <WellbeingMeter
              wellbeing={wellbeing}
              crowd={result?.results?.crowd}
              env={result?.results?.environment}
            />
            <StressTrend stressHistory={stressHistory} />
            <PeopleTrend peopleHistory={peopleHistory} />
          </div>
        )}
      </div>

      <AnomalyAlert anomaly={anomaly} setAnomaly={setAnomaly} />
    </main>
  );
}
