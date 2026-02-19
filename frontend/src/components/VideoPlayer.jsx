import { useEffect, useRef, useState } from 'react';
import { useCameraStore } from '../store/cameraStore';
import { Zap, Activity } from 'lucide-react';

export default function VideoPlayer({ zoom = 0 }) {
  const { sessionId, currentFrame, setFrame } = useCameraStore();
  const canvasRef = useRef(null);
  const wsRef = useRef(null);
  const [detectionEnabled, setDetectionEnabled] = useState(false);
  const [confidence, setConfidence] = useState(0.5);
  const [frameRate, setFrameRate] = useState(0);
  const [lastDetectionCount, setLastDetectionCount] = useState(0);
  const frameCountRef = useRef(0);
  const lastTimeRef = useRef(Date.now());
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!sessionId) return;

    const ws = new WebSocket(`ws://localhost:8000/ws/video/${sessionId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.frame) {
          setFrame(data.frame);
          
          // Track detection count
          if (data.detections && Array.isArray(data.detections)) {
            setLastDetectionCount(data.detections.length);
          }
          
          // Calculate FPS
          frameCountRef.current++;
          const now = Date.now();
          if (now - lastTimeRef.current >= 1000) {
            setFrameRate(frameCountRef.current);
            frameCountRef.current = 0;
            lastTimeRef.current = now;
          }
        }
      } catch (err) {
        console.error('Failed to parse message:', err);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [sessionId]);

  const toggleDetection = () => {
    const newState = !detectionEnabled;
    setDetectionEnabled(newState);
    setLastDetectionCount(0);
    
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'toggle_detection',
        enabled: newState,
        confidence: confidence
      }));
    }
  };

  const updateConfidence = (newConfidence) => {
    setConfidence(newConfidence);
    
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'toggle_detection',
        enabled: detectionEnabled,
        confidence: newConfidence
      }));
    }
  };

  useEffect(() => {
    if (!currentFrame || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const img = new Image();

    img.onload = () => {
      if (canvas.width !== img.width || canvas.height !== img.height) {
        canvas.width = img.width;
        canvas.height = img.height;
      }
      
      // Clear canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      // Apply zoom by scaling the canvas
      const zoomFactor = 1 + (zoom * 0.1); // Each zoom level adds 10%
      
      // Save the context state
      ctx.save();
      
      // Center the zoom
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      ctx.translate(centerX, centerY);
      ctx.scale(zoomFactor, zoomFactor);
      ctx.translate(-centerX, -centerY);
      
      // Draw the image
      ctx.drawImage(img, 0, 0);
      
      // Restore the context state
      ctx.restore();
    };

    img.onerror = () => {
      console.error('Failed to load image');
    };

    img.src = `data:image/jpeg;base64,${currentFrame}`;
  }, [currentFrame, zoom]);

  const getStreamQuality = () => {
    if (frameRate >= 30) return { color: 'text-green-400', status: 'Excellent' };
    if (frameRate >= 20) return { color: 'text-yellow-400', status: 'Good' };
    return { color: 'text-red-400', status: 'Poor' };
  };

  const quality = getStreamQuality();

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
        <>
          <canvas ref={canvasRef} className="w-full h-full object-contain" />
          
          {/* Connection Status */}
          <div className="absolute top-4 left-4 flex items-center gap-2">
            <div
              className={`w-3 h-3 rounded-full ${
                isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
              }`}
            />
            <span className="text-sm text-gray-300">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>

          {/* Detection Controls Panel */}
          <div className="absolute top-4 right-4 flex flex-col gap-3 bg-black/80 p-4 rounded-lg border border-white/10 backdrop-blur-sm max-w-xs">
            {/* Detection Toggle Button */}
            <button
              onClick={toggleDetection}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold transition-all duration-200 ${
                detectionEnabled
                  ? 'bg-green-600 text-white hover:bg-green-700 shadow-lg shadow-green-500/30'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              <Zap size={16} />
              {detectionEnabled ? 'Detection ON' : 'Detection OFF'}
            </button>

            {/* Confidence Slider */}
            {detectionEnabled && (
              <div className="flex items-center gap-2 pt-2 border-t border-white/10">
                <label className="text-xs text-gray-400 whitespace-nowrap">
                  Confidence:
                </label>
                <input
                  type="range"
                  min="0.1"
                  max="0.99"
                  step="0.05"
                  value={confidence}
                  onChange={(e) => updateConfidence(parseFloat(e.target.value))}
                  className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                />
                <span className="text-xs text-white font-mono w-10 text-right">
                  {(confidence * 100).toFixed(0)}%
                </span>
              </div>
            )}

            {/* Divider */}
            <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

            {/* Performance Stats */}
            <div className="space-y-2 text-xs">
              {/* Stream FPS */}
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Stream FPS:</span>
                <span className={`font-mono font-semibold ${quality.color}`}>
                  {frameRate} fps
                </span>
              </div>

              {/* Quality Indicator */}
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Quality:</span>
                <span className={`font-mono font-semibold ${quality.color}`}>
                  {quality.status}
                </span>
              </div>

              {/* Detection Status */}
              {detectionEnabled && (
                <>
                  <div className="h-px bg-white/5" />
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1">
                      <Activity size={12} className="text-blue-400" />
                      <span className="text-gray-400">Detection:</span>
                    </div>
                    <span className="font-mono text-blue-400 animate-pulse">Active</span>
                  </div>

                  {/* Objects Detected */}
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">Objects Found:</span>
                    <span className="font-mono text-cyan-400 font-semibold">
                      {lastDetectionCount}
                    </span>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Detection Activity Indicator */}
          {detectionEnabled && (
            <div className="absolute bottom-4 right-4 flex items-center gap-2 text-xs">
              <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
              <span className="text-blue-400">Live Detection</span>
            </div>
          )}
        </>
      )}
    </div>
  );
}