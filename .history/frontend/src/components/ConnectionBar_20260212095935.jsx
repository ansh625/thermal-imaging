import { useState } from 'react';
import { useCameraStore } from '../store/cameraStore';
import { cameraAPI } from '../services/api';
import toast from 'react-hot-toast';
import { Wifi, WifiOff } from 'lucide-react';

export default function ConnectionBar() {
  const [url, setUrl] = useState('');
  const { connected, setSession, disconnect } = useCameraStore();
  const [loading, setLoading] = useState(false);

  const handleConnect = async () => {
    if (connected) {
      disconnect();
      toast.success('Camera disconnected');
      return;
    }

    if (!url.trim()) {
      toast.error('Please enter a camera URL');
      return;
    }

    setLoading(true);
    try {
      const response = await cameraAPI.connect({ url, camera_id: 1 });
      setSession(response.data.session_id);
      toast.success('Camera connected successfully!');
    } catch (error) {
      toast.error('Failed to connect to camera');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-secondary p-4 rounded-lg flex items-center gap-4">
      <div className="flex items-center gap-2">
        {connected ? (
          <Wifi className="text-green-500" size={24} />
        ) : (
          <WifiOff className="text-red-500" size={24} />
        )}
        <span className="font-semibold">
          {connected ? 'Connected' : 'Disconnected'}
        </span>
      </div>

      <input
        type="text"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="Enter IP, USB index (0, 1, 2) or URL..."
        disabled={connected}
        className="flex-1 px-4 py-2 bg-dark border border-gray-600 rounded-lg focus:border-primary outline-none disabled:opacity-50"
      />

      <button
        onClick={handleConnect}
        disabled={loading}
        className={`px-6 py-2 rounded-lg font-semibold transition ${
          connected
            ? 'bg-red-600 hover:bg-red-700'
            : 'bg-primary hover:bg-blue-600'
        } disabled:opacity-50`}
      >
        {loading ? 'Connecting...' : connected ? 'Disconnect' : 'Connect'}
      </button>
    </div>
  );
}