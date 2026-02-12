import { useEffect, useRef } from 'react';
import { useCameraStore } from '../store/cameraStore';
// import { io } from 'socket.io-client';

export default function VideoPlayer() {
  const { sessionId, currentFrame, setFrame } = useCameraStore();
  const canvasRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    if (!sessionId) return;

    const ws = new WebSocket(`ws://localhost:8000/ws/video/${sessionId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.frame) {
        setFrame(data.frame);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [sessionId]);

  useEffect(() => {
    if (!currentFrame || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const img = new Image();

    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);
    };

    img.src = `data:image/jpeg;base64,${currentFrame}`;
  }, [currentFrame]);

  return (
    <div className="relative w-full h-full bg-black rounded-lg overflow-hidden border-2 border-primary">
      {!sessionId ? (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <h3 className="text-2xl font-bold mb-2">No Camera Connected</h3>
            <p className="text-gray-400">Enter camera URL and click Connect</p>
          </div>
        </div>
      ) : (
        <canvas ref={canvasRef} className="w-full h-full object-contain" />
      )}
    </div>
  );
}