import { useEffect, useRef, useState } from 'react';
import { useCameraStore } from '../store/cameraStore';
import { Zap, Activity } from 'lucide-react';

export default function VideoPlayer({ zoom = 0 }) {
  const { sessionId, currentFrame, setFrame } = useCameraStore();
  const canvasRef = useRef(null);
  const wsRef = useRef(null);
  const [detectionEnabled, setDetectionEnabled] = useState(true);  // Enable detection by default
  const [confidence, setConfidence] = useState(0.5);
  const [frameRate, setFrameRate] = useState(0);
  const [lastDetectionCount, setLastDetectionCount] = useState(0);
  const [detectionData, setDetectionData] = useState([]);
  const frameCountRef = useRef(0);
  const lastTimeRef = useRef(Date.now());
  const [isConnected, setIsConnected] = useState(false);
  const [streamStarted, setStreamStarted] = useState(false);
  const reconnectAttemptsRef = useRef(0);
  const MAX_RECONNECT_ATTEMPTS = 5;

  useEffect(() => {
    if (!sessionId) return;

    const connectWebSocket = () => {
      const ws = new WebSocket(`ws://localhost:8000/ws/video/${sessionId}`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        reconnectAttemptsRef.current = 0; // Reset reconnect counter
        
        // Send initial detection state (enabled by default)
        ws.send(
          JSON.stringify({
            type: 'toggle_detection',
            enabled: true,
            confidence: 0.5,
          })
        );
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Handle stream ready message
          if (data.type === 'stream_ready') {
            console.log('Stream ready:', data);
            setStreamStarted(true);
            return;
          }

          // Handle frame data
          if (data.frame) {
            setFrame(data.frame);

            // Track detection count
            if (data.detections || data.cached_detections) {
              setLastDetectionCount(data.detections || data.cached_detections);
            }

            // Store detection data for rendering bounding boxes
            if (data.detection_data && data.detection_data.length > 0) {
              setDetectionData(data.detection_data);
            } else if (
              data.cached_detection_data &&
              data.cached_detection_data.length > 0
            ) {
              setDetectionData(data.cached_detection_data);
            } else {
              setDetectionData([]);
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
        console.log('WebSocket closed');
        setIsConnected(false);
        setStreamStarted(false);

        // Attempt to reconnect
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current++;
          console.log(
            `Reconnecting... (attempt ${reconnectAttemptsRef.current})`
          );
          setTimeout(connectWebSocket, 2000 * reconnectAttemptsRef.current);
        }
      };
    };

    connectWebSocket();

    return () => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
    };
  }, [sessionId, setFrame]);

  const toggleDetection = () => {
    const newState = !detectionEnabled;
    setDetectionEnabled(newState);
    setLastDetectionCount(0);
    if (!newState) {
      setDetectionData([]); // Clear detection data when disabled
    }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'toggle_detection',
          enabled: newState,
          confidence: confidence,
        })
      );
    }
  };

  const updateConfidence = (newConfidence) => {
    setConfidence(newConfidence);

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'toggle_detection',
          enabled: detectionEnabled,
          confidence: newConfidence,
        })
      );
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

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const zoomFactor = 1 + zoom * 0.1;
      ctx.save();
      ctx.translate(canvas.width / 2, canvas.height / 2);
      ctx.scale(zoomFactor, zoomFactor);
      ctx.translate(-canvas.width / 2, -canvas.height / 2);

      // Draw the image
      ctx.drawImage(img, 0, 0);

      // Draw bounding boxes if detection is enabled and we have detection data
      if (detectionEnabled && detectionData && detectionData.length > 0) {
        detectionData.forEach((detection) => {
          const bbox = detection.bbox;
          if (!bbox) return;

          const x1 = bbox.x1;
          const y1 = bbox.y1;
          const x2 = bbox.x2;
          const y2 = bbox.y2;
          const width = x2 - x1;
          const height = y2 - y1;

          // Draw bounding box rectangle
          ctx.strokeStyle = '#4b8f2c';
          ctx.lineWidth = 2 / zoomFactor; // Adjust line width for zoom
          ctx.strokeRect(x1, y1, width, height);

          // Smaller font size
          const fontSize = 12 / zoomFactor;
          ctx.font = `bold ${fontSize}px Arial`;

          // Create label text
          const label = `${detection.class_name} ${(detection.confidence * 100).toFixed(0)}%`;

          // Measure text properly
          const textMetrics = ctx.measureText(label);
          const textWidth = textMetrics.width;
          const textHeight =
            textMetrics.actualBoundingBoxAscent +
            textMetrics.actualBoundingBoxDescent;

          // Padding around text
          const paddingX = 6 / zoomFactor;
          const paddingY = 4 / zoomFactor;

          // Draw label background exactly wrapping text
          ctx.fillStyle = 'rgba(0, 255, 0, 0.85)';
          ctx.fillRect(
            x1,
            y1 - textHeight - paddingY * 2,
            textWidth + paddingX * 2,
            textHeight + paddingY * 2
          );

          // Draw text
          ctx.fillStyle = '#000000';
          ctx.fillText(label, x1 + paddingX, y1 - paddingY);
        });
      }

      ctx.restore();
    };

    img.src = `data:image/jpeg;base64,${currentFrame}`;
  }, [currentFrame, zoom, detectionEnabled, detectionData]);

  const getStreamQuality = () => {
    if (frameRate >= 30)
      return { color: 'text-green-400', status: 'Excellent' };
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
              {isConnected
                ? streamStarted
                  ? 'Live Stream'
                  : 'Connecting...'
                : 'Disconnected'}
            </span>
          </div>

          {/* Detection Controls */}
          <div className="absolute top-4 right-4 flex flex-col gap-3 bg-black/80 p-4 rounded-lg border border-white/10 backdrop-blur-sm max-w-xs">
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

            <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Stream FPS:</span>
                <span className={`font-mono font-semibold ${quality.color}`}>
                  {frameRate} fps
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-gray-400">Quality:</span>
                <span className={`font-mono font-semibold ${quality.color}`}>
                  {quality.status}
                </span>
              </div>

              {detectionEnabled && (
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Detections:</span>
                  <span className="font-mono font-semibold text-blue-400">
                    {lastDetectionCount}
                  </span>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
