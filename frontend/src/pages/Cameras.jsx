import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import Navbar from '../components/Navbar';
import { cameraAPI } from '../services/api';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';
import { Camera, Trash2, Power, PowerOff, Edit2, Plus } from 'lucide-react';

export default function Cameras() {
  const { token } = useAuthStore();
  const navigate = useNavigate();
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) navigate('/login');
    else loadCameras();
  }, [token, navigate]);

  const loadCameras = async () => {
    setLoading(true);
    try {
      const response = await cameraAPI.list();
      setCameras(response.data.cameras);
    } catch (error) {
      toast.error('Failed to load cameras');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (cameraId) => {
    if (!confirm('Are you sure you want to delete this camera?')) return;

    try {
      await cameraAPI.delete(cameraId);
      toast.success('Camera deleted');
      loadCameras();
    } catch (error) {
      toast.error('Failed to delete camera');
    }
  };

  const getStatusColor = (status) => {
    return status === 'connected' ? 'text-green-500' : 'text-red-500';
  };

  const getStatusIcon = (status) => {
    return status === 'connected' ? <Power size={16} /> : <PowerOff size={16} />;
  };

  return (
    <div className="min-h-screen bg-dark-500">
      <Navbar />
      
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Cameras</h1>
            <p className="text-gray-400">Manage your camera connections</p>
          </div>
          <button
            onClick={() => navigate('/dashboard')}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={18} />
            Add Camera
          </button>
        </div>

        {loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="w-12 h-12 border-4 border-primary-500/30 border-t-primary-500 rounded-full animate-spin"></div>
          </div>
        ) : cameras.length === 0 ? (
          <div className="glass-dark rounded-xl p-12 text-center border border-white/10">
            <Camera size={64} className="mx-auto text-gray-600 mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">No Cameras Yet</h3>
            <p className="text-gray-400 mb-6">Add your first camera to get started</p>
            <button
              onClick={() => navigate('/dashboard')}
              className="btn-primary"
            >
              Add Camera
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {cameras.map((camera, index) => (
              <motion.div
                key={camera.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="glass-dark rounded-xl p-6 border border-white/10 hover:border-primary-500/50 transition-all"
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-lg bg-primary-500/20 flex items-center justify-center">
                      <Camera className="text-primary-400" size={24} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-white">{camera.name}</h3>
                      <p className="text-xs text-gray-400 uppercase">{camera.connection_type}</p>
                    </div>
                  </div>
                  <div className={`flex items-center gap-1 ${getStatusColor(camera.status)}`}>
                    {getStatusIcon(camera.status)}
                    <span className="text-xs font-medium capitalize">{camera.status}</span>
                  </div>
                </div>

                <div className="space-y-2 mb-4 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">URL:</span>
                    <span className="text-white font-mono text-xs truncate max-w-[150px]">
                      {camera.connection_url}
                    </span>
                  </div>
                  {camera.resolution && (
                    <div className="flex justify-between">
                      <span className="text-gray-400">Resolution:</span>
                      <span className="text-white">{camera.resolution}</span>
                    </div>
                  )}
                  {camera.fps > 0 && (
                    <div className="flex justify-between">
                      <span className="text-gray-400">FPS:</span>
                      <span className="text-white">{camera.fps}</span>
                    </div>
                  )}
                  {camera.last_seen && (
                    <div className="flex justify-between">
                      <span className="text-gray-400">Last Seen:</span>
                      <span className="text-white text-xs">
                        {new Date(camera.last_seen).toLocaleString()}
                      </span>
                    </div>
                  )}
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => navigate('/dashboard')}
                    className="flex-1 py-2 bg-primary-500 hover:bg-primary-600 rounded-lg text-sm font-medium transition-colors"
                  >
                    View Stream
                  </button>
                  <button
                    onClick={() => handleDelete(camera.id)}
                    className="p-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}