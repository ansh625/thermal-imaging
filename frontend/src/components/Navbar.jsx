import { useAuthStore } from '../store/authStore';
import { useNavigate } from 'react-router-dom';
import { LogOut, User } from 'lucide-react';

export default function Navbar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="bg-secondary border-b border-gray-700 px-6 py-4">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
            <span className="text-xl font-bold">TS</span>
          </div>
          <h1 className="text-xl font-bold text-primary">ThermalStream Polaris</h1>
        </div>
        
        {user && (
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <User size={20} />
              <span>{user.full_name || user.email}</span>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg transition"
            >
              <LogOut size={18} />
              Logout
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}