import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Clock, Calendar, Plus } from 'lucide-react';
import { scheduleAPI } from '../services/api';
import toast from 'react-hot-toast';

export default function SchedulerModal({ isOpen, onClose, cameras, onScheduleCreated }) {
  const [formData, setFormData] = useState({
    camera_id: '',
    name: '',
    days_of_week: [],
    start_time: '09:00',
    end_time: '17:00',
  });

  const [loading, setLoading] = useState(false);

  const daysOfWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

  const toggleDay = (day) => {
    setFormData(prev => ({
      ...prev,
      days_of_week: prev.days_of_week.includes(day)
        ? prev.days_of_week.filter(d => d !== day)
        : [...prev.days_of_week, day]
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.camera_id) {
      toast.error('Please select a camera');
      return;
    }

    if (formData.days_of_week.length === 0) {
      toast.error('Please select at least one day');
      return;
    }

    setLoading(true);
    try {
      await scheduleAPI.create(formData);
      toast.success('Schedule created successfully!');
      onScheduleCreated?.();
      onClose();
      
      // Reset form
      setFormData({
        camera_id: '',
        name: '',
        days_of_week: [],
        start_time: '09:00',
        end_time: '17:00',
      });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create schedule');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className="glass-dark rounded-2xl w-full max-w-2xl border border-white/10 shadow-2xl">
              {/* Header */}
              <div className="p-6 border-b border-white/10 flex justify-between items-center">
                <div>
                  <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                    <Clock className="text-primary-400" size={28} />
                    Schedule Recording
                  </h2>
                  <p className="text-gray-400 text-sm mt-1">
                    Automatically record at specific times
                  </p>
                </div>
                <button
                  onClick={onClose}
                  className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                >
                  <X size={24} className="text-gray-400" />
                </button>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="p-6 space-y-6">
                {/* Schedule Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Schedule Name
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                    className="input-field"
                    placeholder="e.g., Business Hours Recording"
                  />
                </div>

                {/* Camera Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Select Camera
                  </label>
                  <select
                    value={formData.camera_id}
                    onChange={(e) => setFormData({ ...formData, camera_id: e.target.value })}
                    required
                    className="input-field"
                  >
                    <option value="">Choose a camera...</option>
                    {cameras.map((camera) => (
                      <option key={camera.id} value={camera.id}>
                        {camera.name} ({camera.connection_type})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Days of Week */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-3">
                    Select Days
                  </label>
                  <div className="grid grid-cols-4 gap-2">
                    {daysOfWeek.map((day) => (
                      <button
                        key={day}
                        type="button"
                        onClick={() => toggleDay(day)}
                        className={`py-2 px-3 rounded-lg font-medium text-sm transition-all ${
                          formData.days_of_week.includes(day)
                            ? 'bg-primary-500 text-white shadow-glow'
                            : 'bg-dark-400/50 text-gray-400 hover:bg-dark-400'
                        }`}
                      >
                        {day.substring(0, 3)}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Time Range */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Start Time
                    </label>
                    <input
                      type="time"
                      value={formData.start_time}
                      onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                      required
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      End Time
                    </label>
                    <input
                      type="time"
                      value={formData.end_time}
                      onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                      required
                      className="input-field"
                    />
                  </div>
                </div>

                {/* Info */}
                <div className="bg-primary-500/10 border border-primary-500/20 rounded-lg p-4">
                  <p className="text-sm text-primary-300">
                    📅 Recording will automatically start at {formData.start_time} and stop at {formData.end_time} on selected days.
                  </p>
                </div>

                {/* Actions */}
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={onClose}
                    className="btn-secondary flex-1"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={loading}
                    className="btn-primary flex-1 flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                        Creating...
                      </>
                    ) : (
                      <>
                        <Plus size={18} />
                        Create Schedule
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}