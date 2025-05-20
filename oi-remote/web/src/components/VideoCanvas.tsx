import React from 'react';

interface VideoCanvasProps {
  streamUrl: string | null;
  showStream: boolean;
}

const VideoCanvas: React.FC<VideoCanvasProps> = ({ streamUrl, showStream }) => {
  if (!showStream || !streamUrl) {
    return null; // Don't render if stream is hidden or URL is not available
  }

  return (
    <div className="fixed bottom-4 right-4 w-64 h-auto bg-black border-2 border-sky-500 shadow-2xl rounded-lg overflow-hidden z-50 group">
      <img 
        src={streamUrl} 
        alt="Desktop Stream" 
        className="w-full h-full object-contain aspect-video"
        onError={(e) => {
          console.error("Stream error:", e);
          // Optionally display a placeholder or error message on the img itself or parent div
          // e.currentTarget.src = 'placeholder_error_image.png'; // If you have one
        }}
      />
      <div className="absolute top-0 right-0 bg-black bg-opacity-50 text-white text-xs px-2 py-1 group-hover:opacity-100 opacity-0 transition-opacity duration-200">
        Live View
      </div>
    </div>
  );
};

export default VideoCanvas;
