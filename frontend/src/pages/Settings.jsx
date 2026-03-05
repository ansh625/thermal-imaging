import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import Navbar from '../components/Navbar';
import { User, Lock, Bell, Database } from 'lucide-react';
import toast from 'react-hot-toast';
import axios from 'axios';

export default function Settings() {
  const { user, setUser } = useAuthStore();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('profile');

  const [profileData, setProfileData] = useState({
    full_name: '',
    organization: '',
  });

  const [loading, setLoading] = useState(false);

  // Load user data into state when component loads
  useEffect(() => {
    if (user) {
      setProfileData({
        full_name: user.full_name || '',
        organization: user.organization || '',
      });
    }
  }, [user]);

  // Handle input change
  const handleChange = (e) => {
    setProfileData({
      ...profileData,
      [e.target.name]: e.target.value,
    });
  };

  // Save Profile Changes
  const handleSaveProfile = async () => {
    try {
      setLoading(true);

      const response = await axios.put(
        'http://localhost:8000/api/users/update-profile',
        profileData,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`,
          },
        }
      );

      // Update Zustand store
      setUser(response.data);

      toast.success('Profile updated successfully!');
    } catch (error) {
      console.error(error);
      toast.error('Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-dark-500">
      <Navbar />

      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-white mb-2">Settings</h1>
          <p className="text-gray-400">Manage your account and preferences</p>
        </div>

        <div className="grid grid-cols-4 gap-6">
          {/* Sidebar */}
          <div className="glass-dark rounded-xl p-4 border border-white/10 h-fit">
            <nav className="space-y-2">
              {[
                { id: 'profile', label: 'Profile', icon: User },
                { id: 'security', label: 'Security', icon: Lock },
                { id: 'notifications', label: 'Notifications', icon: Bell },
                { id: 'storage', label: 'Storage', icon: Database },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                    activeTab === tab.id
                      ? 'bg-primary-500 text-white'
                      : 'text-gray-400 hover:bg-white/10 hover:text-white'
                  }`}
                >
                  <tab.icon size={18} />
                  <span className="font-medium">{tab.label}</span>
                </button>
              ))}
            </nav>
          </div>

          {/* Content */}
          <div className="col-span-3 glass-dark rounded-xl p-6 border border-white/10">
            {activeTab === 'profile' && (
              <div>
                <h2 className="text-xl font-semibold text-white mb-6">
                  Profile Information
                </h2>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Full Name
                    </label>
                    <input
                      type="text"
                      name="full_name"
                      value={profileData.full_name}
                      onChange={handleChange}
                      className="input-field"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Email
                    </label>
                    <input
                      type="email"
                      value={user?.email}
                      className="input-field"
                      disabled
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Organization
                    </label>
                    <input
                      type="text"
                      name="organization"
                      value={profileData.organization}
                      onChange={handleChange}
                      className="input-field"
                    />
                  </div>

                  <button
                    onClick={handleSaveProfile}
                    className="btn-primary"
                    disabled={loading}
                  >
                    {loading ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </div>
            )}

            {activeTab === 'security' && (
              <div>
                <h2 className="text-xl font-semibold text-white mb-6">
                  Security Settings
                </h2>
                <p className="text-gray-400">Coming soon...</p>
              </div>
            )}

            {activeTab === 'notifications' && (
              <div>
                <h2 className="text-xl font-semibold text-white mb-6">
                  Notification Preferences
                </h2>
                <p className="text-gray-400">Coming soon...</p>
              </div>
            )}

            {activeTab === 'storage' && (
              <div>
                <h2 className="text-xl font-semibold text-white mb-6">
                  Storage Management
                </h2>
                <p className="text-gray-400">Coming soon...</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}