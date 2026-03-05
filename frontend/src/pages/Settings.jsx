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

  const [passwordData, setPasswordData] = useState({
    old_password: '',
    new_password: '',
    confirm_password: '',
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
    const { name, value } = e.target;
    if (name.includes('password')) {
      setPasswordData({
        ...passwordData,
        [name]: value,
      });
    } else {
      setProfileData({
        ...profileData,
        [name]: value,
      });
    }
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

  // Handle Password Change
  const handleChangePassword = async () => {
    // Validate form
    if (!passwordData.old_password || !passwordData.new_password || !passwordData.confirm_password) {
      toast.error('Please fill in all password fields');
      return;
    }

    if (passwordData.new_password !== passwordData.confirm_password) {
      toast.error('New passwords do not match');
      return;
    }

    if (passwordData.new_password.length < 8) {
      toast.error('New password must be at least 8 characters long');
      return;
    }

    if (passwordData.old_password === passwordData.new_password) {
      toast.error('New password cannot be the same as old password');
      return;
    }

    try {
      setLoading(true);

      await axios.post(
        'http://localhost:8000/api/users/change-password',
        {
          old_password: passwordData.old_password,
          new_password: passwordData.new_password,
        },
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`,
          },
        }
      );

      // Clear password fields
      setPasswordData({
        old_password: '',
        new_password: '',
        confirm_password: '',
      });

      toast.success('Password changed successfully!');
    } catch (error) {
      console.error(error);
      if (error.response?.status === 401) {
        toast.error('Old password is incorrect');
      } else {
        toast.error('Failed to change password');
      }
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
                <div className="max-w-md">
                  <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 mb-6">
                    <p className="text-blue-300 text-sm">
                      🔒 Keep your account secure by regularly updating your password.
                    </p>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Current Password
                      </label>
                      <input
                        type="password"
                        name="old_password"
                        value={passwordData.old_password}
                        onChange={handleChange}
                        placeholder="Enter your current password"
                        className="input-field"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        New Password
                      </label>
                      <input
                        type="password"
                        name="new_password"
                        value={passwordData.new_password}
                        onChange={handleChange}
                        placeholder="Enter new password (min 8 characters)"
                        className="input-field"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Confirm New Password
                      </label>
                      <input
                        type="password"
                        name="confirm_password"
                        value={passwordData.confirm_password}
                        onChange={handleChange}
                        placeholder="Confirm your new password"
                        className="input-field"
                      />
                    </div>

                    <button
                      onClick={handleChangePassword}
                      className="btn-primary w-full"
                      disabled={loading}
                    >
                      {loading ? 'Changing Password...' : 'Change Password'}
                    </button>
                  </div>
                </div>
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