import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { User, Settings, LogOut, ChevronDown } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { useNavigate } from 'react-router-dom';

export default function ProfileDropdown() {
  const [isOpen, setIsOpen] = useState(false);
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getInitials = (name) => {
    if (!name) return 'U';
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .substring(0, 2);
  };

  return (
    <div className="relative">
      {/* Profile Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-3 px-3 py-2 hover:bg-white/10 rounded-lg transition-colors"
      >
        {/* Avatar */}
        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-glow font-semibold">
          {getInitials(user?.full_name)}
        </div>

        {/* User Info */}
        <div className="hidden md:block text-left">
          <p className="text-sm font-semibold text-white leading-tight">
            {user?.full_name || 'User'}
          </p>
          <p className="text-xs text-gray-400 leading-tight">
            {user?.email}
          </p>
        </div>

        {/* Chevron */}
        <ChevronDown
          size={16}
          className={`text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <div
              className="fixed inset-0 z-40"
              onClick={() => setIsOpen(false)}
            />

            {/* Menu */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className="absolute right-0 mt-2 w-64 bg-secondary-900 rounded-xl shadow-2xl border border-white/10 overflow-hidden z-50"
            >
              {/* User Info Section */}
              <div className="p-4 border-b border-white/10 bg-gradient-to-r from-primary-500/10 to-transparent">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-glow font-bold text-lg">
                    {getInitials(user?.full_name)}
                  </div>
                  <div className="flex-1">
                    <p className="font-semibold text-white text-sm">
                      {user?.full_name}
                    </p>
                    <p className="text-xs text-gray-400 break-all">
                      {user?.email}
                    </p>
                  </div>
                </div>
                {user?.organization && (
                  <div className="mt-2 px-2 py-1 bg-white/5 rounded text-xs text-gray-300">
                    {user.organization}
                  </div>
                )}
              </div>

              {/* Menu Items */}
              <div className="py-2">
                <button
                  onClick={() => {
                    navigate('/settings');
                    setIsOpen(false);
                  }}
                  className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-white/10 transition-colors text-left"
                >
                  <Settings size={18} className="text-gray-400" />
                  <span className="text-sm text-gray-300">Settings</span>
                </button>

                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-red-500/10 transition-colors text-left text-red-400"
                >
                  <LogOut size={18} />
                  <span className="text-sm font-medium">Logout</span>
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}