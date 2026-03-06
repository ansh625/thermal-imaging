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
    <nav className="bg-gradient-to-r from-secondary-900 via-dark-500 to-secondary-900 border-b border-secondary-700/50 sticky top-0 z-50">
      
      {/* Top Section */}
      <div className="px-10 py-5">
        <div className="flex justify-between items-center">
          
          {/* Logo & Brand */}
          <div className="flex items-center gap-8">
            <div
              className="flex items-center gap-6 group cursor-pointer"
              onClick={() => navigate('/dashboard')}
            >
              {/* EXTRA BIG + TIGHT LOGO */}
              <div className="bg-white rounded-full w-32 h-32 flex items-center justify-center shadow-xl overflow-hidden transition-transform duration-300 group-hover:scale-105">
                <img
                  src="/logo.png"
                  alt="Thermal Polaris Logo"
                  className="w-30 h-30 object-contain"
                />
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
        <div className="flex items-center gap-10 text-base">
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