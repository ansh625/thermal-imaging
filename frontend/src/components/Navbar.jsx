import { useAuthStore } from '../store/authStore';
import { useNavigate, useLocation } from 'react-router-dom';
import { Activity } from 'lucide-react';

import NotificationCenter from './NotificationCenter';
import ProfileDropdown from './ProfileDropdown';

export default function Navbar() {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <nav className="bg-gradient-to-r from-secondary-900 via-dark-500 to-secondary-900 border-b border-secondary-700/50 backdrop-blur-lg sticky top-0 z-50">
      
      {/* Main Navbar */}
      <div className="px-10 py-6">
        <div className="flex justify-between items-center">
          
          {/* Logo & Brand */}
          <div className="flex items-center gap-6">
            
            <div
              className="flex items-center gap-5 group cursor-pointer"
              onClick={() => navigate('/dashboard')}
            >
              
              {/* Logo */}
              <div className="relative">
                <img
                  src="/logo.png"
                  alt="Thermal Polaris Logo"
                  className="w-20 h-20 drop-shadow-glow group-hover:scale-105 transition-transform duration-300"
                />
                <div className="absolute inset-0 bg-primary-500/20 rounded-full blur-xl group-hover:bg-primary-500/40 transition-all duration-300"></div>
              </div>

              {/* Brand Text */}
              <div className="flex flex-col">
                <h1 className="text-3xl font-display font-bold text-gradient leading-tight">
                  Thermal Polaris Beta
                </h1>
                <p className="text-base text-gray-400 font-medium">
                  AI-Powered Thermal Monitoring System
                </p>
              </div>
            </div>

            {/* Quick Status Indicator */}
            <div className="hidden md:flex items-center gap-3 ml-8 px-5 py-3 bg-dark-400/30 rounded-full border border-secondary-700/50">
              <Activity size={18} className="text-primary-400 animate-pulse" />
              <span className="text-base text-gray-300">System Active</span>
            </div>
          </div>

          {/* Right Section */}
          {user && (
            <div className="flex items-center gap-5">
              <NotificationCenter />
              <ProfileDropdown />
            </div>
          )}
        </div>
      </div>

      {/* Sub-navigation */}
      <div className="px-10 py-3 border-t border-secondary-700/30 bg-dark-500/50">
        <div className="flex items-center gap-8 text-base">
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