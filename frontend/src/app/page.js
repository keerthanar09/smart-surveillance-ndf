"use client";

import { useState } from "react";
import Image from "next/image";

export default function Home() {
  const [file, setFile] = useState(null);
  const [context, setContext] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file || !context) {
      alert("Please upload a video and enter a context.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("context", context);

    setLoading(true);
    try {
      const res = await fetch("http://127.0.0.1:8000/process/", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setSummary(data.gemini || "");
      console.log("Summary:", summary);
      console.log("data:", data);
      setResult(data);
    } catch (err) {
      alert("Backend connection failed!");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-blue-900 p-8">
      <h1 className="text-3xl font-bold mb-6 text-white">
        Smart Surveillance Quick Run
      </h1>

      <form
        onSubmit={handleSubmit}
        className="bg-black p-6 rounded-2xl shadow-lg w-full max-w-md flex flex-col gap-4"
      >
        <input
          type="file"
          accept="video/*,image/*"
          onChange={(e) => setFile(e.target.files[0])}
          className="border border-gray-900 rounded-md p-2"
        />
        <input
          type="text"
          placeholder="Enter context (e.g., classroom, road, etc.)"
          value={context}
          onChange={(e) => setContext(e.target.value)}
          className="border border-gray-900 rounded-md p-2"
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition disabled:opacity-50"
        >
          {loading ? "Processing..." : "Analyze"}
        </button>
      </form>

      {result && (
        <div className="mt-8 bg-gray-900 text-blue-300 p-4 rounded-lg w-full max-w-3xl overflow-x-auto">
          <h2 className="text-xl mb-2 text-white">Analysis Result</h2>
          {result.graphs?.crowd_graph && (
            <Image
              src={`http://127.0.0.1:8000/${result.graphs.crowd_graph}`}
              alt="Crowd Graph"
              className="mt-4 rounded-md"
              width={600}
              height={400}
            />
            
          )}
          {result.graphs?.environment_graph && (
            <Image
              src={`http://127.0.0.1:8000/${result.graphs.environment_graph}`}
              alt="Environment Graph"
              className="mt-4 rounded-md"
              width={600}
              height={400}
            />
            
          )}
          {summary && (
            <div className="mt-4 p-4 bg-blue-800 rounded-md">
              <h3 className="text-lg font-semibold mb-2 text-white">Summary</h3>
              <p>{JSON.stringify(summary, null, 2)}</p>
            </div>
          )}
          <pre>{JSON.stringify(result, null, 2)}</pre>
          
        </div>
      )}
    </main>
  );
}
