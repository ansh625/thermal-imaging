import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import Navbar from '../components/Navbar';
import { scheduleAPI, cameraAPI } from '../services/api';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';
import { Clock, Trash2, Power, PowerOff, Plus, Calendar, AlertCircle, Camera } from 'lucide-react';
import SchedulerModal from '../components/SchedulerModal';

export default function Schedules() {
  const { token } = useAuthStore();
  const navigate = useNavigate();
  const [schedules, setSchedules] = useState([]);
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showScheduler, setShowScheduler] = useState(false);

  useEffect(() => {
    if (!token) navigate('/login');
    else {
      loadSchedules();
      loadCameras();
    }
  }, [token, navigate]);

  const loadSchedules = async () => {
    try {
      const response = await scheduleAPI.list();
      setSchedules(response.data.schedules || []);
    } catch (error) {
      let errorMessage = 'Failed to load schedules';
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        errorMessage = Array.isArray(detail) ? detail[0]?.msg || errorMessage : detail;
      }
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const loadCameras = async () => {
    try {
      const response = await cameraAPI.list();
      setCameras(response.data.cameras || []);
    } catch (error) {
      console.error('Failed to load cameras');
    }
  };

  const getCameraName = (cameraId) => {
    const camera = cameras.find((c) => c.id === cameraId);
    return camera ? camera.name : `Camera ${cameraId}`;
  };

  const handleToggle = async (scheduleId, currentStatus) => {
    try {
      await scheduleAPI.toggle(scheduleId);
      toast.success(currentStatus ? 'Schedule disabled' : 'Schedule enabled');
      loadSchedules();
    } catch (error) {
      toast.error('Failed to toggle schedule');
    }
  };

  const handleDelete = async (scheduleId, scheduleName) => {
    if (!confirm(`Delete schedule "${scheduleName}"?`)) return;

    try {
      await scheduleAPI.delete(scheduleId);
      toast.success('Schedule deleted');
      loadSchedules();
    } catch (error) {
      toast.error('Failed to delete schedule');
    }
  };

  const formatDays = (days) => {
    return days.map((d) => d.slice(0, 3)).join(', ');
  };

  return (
    <div className="min-h-screen bg-dark-500">
      <Navbar />

      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Recording Schedules</h1>
            <p className="text-gray-400">Manage your automatic recording schedules</p>
          </div>
          <button
            onClick={() => setShowScheduler(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={18} />
            Create Schedule
          </button>
        </div>

        {loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="w-12 h-12 border-4 border-primary-500/30 border-t-primary-500 rounded-full animate-spin"></div>
          </div>
        ) : schedules.length === 0 ? (
          <div className="glass-dark rounded-xl p-12 text-center border border-white/10">
            <Calendar size={64} className="mx-auto text-gray-600 mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">No Schedules Yet</h3>
            <p className="text-gray-400 mb-6">Create a schedule to automatically record at specific times</p>
            <button
              onClick={() => setShowScheduler(true)}
              className="btn-primary inline-flex items-center gap-2"
            >
              <Plus size={18} />
              Create Your First Schedule
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {schedules.map((schedule, index) => (
              <motion.div
                key={schedule.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="glass-dark rounded-xl p-6 border border-white/10 hover:border-primary-500/50 transition-all"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-3">
                      <h3 className="text-lg font-semibold text-white">{schedule.name}</h3>
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-medium ${
                          schedule.enabled
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-gray-500/20 text-gray-400'
                        }`}
                      >
                        {schedule.enabled ? '● Active' : '● Inactive'}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-sm text-gray-400">
                      <div className="flex items-center gap-2">
                        <Camera size={14} className="text-primary-400" />
                        <span>{getCameraName(schedule.camera_id)}</span>
                      </div>

                      <div className="flex items-center gap-2">
                        <Clock size={14} className="text-primary-400" />
                        <span>
                          {schedule.start_time} - {schedule.end_time}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 col-span-2">
                        <Calendar size={14} className="text-primary-400" />
                        <span>{formatDays(schedule.days_of_week)}</span>
                      </div>
                    </div>

                    {schedule.enabled && (
                      <div className="mt-3 p-2 bg-green-500/10 border border-green-500/20 rounded flex items-center gap-2 text-xs text-green-400">
                        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                        Recording automatically at scheduled times
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2 ml-4">
                    <button
                      onClick={() => handleToggle(schedule.id, schedule.enabled)}
                      className={`p-2 rounded-lg transition-colors ${
                        schedule.enabled
                          ? 'bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-400'
                          : 'bg-gray-500/20 hover:bg-gray-500/30 text-gray-400'
                      }`}
                      title={schedule.enabled ? 'Disable schedule' : 'Enable schedule'}
                    >
                      {schedule.enabled ? <Power size={18} /> : <PowerOff size={18} />}
                    </button>

                    <button
                      onClick={() => handleDelete(schedule.id, schedule.name)}
                      className="p-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors"
                      title="Delete schedule"
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

      {/* Scheduler Modal */}
      <SchedulerModal
        isOpen={showScheduler}
        onClose={() => setShowScheduler(false)}
        cameras={cameras}
        onScheduleCreated={loadSchedules}
      />
    </div>
  );
}
