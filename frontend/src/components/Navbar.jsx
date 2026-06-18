import { useAuthStore } from '../store/authStore';
import { useNavigate, useLocation } from 'react-router-dom';

import NotificationCenter from './NotificationCenter';
import ProfileDropdown from './ProfileDropdown';

export default function Navbar() {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <nav className="bg-gradient-to-r from-secondary-900 via-dark-500 to-secondary-900 border-b border-secondary-700/50 sticky top-0 z-50">
      {/* Top Section */}
      <div className="px-8 py-3">
        <div className="flex justify-between items-center">
          {/* Logo & Brand */}
          <div className="flex items-center gap-4">
            <div
              className="flex items-center gap-4 cursor-pointer group"
              onClick={() => navigate('/dashboard')}
            >
              <div className="w-16 h-16 rounded-full bg-white flex items-center justify-center overflow-hidden shadow-md transition-transform duration-300 group-hover:scale-105">
                <img
                  src="/logo.png"
                  alt="Thermal Polaris Logo"
                  className="w-[58px] h-[58px] object-contain"
                />
              </div>

              {/* Brand */}
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-xl font-display font-bold text-gradient">
                    Thermal Polaris
                  </h1>

                  <span className="px-2 py-0.5 text-[10px] font-semibold rounded-md bg-primary-500/20 text-primary-400 border border-primary-500/30">
                    BETA
                  </span>
                </div>

                <p className="text-xs text-gray-400">
                  AI-Powered Thermal Monitoring System
                </p>
              </div>
            </div>
          </div>

          {/* Right Section */}
          {user && (
            <div className="flex items-center gap-4">
              <NotificationCenter />
              <ProfileDropdown />
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <div className="px-8 py-2 border-t border-secondary-700/30 bg-dark-500/50">
        <div className="flex items-center gap-8 text-sm">
          {[
            ['/dashboard', 'Dashboard'],
            ['/cameras', 'Cameras'],
            ['/recordings', 'Recordings'],
            ['/schedules', 'Schedules'],
            ['/analytics', 'Analytics'],
          ].map(([path, label]) => (
            <button
              key={path}
              onClick={() => navigate(path)}
              className={`font-medium pb-1 transition-colors ${
                location.pathname === path
                  ? 'text-primary-400 border-b-2 border-primary-400'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </nav>
  );
}
