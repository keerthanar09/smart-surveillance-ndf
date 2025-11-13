"use client";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import InfoTooltip from "./InfoToolTip";

export default function PeopleTrend({ peopleHistory }) {
  const data = peopleHistory.map((v, i) => ({ index: i + 1, people: v }));

  return (
    <InfoTooltip text="Tracks how the number of people changes over time. Spikes can indicate sudden crowding or unusual gatherings.">
      <div className="bg-gray-800 p-4 rounded-xl">
        <h3 className="text-lg font-semibold mb-2">People Count Trend</h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis dataKey="index" stroke="#aaa" />
            <YAxis stroke="#aaa" />
            <Tooltip
              contentStyle={{ backgroundColor: "#111", border: "1px solid #555" }}
              labelStyle={{ color: "#fff" }}
            />
            <Line type="monotone" dataKey="people" stroke="#00ffff" strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </InfoTooltip>
  );
}
