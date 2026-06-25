import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { authAPI } from '../services/api';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';
import { Lock, Eye, EyeOff, CheckCircle, Copy } from 'lucide-react';

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [manualToken, setManualToken] = useState('');
  const token = searchParams.get('token') || manualToken;

  console.log('Reset Password Page Loaded');
  console.log('Token from URL:', searchParams.get('token'));
  console.log('Manual token:', manualToken);
  console.log('Final token to use:', token);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!token) {
      toast.error('Please enter or provide a valid reset token');
      return;
    }

    if (password.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }

    if (password !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      console.log('Submitting reset with token:', token);
      const response = await authAPI.resetPassword(token, password);
      console.log('Reset password response:', response);
      setSuccess(true);
      toast.success('Password reset successful!');
      setTimeout(() => navigate('/login'), 2000);
    } catch (error) {
      console.error('Reset password error:', error);
      const errorMsg = error.response?.data?.detail || error.response?.data?.message || 'Failed to reset password';
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-dark-500 via-secondary-900 to-dark-600 p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="glass-dark rounded-2xl p-8 w-full max-w-md text-center border border-white/10"
        >
          <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle size={40} className="text-green-500" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-3">Password Reset!</h2>
          <p className="text-gray-300 mb-6">
            Your password has been successfully reset. Redirecting to login...
          </p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-dark-500 via-secondary-900 to-dark-600 p-4">
      <div className="absolute inset-0 opacity-30">
        <div className="absolute top-0 -left-4 w-72 h-72 bg-primary-500 rounded-full mix-blend-multiply filter blur-3xl animate-blob"></div>
        <div className="absolute top-0 -right-4 w-72 h-72 bg-accent-purple rounded-full mix-blend-multiply filter blur-3xl animate-blob animation-delay-2000"></div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-dark rounded-2xl p-8 w-full max-w-md border border-white/10 relative z-10"
      >
        <Link to="/login" className="flex items-center gap-2 text-gray-400 hover:text-white mb-6 transition-colors">
          <span className="text-sm">← Back to login</span>
        </Link>

        <div className="mb-8">
          <h2 className="text-3xl font-display font-bold text-white mb-2">
            Reset Password
          </h2>
          <p className="text-gray-400">
            {token ? 'Enter your new password below' : 'Enter the reset token and your new password'}
          </p>
        </div>

        {/* If no token in URL, show token input field */}
        {!searchParams.get('token') && (
          <div className="mb-6 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
            <p className="text-sm text-blue-300 mb-3">
              <strong>No reset token found in URL.</strong> If you got a reset code from the app, paste it below:
            </p>
            <div className="relative">
              <input
                type="text"
                value={manualToken}
                onChange={(e) => setManualToken(e.target.value)}
                placeholder="Paste your reset token here"
                className="input-field text-sm w-full"
              />
            </div>
            <p className="text-xs text-gray-400 mt-2">
              Or go back to <Link to="/forgot-password" className="text-blue-400 hover:underline">Forgot Password</Link> to request a new one
            </p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              New Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={20} />
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                className="input-field pl-11 pr-11"
                placeholder="••••••••"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-1">Minimum 8 characters</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Confirm Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={20} />
              <input
                type={showPassword ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                className="input-field pl-11"
                placeholder="••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || !token}
            className={`w-full py-3 rounded-lg font-medium transition-all ${
              loading || !token
                ? 'bg-gray-600 text-gray-300 cursor-not-allowed'
                : 'btn-primary'
            }`}
          >
            {loading ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin inline-block mr-2"></div>
                Resetting...
              </>
            ) : (
              'Reset Password'
            )}
          </button>
        </form>

        <div className="mt-6 space-y-2 text-center">
          <p className="text-sm text-gray-400">
            Remember your password?{' '}
            <Link to="/login" className="text-primary-400 hover:underline">
              Sign in
            </Link>
          </p>
          <p className="text-sm text-gray-400">
            Don't have a reset link?{' '}
            <Link to="/forgot-password" className="text-primary-400 hover:underline">
              Request one
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
}