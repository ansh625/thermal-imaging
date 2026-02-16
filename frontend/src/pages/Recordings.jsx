import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import Navbar from '../components/Navbar';
import { recordingAPI } from '../services/api';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';
import { Video, Download, Trash2, Play, Clock } from 'lucide-react';

export default function Recordings() {
  const { token } = useAuthStore();
  const navigate = useNavigate();
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) navigate('/login');
    else loadRecordings();
  }, [token, navigate]);

  const loadRecordings = async () => {
    setLoading(true);
    try {
      const response = await recordingAPI.list();
      setRecordings(response.data.recordings);
    } catch (error) {
      toast.error('Failed to load recordings');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = (recordingId, filename) => {
    window.open(recordingAPI.download(recordingId), '_blank');
    toast.success(`Downloading ${filename}`);
  };

  const handleDelete = async (recordingId) => {
    if (!confirm('Are you sure you want to delete this recording?')) return;

    try {
      await recordingAPI.delete(recordingId);
      toast.success('Recording deleted');
      loadRecordings();
    } catch (error) {
      toast.error('Failed to delete recording');
    }
  };

  const formatDuration = (seconds) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return hrs > 0 ? `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
                   : `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="min-h-screen bg-dark-500">
      <Navbar />
      
      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-white mb-2">Recordings</h1>
          <p className="text-gray-400">View and manage your video recordings</p>
        </div>

        {loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="w-12 h-12 border-4 border-primary-500/30 border-t-primary-500 rounded-full animate-spin"></div>
          </div>
        ) : recordings.length === 0 ? (
          <div className="glass-dark rounded-xl p-12 text-center border border-white/10">
            <Video size={64} className="mx-auto text-gray-600 mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">No Recordings Yet</h3>
            <p className="text-gray-400 mb-6">Start recording to see your videos here</p>
            <button
              onClick={() => navigate('/dashboard')}
              className="btn-primary"
            >
              Go to Dashboard
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {recordings.map((recording, index) => (
              <motion.div
                key={recording.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="glass-dark rounded-xl p-4 border border-white/10 hover:border-primary-500/50 transition-all"
              >
                <div className="flex items-center gap-4">
                  {/* Thumbnail Placeholder */}
                  <div className="w-32 h-20 rounded-lg bg-dark-400 flex items-center justify-center flex-shrink-0">
                    <Play className="text-gray-600" size={32} />
                  </div>

                  {/* Info */}
                  <div className="flex-1">
                    <h3 className="font-semibold text-white mb-1">{recording.filename}</h3>
                    <div className="flex flex-wrap gap-4 text-sm text-gray-400">
                      <span className="flex items-center gap-1">
                        <Clock size={14} />
                        {formatDuration(recording.duration_seconds)}
                      </span>
                      <span>{formatFileSize(recording.file_size_bytes)}</span>
                      <span>{new Date(recording.started_at).toLocaleString()}</span>
                      {recording.is_scheduled && (
                        <span className="px-2 py-0.5 bg-primary-500/20 text-primary-400 rounded text-xs">
                          Scheduled
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleDownload(recording.id, recording.filename)}
                      className="p-2 bg-primary-500/20 hover:bg-primary-500/30 text-primary-400 rounded-lg transition-colors"
                      title="Download"
                    >
                      <Download size={18} />
                    </button>
                    <button
                      onClick={() => handleDelete(recording.id)}
                      className="p-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors"
                      title="Delete"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}