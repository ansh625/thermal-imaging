import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { useCameraStore } from '../store/cameraStore';

import Navbar from '../components/Navbar';
import ConnectionBar from '../components/ConnectionBar';
import VideoPlayer from '../components/VideoPlayer';
import SchedulerModal from '../components/SchedulerModal';

import { useRealTimeData } from '../hooks/useRealTimeData';
import { dashboardAPI, cameraAPI, recordingAPI, screenshotAPI } from '../services/api';

import toast from 'react-hot-toast';
import { motion } from 'framer-motion';
import { 
  Camera, Video, Image as ImageIcon, Maximize2, ZoomIn,
  Radio, Activity, Thermometer, Eye, Download, Settings2, Clock
} from 'lucide-react';

export default function Dashboard() {
  const { token } = useAuthStore();
  const { connected, sessionId } = useCameraStore();
  const navigate = useNavigate();

  const { stats: realtimeStats, isConnected } = useRealTimeData();

  const [zoom, setZoom] = useState(0);
  const [recording, setRecording] = useState(false);
  const [recordingLoading, setRecordingLoading] = useState(false);
  const [screenshotLoading, setScreenshotLoading] = useState(false);
  const [showScheduler, setShowScheduler] = useState(false);
  const [cameras, setCameras] = useState([]);

  const [stats, setStats] = useState({
    active_cameras: 0,
    total_recordings: 0,
    total_detections: 0,
    storage_used_gb: 0,
  });

  /* Auth Guard */
  useEffect(() => {
    if (!token) navigate('/login');
  }, [token, navigate]);

  /* Initial Load */
  useEffect(() => {
    loadStats();
    loadCameras();
  }, []);

  /* Realtime Updates */
  useEffect(() => {
    if (realtimeStats) {
      setStats(realtimeStats);
    }
  }, [realtimeStats]);

  const loadStats = async () => {
    try {
      const response = await dashboardAPI.getStats();
      setStats(response.data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const loadCameras = async () => {
    try {
      const response = await cameraAPI.list();
      setCameras(response.data.cameras);
    } catch (error) {
      console.error('Failed to load cameras:', error);
    }
  };

  const handleRecordingToggle = async () => {
    if (!sessionId) {
      toast.error('No camera connected');
      return;
    }

    setRecordingLoading(true);
    try {
      if (recording) {
        // Stop recording
        await recordingAPI.stop(sessionId);
        setRecording(false);
        toast.success('Recording stopped');
        loadStats();
      } else {
        // Start recording
        await recordingAPI.start(sessionId);
        setRecording(true);
        toast.success('Recording started');
        loadStats();
      }
    } catch (error) {
      console.error('Recording error:', error);
      toast.error(error.response?.data?.detail || 'Recording failed');
    } finally {
      setRecordingLoading(false);
    }
  };

  const handleScreenshot = async () => {
    if (!sessionId) {
      toast.error('No camera connected');
      return;
    }

    setScreenshotLoading(true);
    try {
      const response = await screenshotAPI.capture(sessionId);
      toast.success('Screenshot captured successfully');
    } catch (error) {
      console.error('Screenshot error:', error);
      toast.error(error.response?.data?.detail || 'Screenshot failed');
    } finally {
      setScreenshotLoading(false);
    }
  };

  const statsData = [
    {
      label: 'Active Cameras',
      value: stats.active_cameras,
      icon: Camera,
      color: 'text-primary-400',
    },
    {
      label: 'Recordings',
      value: stats.total_recordings,
      icon: Video,
      color: 'text-accent-green',
    },
    {
      label: 'Detections',
      value: stats.total_detections,
      icon: Eye,
      color: 'text-accent-orange',
    },
    {
      label: 'Storage',
      value: `${stats.storage_used_gb} GB`,
      icon: Download,
      color: 'text-accent-purple',
    },
  ];

  return (
    <div className="min-h-screen bg-dark-500">
      <Navbar />

      <div className="p-6 space-y-6">

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {statsData.map((stat, i) => (
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

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">

          {/* Video Section */}
          <div className="lg:col-span-3 space-y-4">
            <div className="glass-dark rounded-xl p-4 border border-white/10">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                    <span className="text-sm font-medium">
                      {connected ? 'Live Stream' : 'No Signal'}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 text-xs text-gray-400">
                    <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                    {isConnected ? 'Live' : 'Offline'}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    className="p-2 hover:bg-white/10 rounded-lg"
                    onClick={() => {
                      const videoBox = document.querySelector('.aspect-video');
                      if (videoBox) {
                        if (!document.fullscreenElement) {
                          videoBox.requestFullscreen();
                        } else {
                          document.exitFullscreen();
                        }
                      }
                    }}
                    title="Enlarge"
                  >
                    <Maximize2 size={18} />
                  </button>
                  {/* Settings button removed as requested */}
                      {/* Stream Settings modal removed as requested */}
                </div>
              </div>

              <div className="aspect-video rounded-lg overflow-hidden bg-black">
                <VideoPlayer zoom={parseInt(zoom)} />
              </div>

              <div className="flex items-center gap-4 mt-4">
                <Thermometer size={16} className="text-gray-400" />
                <div className="flex-1 h-2 bg-dark-400 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-blue-500 via-yellow-500 to-red-500 w-[60%]" />
                </div>
                <span className="text-sm text-gray-400">25°C</span>
              </div>
            </div>
          </div>

          {/* Control Panel */}
          <div className="space-y-4">

            {/* Recording */}
            <div className="glass-dark rounded-xl p-4 border border-white/10">
              <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
                <Radio size={18} className="text-primary-400" />
                Recording
              </h3>

              <button
                onClick={handleRecordingToggle}
                disabled={recordingLoading || !sessionId}
                className={`w-full py-3 rounded-lg font-semibold flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed ${
                  recording ? 'bg-red-600 hover:bg-red-700' : 'btn-primary'
                }`}
              >
                {recordingLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    {recording ? 'Stopping...' : 'Starting...'}
                  </>
                ) : (
                  <>
                    <Video size={18} />
                    {recording ? 'STOP Recording' : 'START Recording'}
                  </>
                )}
              </button>

              <button 
                onClick={handleScreenshot}
                disabled={screenshotLoading || !sessionId}
                className="btn-secondary w-full mt-2 flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {screenshotLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Capturing...
                  </>
                ) : (
                  <>
                    <ImageIcon size={18} />
                    Screenshot
                  </>
                )}
              </button>

              <button
                onClick={() => setShowScheduler(true)}
                className="btn-secondary w-full mt-2 flex items-center justify-center gap-2"
              >
                <Clock size={18} />
                Schedule Recording
              </button>
            </div>

            {/* Zoom */}
            <div className="glass-dark rounded-xl p-4 border border-white/10">
              <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
                <ZoomIn size={18} className="text-primary-400" />
                Zoom Level
              </h3>

              <input
                type="range"
                min="0"
                max="10"
                value={zoom}
                onChange={(e) => setZoom(e.target.value)}
                className="w-full"
              />
              <div className="text-right text-primary-400 font-mono">{zoom}x</div>
            </div>
          </div>
        </div>
      </div>

      {/* Scheduler Modal */}
      <SchedulerModal
        isOpen={showScheduler}
        onClose={() => setShowScheduler(false)}
        cameras={cameras}
        onScheduleCreated={loadCameras}
      />
    </div>
  );
}
