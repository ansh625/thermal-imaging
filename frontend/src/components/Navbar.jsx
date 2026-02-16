import { useAuthStore } from '../store/authStore';
import { useNavigate } from 'react-router-dom';
import { Activity } from 'lucide-react';

import NotificationCenter from './NotificationCenter';
import ProfileDropdown from './ProfileDropdown';

export default function Navbar() {
  const { user } = useAuthStore();
  const navigate = useNavigate();

  return (
    <nav className="bg-gradient-to-r from-secondary-900 via-dark-500 to-secondary-900 border-b border-secondary-700/50 backdrop-blur-lg sticky top-0 z-50">
      <div className="px-6 py-3">
        <div className="flex justify-between items-center">
          
          {/* Logo & Brand */}
          <div className="flex items-center gap-4">
            <div
              className="flex items-center gap-3 group cursor-pointer"
              onClick={() => navigate('/dashboard')}
            >
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
              <NotificationCenter />
              <ProfileDropdown />
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
