import { useState, useEffect } from 'react';
import { useCameraStore } from '../store/cameraStore';
import { cameraAPI } from '../services/api';
import toast from 'react-hot-toast';
import { Wifi, WifiOff, AlertCircle, ChevronDown } from 'lucide-react';
import { Loader } from 'lucide-react';

const STREAM_TYPES = [
  {
    id: 'usb',
    label: 'USB Camera',
    description: 'Local USB webcam or camera device',
    placeholder: 'e.g., 0, 1, 2 (device index)',
    example: '0',
    help: 'Enter your device index. Usually webcams start at 0.'
  },
  {
    id: 'rtsp',
    label: 'RTSP Stream',
    description: 'RTSP network stream (IP cameras, streaming servers)',
    placeholder: 'e.g., 192.168.1.100 (will try default port 554)',
    example: 'rtsp://192.168.1.100:554/stream',
    help: `Enter IP address only (e.g., 192.168.1.100). The system will:
1. AutoAddresses default RTSP port 554
2. Try common stream paths: /stream, /main, /ch0, /preview, /live

Or enter complete RTSP URL with protocol and path for manual control.

Check your camera documentation for the exact stream path (e.g., /main, /h264, etc.).`
  },
  {
    id: 'ip',
    label: 'IP Camera',
    description: 'IP-based camera with HTTP/HTTPS',
    placeholder: 'e.g., 192.168.1.100 or camera.local',
    example: '192.168.1.100',
    help: 'IP address or hostname of your HTTP/HTTPS camera.'
  },
  {
    id: 'raw',
    label: 'Raw Stream',
    description: 'Direct network stream URL',
    placeholder: 'e.g., http://ip:port/stream',
    example: 'http://192.168.1.100:8080/stream',
    help: 'Direct URL for custom network streams. Must include full protocol and path.'
  }
];

export default function ConnectionBar() {
  const [url, setUrl] = useState('');
  const [streamType, setStreamType] = useState('usb');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const { sessionId, connected, setSession, disconnect } = useCameraStore();
  const [loading, setLoading] = useState(false);
  const [connectionTime, setConnectionTime] = useState(0);
  const [error, setError] = useState(null);

  useEffect(() => {
    let interval;
    if (loading) {
      const startTime = Date.now();
      interval = setInterval(() => {
        setConnectionTime(Math.floor((Date.now() - startTime) / 1000));
      }, 100);
    } else {
      setConnectionTime(0);
    }
    return () => clearInterval(interval);
  }, [loading]);

  const currentStreamType = STREAM_TYPES.find(t => t.id === streamType);

  const handleConnect = async () => {
    if (connected) {
      // Disconnect request
      setLoading(true);
      try {
        await cameraAPI.disconnect({ session_id: sessionId });
        disconnect();
        toast.success('Camera disconnected');
      } catch (error) {
        console.error('Disconnect error:', error);
        toast.error('Failed to disconnect camera');
        disconnect(); // Force disconnect on frontend even if API fails
      } finally {
        setLoading(false);
      }
      return;
    }

    const inputUrl = url.trim();
    if (!inputUrl) {
      toast.error(`Please enter a ${currentStreamType.label.toLowerCase()} URL or index`);
      setError(`${currentStreamType.label} URL is required`);
      return;
    }

    setLoading(true);
    setError(null);
    const startTime = Date.now();
    
    try {
      console.log(`Connecting to camera with ${streamType} stream:`, inputUrl);
      
      const response = await cameraAPI.connect({
        url: inputUrl,
        camera_id: 1,
        stream_type: streamType
      });

      const duration = Math.floor((Date.now() - startTime) / 1000);
      console.log('Full response object:', response);
      console.log('Response.data:', response.data);
      console.log('Session ID from response:', response.data?.session_id);
      
      if (!response.data?.session_id) {
        throw new Error('No session_id in response');
      }
      
      setSession(response.data.session_id);
      console.log('Session set to:', response.data.session_id);
      toast.success(`${currentStreamType.label} connected in ${duration}s!`);
      setUrl('');
      
    } catch (error) {
      const duration = Math.floor((Date.now() - startTime) / 1000);
      
      console.error('Connection error full object:', error);
      console.error('Error response:', error.response);
      console.error('Error request:', error.request);
      console.error('Error message:', error.message);
      console.error('Error status:', error.response?.status);
      console.error('Error data:', error.response?.data);
      
      let errorMessage = `Failed to connect to ${currentStreamType.label.toLowerCase()}`;
      
      if (error.response?.status === 400) {
        const detail = error.response.data?.detail;
        errorMessage = detail || `Invalid ${streamType} URL or stream not found`;
      } else if (error.response?.status === 401) {
        errorMessage = 'Authentication required. Please login again.';
      } else if (error.response?.status === 500) {
        errorMessage = 'Server error. Please try again later.';
      } else if (error.message === 'Network Error') {
        errorMessage = 'Cannot reach server. Is backend running?';
      } else if (duration > 30) {
        errorMessage = `${currentStreamType.label} not responding. Check the address or network connection.`;
      }
      
      setError(errorMessage);
      toast.error(`${errorMessage} (${duration}s)`);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !loading) {
      handleConnect();
    }
  };

  return (
    <div className="space-y-3">
      {/* Stream Type Selector and Connection Controls */}
      <div className="bg-secondary p-4 rounded-lg space-y-3">
        {/* Stream Type Dropdown */}
        <div className="relative">
          <label className="block text-xs font-semibold text-gray-400 mb-2">
            Stream Type
          </label>
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            disabled={connected || loading}
            className="
              w-full px-4 py-2 rounded-lg
              bg-dark-400
              text-white
              border border-gray-600
              focus:border-primary-500
              focus:outline-none
              disabled:opacity-50
              flex items-center justify-between
              hover:border-gray-500
              transition
            "
          >
            <span className="flex items-center gap-2">
              {currentStreamType && (
                <>
                  <span className="text-sm font-medium">{currentStreamType.label}</span>
                  <span className="text-xs text-gray-400">
                    {currentStreamType.description}
                  </span>
                </>
              )}
            </span>
            <ChevronDown
              size={18}
              className={`transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`}
            />
          </button>

          {/* Dropdown Menu */}
          {isDropdownOpen && !connected && !loading && (
            <div className="
              absolute top-full left-0 right-0 mt-1 z-50
              bg-dark-400 border border-gray-600 rounded-lg
              shadow-lg overflow-hidden
            ">
              {STREAM_TYPES.map((type) => (
                <button
                  key={type.id}
                  onClick={() => {
                    setStreamType(type.id);
                    setIsDropdownOpen(false);
                    setError(null);
                  }}
                  className={`
                    w-full px-4 py-3 text-left transition
                    border-b border-gray-700 last:border-b-0
                    hover:bg-dark-300
                    ${streamType === type.id ? 'bg-primary/20 border-l-4 border-l-primary' : ''}
                  `}
                >
                  <div className="font-semibold text-white">{type.label}</div>
                  <div className="text-xs text-gray-400 mt-1">{type.description}</div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Connection Input and Button */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            {connected ? (
              <Wifi className="text-green-500 animate-pulse" size={24} />
            ) : (
              <WifiOff className="text-red-500" size={24} />
            )}
            <span className="font-semibold text-sm">
              {connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>

          <input
            id="camera-source"
            name="camera_source"
            type="text"
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              setError(null);
            }}
            onKeyPress={handleKeyPress}
            placeholder={currentStreamType?.placeholder || 'Enter camera source...'}
            disabled={connected || loading}
            className="
              flex-1 px-4 py-2 rounded-lg
              bg-dark-400
              text-white
              caret-primary-400
              placeholder-gray-400
              border border-gray-600
              focus:border-primary-500
              focus:outline-none
              disabled:opacity-50
              text-sm
            "
          />

          <button
            onClick={handleConnect}
            disabled={loading}
            className={`px-6 py-2 rounded-lg font-semibold transition whitespace-nowrap text-sm ${
              connected
                ? 'bg-red-600 hover:bg-red-700'
                : loading
                ? 'bg-yellow-600'
                : 'bg-primary hover:bg-blue-600'
            } disabled:opacity-50`}
          >
            {loading ? `Connecting ${connectionTime}s...` : connected ? 'Disconnect' : 'Connect'}
          </button>
        </div>
      </div>

      {/* Info Message for RTSP Stream Type */}
      {streamType === 'rtsp' && !error && (
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
          <div className="flex gap-2">
            <AlertCircle size={18} className="text-blue-500 flex-shrink-0 mt-0.5" />
            <div className="flex-1 text-xs text-blue-300 whitespace-pre-wrap">
              <strong>RTSP Connection Help:</strong>
              <br />
              {currentStreamType?.help}
            </div>
          </div>
        </div>
      )}

      {/* Error Message with Stream-Specific Help */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 space-y-3">
          <div className="flex gap-2">
            <AlertCircle size={18} className="text-red-500 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-red-400 font-semibold">{error}</p>
            </div>
          </div>
          
          {currentStreamType && (
            <div className="bg-red-900/20 rounded p-3 space-y-2">
              <p className="text-xs text-red-300 font-semibold">
                {currentStreamType.label} Guide:
              </p>
              <p className="text-xs text-red-300 whitespace-pre-wrap">
                {currentStreamType.help}
              </p>
              <p className="text-xs text-red-400 mt-2">
                Example: <code className="bg-red-900/40 px-1.5 py-0.5 rounded">{currentStreamType.example}</code>
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}