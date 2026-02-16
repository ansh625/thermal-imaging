import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import Navbar from '../components/Navbar';
import { detectionAPI, dashboardAPI } from '../services/api';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';
import { Eye, TrendingUp, BarChart3, Image as ImageIcon } from 'lucide-react';

export default function Analytics() {
  const { token } = useAuthStore();
  const navigate = useNavigate();
  const [detections, setDetections] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('detections');

  useEffect(() => {
    if (!token) navigate('/login');
    else loadData();
  }, [token, navigate]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [detectionsRes, statsRes] = await Promise.all([
        detectionAPI.list(100),
        dashboardAPI.getStats()
      ]);
      setDetections(detectionsRes.data.detections);
      setStats(statsRes.data);
    } catch (error) {
      toast.error('Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  const getDetectionsByClass = () => {
    const counts = {};
    detections.forEach(det => {
      counts[det.class_name] = (counts[det.class_name] || 0) + 1;
    });
    return Object.entries(counts).sort((a, b) => b[1] - a[1]);
  };

  return (
    <div className="min-h-screen bg-dark-500">
      <Navbar />
      
      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-white mb-2">Analytics</h1>
          <p className="text-gray-400">View detection statistics and insights</p>
        </div>

        {loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="w-12 h-12 border-4 border-primary-500/30 border-t-primary-500 rounded-full animate-spin"></div>
          </div>
        ) : (
          <>
            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="glass-dark rounded-xl p-6 border border-white/10">
                <div className="flex items-center justify-between mb-2">
                  <Eye className="text-primary-400" size={24} />
                  <span className="text-xs text-gray-400">Total</span>
                </div>
                <p className="text-3xl font-bold text-white">{stats?.total_detections || 0}</p>
                <p className="text-sm text-gray-400">Detections</p>
              </div>

              <div className="glass-dark rounded-xl p-6 border border-white/10">
                <div className="flex items-center justify-between mb-2">
                  <TrendingUp className="text-green-400" size={24} />
                  <span className="text-xs text-gray-400">Today</span>
                </div>
                <p className="text-3xl font-bold text-white">
                  {detections.filter(d => 
                    new Date(d.detected_at).toDateString() === new Date().toDateString()
                  ).length}
                </p>
                <p className="text-sm text-gray-400">New Detections</p>
              </div>

              <div className="glass-dark rounded-xl p-6 border border-white/10">
                <div className="flex items-center justify-between mb-2">
                  <BarChart3 className="text-purple-400" size={24} />
                  <span className="text-xs text-gray-400">Types</span>
                </div>
                <p className="text-3xl font-bold text-white">
                  {getDetectionsByClass().length}
                </p>
                <p className="text-sm text-gray-400">Object Classes</p>
              </div>

              <div className="glass-dark rounded-xl p-6 border border-white/10">
                <div className="flex items-center justify-between mb-2">
                  <ImageIcon className="text-orange-400" size={24} />
                  <span className="text-xs text-gray-400">Storage</span>
                </div>
                <p className="text-3xl font-bold text-white">
                  {stats?.storage_breakdown?.detections_gb || 0}
                </p>
                <p className="text-sm text-gray-400">GB Used</p>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-4 mb-6 border-b border-white/10">
              <button
                onClick={() => setActiveTab('detections')}
                className={`pb-3 px-1 font-medium transition-colors ${
                  activeTab === 'detections'
                    ? 'text-primary-400 border-b-2 border-primary-400'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Detection History
              </button>
              <button
                onClick={() => setActiveTab('stats')}
                className={`pb-3 px-1 font-medium transition-colors ${
                  activeTab === 'stats'
                    ? 'text-primary-400 border-b-2 border-primary-400'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Statistics
              </button>
            </div>

            {/* Content */}
            {activeTab === 'detections' ? (
              detections.length === 0 ? (
                <div className="glass-dark rounded-xl p-12 text-center border border-white/10">
                  <Eye size={64} className="mx-auto text-gray-600 mb-4" />
                  <h3 className="text-xl font-semibold text-white mb-2">No Detections Yet</h3>
                  <p className="text-gray-400">Enable object detection to start tracking</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {detections.map((detection, index) => (
                    <motion.div
                      key={detection.id}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: index * 0.03 }}
                      className="glass-dark rounded-xl overflow-hidden border border-white/10 hover:border-primary-500/50 transition-all"
                    >
                      {detection.screenshot_path ? (
                        <img
                          src={`http://localhost:8000/${detection.screenshot_path}`}
                          alt={detection.class_name}
                          className="w-full h-40 object-cover"
                        />
                      ) : (
                        <div className="w-full h-40 bg-dark-400 flex items-center justify-center">
                          <ImageIcon className="text-gray-600" size={32} />
                        </div>
                      )}
                      <div className="p-3">
                        <div className="flex justify-between items-start mb-2">
                          <h4 className="font-semibold text-white capitalize">
                            {detection.class_name}
                          </h4>
                          <span className="text-xs px-2 py-1 bg-primary-500/20 text-primary-400 rounded">
                            {(detection.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                        <p className="text-xs text-gray-400">
                          {new Date(detection.detected_at).toLocaleString()}
                        </p>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )
            ) : (
              <div className="glass-dark rounded-xl p-6 border border-white/10">
                <h3 className="text-xl font-semibold text-white mb-6">Detection Statistics</h3>
                <div className="space-y-4">
                  {getDetectionsByClass().map(([className, count]) => (
                    <div key={className} className="flex items-center gap-4">
                      <div className="flex-1">
                        <div className="flex justify-between items-center mb-2">
                          <span className="text-white capitalize font-medium">{className}</span>
                          <span className="text-gray-400">{count} detections</span>
                        </div>
                        <div className="h-2 bg-dark-400 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary-500 rounded-full"
                            style={{
                              width: `${(count / detections.length) * 100}%`
                            }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}