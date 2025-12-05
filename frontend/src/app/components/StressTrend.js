"use client";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import InfoTooltip from "./InfoToolTip";

export default function StressTrend({ stressHistory }) {
  const data = stressHistory.map((v, i) => ({ index: i + 1, stress: v }));
  // console.log("StressTrend rendering", stressHistory);


  return (
    <InfoTooltip text="This graph shows the stress trend derived from detected emotions such as fear, sadness, and disgust. Peaks indicate higher stress levels in the analyzed video.">
      <div className="bg-gray-800 p-4 rounded-xl">
        <h3 className="text-lg font-semibold mb-2">Stress Trend</h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis dataKey="index" stroke="#aaa" />
            <YAxis stroke="#aaa" domain={[0, 100]} />
            <Tooltip
              contentStyle={{ backgroundColor: "#111", border: "1px solid #555" }}
              labelStyle={{ color: "#fff" }}
            />
            <Line type="monotone" dataKey="stress" stroke="#ffa500" strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </InfoTooltip>
  );
}
