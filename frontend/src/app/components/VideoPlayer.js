export default function VideoPlayer({ videoRef, anomaly }) {
  return (
    <div className="w-1/2 bg-gray-900 rounded-md p-2 flex items-center justify-center">
      <div className="relative">
        <video ref={videoRef} controls className="max-h-48" />
        {anomaly.visible && (
          <div className="absolute top-0 right-0 bg-red-600 text-white px-2 py-1 rounded mt-2 mr-2 text-sm">ALERT</div>
        )}
      </div>
    </div>
  );
}
