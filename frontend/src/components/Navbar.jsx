import { useAuthStore } from '../store/authStore';
import { useNavigate } from 'react-router-dom';
import { LogOut, User, Settings, Bell, Activity } from 'lucide-react';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function Navbar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="bg-gradient-to-r from-secondary-900 via-dark-500 to-secondary-900 border-b border-secondary-700/50 backdrop-blur-lg sticky top-0 z-50">
      <div className="px-6 py-3">
        <div className="flex justify-between items-center">
          {/* Logo & Brand */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3 group cursor-pointer" onClick={() => navigate('/dashboard')}>
              <div className="relative">
                <img 
                  src="/logo.svg" 
                  alt="CSIO Logo" 
                  className="w-12 h-12 drop-shadow-glow group-hover:scale-110 transition-transform duration-300"
                />
                <div className="absolute inset-0 bg-primary-500/20 rounded-full blur-xl group-hover:bg-primary-500/40 transition-all duration-300"></div>
              </div>
              <div className="flex flex-col">
                <h1 className="text-xl font-display font-bold text-gradient">
                  CSIO ThermalStream
                </h1>
                <p className="text-xs text-gray-400 font-medium">
                  Professional Imaging Platform
                </p>
              </div>
            </div>

            {/* Quick Status Indicator */}
            <div className="hidden md:flex items-center gap-2 ml-6 px-4 py-2 bg-dark-400/30 rounded-full border border-secondary-700/50">
              <Activity size={16} className="text-primary-400 animate-pulse" />
              <span className="text-sm text-gray-300">System Active</span>
            </div>
          </div>

          {/* Right Section */}
          {user && (
            <div className="flex items-center gap-3">
              {/* Notifications */}
              <div className="relative">
                <button
                  onClick={() => setShowNotifications(!showNotifications)}
                  className="relative p-2 hover:bg-white/10 rounded-lg transition-colors"
                >
                  <Bell size={20} className="text-gray-300" />
                  <span className="absolute top-1 right-1 w-2 h-2 bg-accent-red rounded-full"></span>
                </button>

                <AnimatePresence>
                  {showNotifications && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 10 }}
                      className="absolute right-0 mt-2 w-80 glass-dark rounded-xl shadow-2xl border border-white/10 overflow-hidden"
                    >
                      <div className="p-4 border-b border-white/10">
                        <h3 className="font-semibold text-white">Notifications</h3>
                      </div>
                      <div className="max-h-96 overflow-y-auto custom-scrollbar">
                        <div className="p-4 hover:bg-white/5 cursor-pointer border-b border-white/5">
                          <p className="text-sm text-gray-300">Camera 1 connected successfully</p>
                          <p className="text-xs text-gray-500 mt-1">2 minutes ago</p>
                        </div>
                        <div className="p-4 hover:bg-white/5 cursor-pointer">
                          <p className="text-sm text-gray-300">Object detected in stream</p>
                          <p className="text-xs text-gray-500 mt-1">15 minutes ago</p>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* User Menu */}
              <div className="relative">
                <button
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  className="flex items-center gap-3 px-3 py-2 hover:bg-white/10 rounded-lg transition-colors group"
                >
                  <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-glow">
                    <User size={18} className="text-white" />
                  </div>
                  <div className="hidden md:block text-left">
                    <p className="text-sm font-semibold text-white">{user.full_name || 'User'}</p>
                    <p className="text-xs text-gray-400">{user.email}</p>
                  </div>
                </button>

                <AnimatePresence>
                  {showUserMenu && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 10 }}
                      className="absolute right-0 mt-2 w-56 glass-dark rounded-xl shadow-2xl border border-white/10 overflow-hidden"
                    >
                      <div className="p-3 border-b border-white/10">
                        <p className="text-sm font-semibold text-white">{user.full_name}</p>
                        <p className="text-xs text-gray-400">{user.email}</p>
                      </div>
                      <button
                        onClick={() => navigate('/settings')}
                        className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-white/10 transition-colors text-left"
                      >
                        <Settings size={16} className="text-gray-400" />
                        <span className="text-sm text-gray-300">Settings</span>
                      </button>
                      <button
                        onClick={handleLogout}
                        className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-red-500/10 transition-colors text-left text-red-400"
                      >
                        <LogOut size={16} />
                        <span className="text-sm">Logout</span>
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Sub-navigation */}
      <div className="px-6 py-2 border-t border-secondary-700/30 bg-dark-500/50">
        <div className="flex items-center gap-6 text-sm">
          <button className="text-primary-400 font-medium border-b-2 border-primary-400 pb-1">
            Dashboard
          </button>
          <button className="text-gray-400 hover:text-white transition-colors pb-1">
            Cameras
          </button>
          <button className="text-gray-400 hover:text-white transition-colors pb-1">
            Recordings
          </button>
          <button className="text-gray-400 hover:text-white transition-colors pb-1">
            Analytics
          </button>
        </div>
      </div>
    </nav>
  );
}