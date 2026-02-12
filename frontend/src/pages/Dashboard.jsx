import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { useCameraStore } from '../store/cameraStore';
import Navbar from '../components/Navbar';
import ConnectionBar from '../components/ConnectionBar';
import VideoPlayer from '../components/VideoPlayer';
import { motion } from 'framer-motion';
import { 
  Camera, Video, Image as ImageIcon, Maximize2, ZoomIn, 
  Radio, Activity, Thermometer, Eye, Download, Settings2
} from 'lucide-react';

export default function Dashboard() {
  const { token } = useAuthStore();
  const { connected } = useCameraStore();
  const navigate = useNavigate();
  const [zoom, setZoom] = useState(0);
  const [recording, setRecording] = useState(false);

  useEffect(() => {
    if (!token) navigate('/login');
  }, [token, navigate]);

  const stats = [
    { label: 'Active Cameras', value: connected ? '1' : '0', icon: Camera, color: 'text-primary-400' },
    { label: 'Recordings', value: '0', icon: Video, color: 'text-accent-green' },
    { label: 'Detections', value: '0', icon: Eye, color: 'text-accent-orange' },
    { label: 'Storage', value: '0 GB', icon: Download, color: 'text-accent-purple' },
  ];

  return (
    <div className="min-h-screen bg-dark-500">
      <Navbar />
      
      <div className="p-6 space-y-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((stat, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="glass-dark rounded-xl p-5 border border-white/10 hover:border-primary-500/50 transition-all duration-300"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-400 mb-1">{stat.label}</p>
                  <p className="text-3xl font-bold text-white">{stat.value}</p>
                </div>
                <div className={`w-12 h-12 rounded-lg bg-white/5 flex items-center justify-center ${stat.color}`}>
                  <stat.icon size={24} />
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Connection Bar */}
        <ConnectionBar />
        
        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Video Area - 3 columns */}
          <div className="lg:col-span-3 space-y-4">
            {/* Main Video Player */}
            <div className="glass-dark rounded-xl p-4 border border-white/10">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
                    <span className="text-sm font-medium">
                      {connected ? 'Live Stream' : 'No Signal'}
                    </span>
                  </div>
                  {connected && (
                    <div className="flex items-center gap-2 px-3 py-1 bg-primary-500/10 rounded-full border border-primary-500/20">
                      <Activity size={14} className="text-primary-400 animate-pulse" />
                      <span className="text-xs font-medium text-primary-400">25 FPS</span>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <button className="p-2 hover:bg-white/10 rounded-lg transition-colors">
                    <Maximize2 size={18} className="text-gray-400" />
                  </button>
                  <button className="p-2 hover:bg-white/10 rounded-lg transition-colors">
                    <Settings2 size={18} className="text-gray-400" />
                  </button>
                </div>
              </div>

              <div className="aspect-video rounded-lg overflow-hidden bg-black">
                <VideoPlayer />
              </div>

              {/* Video Controls */}
              <div className="flex items-center gap-4 mt-4">
                <div className="flex items-center gap-2 flex-1">
                  <Thermometer size={16} className="text-gray-400" />
                  <div className="flex-1 h-2 bg-dark-400 rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-blue-500 via-yellow-500 to-red-500" style={{ width: '60%' }}></div>
                  </div>
                  <span className="text-sm text-gray-400">25°C</span>
                </div>
              </div>
            </div>
            
            {/* Camera Thumbnails */}
            <div className="grid grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <motion.div
                  key={i}
                  whileHover={{ scale: 1.02 }}
                  className="glass-dark rounded-lg overflow-hidden border border-white/10 hover:border-primary-500/50 transition-all duration-300 cursor-pointer group"
                >
                  <div className="aspect-video bg-dark-400 flex items-center justify-center relative">
                    <Camera className="text-gray-600 group-hover:text-primary-400 transition-colors" size={24} />
                    <div className="absolute top-2 left-2 px-2 py-1 bg-black/50 rounded text-xs">
                      Camera {i}
                    </div>
                    {i === 1 && connected && (
                      <div className="absolute top-2 right-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Control Panel - 1 column */}
          <div className="space-y-4">
            {/* Recording Controls */}
            <div className="glass-dark rounded-xl p-4 border border-white/10">
              <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
                <Radio size={18} className="text-primary-400" />
                Recording
              </h3>
              <div className="space-y-3">
                <button 
                  onClick={() => setRecording(!recording)}
                  className={`w-full py-3 rounded-lg font-semibold transition-all duration-200 flex items-center justify-center gap-2 ${
                    recording 
                      ? 'bg-red-600 hover:bg-red-700 shadow-lg shadow-red-500/30' 
                      : 'btn-primary'
                  }`}
                >
                  <Video size={18} />
                  {recording ? 'STOP Recording' : 'START Recording'}
                </button>

                <button className="btn-secondary w-full flex items-center justify-center gap-2">
                  <ImageIcon size={18} />
                  Screenshot
                </button>
              </div>
            </div>

            {/* Zoom Control */}
            <div className="glass-dark rounded-xl p-4 border border-white/10">
              <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
                <ZoomIn size={18} className="text-primary-400" />
                Zoom Level
              </h3>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <input
                    type="range"
                    min="0"
                    max="10"
                    value={zoom}
                    onChange={(e) => setZoom(e.target.value)}
                    className="flex-1 h-2 bg-dark-400 rounded-full appearance-none cursor-pointer"
                    style={{
                      background: `linear-gradient(to right, #1a90ff 0%, #1a90ff ${zoom * 10}%, #2d2d42 ${zoom * 10}%, #2d2d42 100%)`
                    }}
                  />
                  <span className="text-sm font-mono text-primary-400 w-8 text-right">{zoom}x</span>
                </div>
                <button 
                  onClick={() => setZoom(0)}
                  className="text-sm text-gray-400 hover:text-white transition-colors"
                >
                  Reset Zoom
                </button>
              </div>
            </div>

            {/* Status Panel */}
            <div className="glass-dark rounded-xl p-4 border border-white/10">
              <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
                <Activity size={18} className="text-primary-400" />
                System Status
              </h3>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Connection</span>
                  <span className={connected ? 'text-green-400 font-medium' : 'text-red-400 font-medium'}>
                    {connected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Frame Rate</span>
                  <span className="text-white font-mono">{connected ? '25' : '0'} FPS</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Resolution</span>
                  <span className="text-white font-mono">1280x720</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Latency</span>
                  <span className="text-white font-mono">{connected ? '45' : '0'} ms</span>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="glass-dark rounded-xl p-4 border border-white/10">
              <h3 className="font-semibold text-white mb-4">Quick Actions</h3>
              <div className="space-y-2 text-sm">
                <button className="w-full text-left px-3 py-2 hover:bg-white/10 rounded-lg transition-colors text-gray-300">
                  View Recordings
                </button>
                <button className="w-full text-left px-3 py-2 hover:bg-white/10 rounded-lg transition-colors text-gray-300">
                  Detection History
                </button>
                <button className="w-full text-left px-3 py-2 hover:bg-white/10 rounded-lg transition-colors text-gray-300">
                  Export Data
                </button>
                <button className="w-full text-left px-3 py-2 hover:bg-white/10 rounded-lg transition-colors text-gray-300">
                  System Settings
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}