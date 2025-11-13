"use client";

export default function AnalyzeForm({
  file,
  setFile,
  context,
  setContext,
  loading,
  handleSubmit,
}) {
  return (
    <form
      onSubmit={handleSubmit}
      className="bg-violet-900 p-6 rounded-2xl shadow-lg flex flex-col gap-4"
    >
      <input
        type="file"
        accept="video/*,image/*"
        onChange={(e) => setFile(e.target.files[0])}
        className="border rounded-md p-2"
      />
      <input
        type="text"
        placeholder="Enter context (e.g., classroom, road, etc.)"
        value={context}
        onChange={(e) => setContext(e.target.value)}
        className="border rounded-md p-2"
      />
      <button
        type="submit"
        disabled={loading}
        className="bg-black hover:bg-gray-900 text-white px-4 py-2 rounded-lg transition disabled:opacity-50"
      >
        {loading ? "Processing..." : "Analyze"}
      </button>
    </form>
  );
}
