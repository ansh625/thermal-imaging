import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import Navbar from '../components/Navbar';
import ConnectionBar from '../components/ConnectionBar';
import VideoPlayer from '../components/VideoPlayer';
import { Camera, Video, Image as ImageIcon } from 'lucide-react';

export default function Dashboard() {
  const { token } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    if (!token) {
      navigate('/login');
    }
  }, [token, navigate]);

  return (
    <div className="min-h-screen bg-dark">
      <Navbar />
      
      <div className="p-6">
        <ConnectionBar />
        
        <div className="grid grid-cols-4 gap-6 mt-6">
          {/* Main Video Area */}
          <div className="col-span-3 space-y-4">
            <div className="h-[500px]">
              <VideoPlayer />
            </div>
            
            {/* Camera Thumbnails */}
            <div className="grid grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="aspect-video bg-secondary rounded-lg border border-gray-700 flex items-center justify-center">
                  <Camera className="text-gray-600" size={32} />
                  <span className="ml-2 text-gray-600">Camera {i}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Control Panel */}
          <div className="space-y-4">
            <button className="w-full py-3 bg-red-600 hover:bg-red-700 rounded-lg font-semibold transition flex items-center justify-center gap-2">
              <Video size={20} />
              START Recording
            </button>

            <button className="w-full py-3 bg-primary hover:bg-blue-600 rounded-lg font-semibold transition flex items-center justify-center gap-2">
              <ImageIcon size={20} />
              Take Screenshot
            </button>

            <div className="bg-secondary p-4 rounded-lg">
              <h3 className="font-semibold mb-3">Zoom Control</h3>
              <input
                type="range"
                min="0"
                max="10"
                defaultValue="0"
                className="w-full"
              />
            </div>

            <div className="bg-secondary p-4 rounded-lg">
              <h3 className="font-semibold mb-3">Status</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Connection:</span>
                  <span className="text-red-500">Disconnected</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">FPS:</span>
                  <span>0</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}