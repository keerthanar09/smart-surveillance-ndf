"use client";

import { useState } from "react";

export default function InfoTooltip({ text, children }) {
  const [visible, setVisible] = useState(false);

  return (
    <div
      className="relative inline-block"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      {children}
      {visible && (
        <div className="absolute z-50 top-full left-1/2 -translate-x-1/2 mt-2 w-64 bg-gray-800 text-white text-sm p-3 rounded-lg shadow-lg border border-gray-700">
          {text}
        </div>
      )}
    </div>
  );
}
