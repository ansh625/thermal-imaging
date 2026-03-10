import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { authAPI } from '../services/api';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';
import { Mail, Lock, ArrowRight, Eye, EyeOff, Shield } from 'lucide-react';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await authAPI.login({
        username: email,
        password,
      });

      setAuth(response.data.user, response.data.access_token);
      toast.success('Welcome back!');
      navigate('/dashboard');
    } catch (error) {
      toast.error('Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-dark-500 via-secondary-900 to-dark-600">
        <div className="absolute inset-0 opacity-30">
          <div className="absolute top-0 -left-4 w-72 h-72 bg-primary-500 rounded-full mix-blend-multiply filter blur-3xl animate-blob"></div>
          <div className="absolute top-0 -right-4 w-72 h-72 bg-accent-purple rounded-full mix-blend-multiply filter blur-3xl animate-blob animation-delay-2000"></div>
          <div className="absolute -bottom-8 left-20 w-72 h-72 bg-primary-600 rounded-full mix-blend-multiply filter blur-3xl animate-blob animation-delay-4000"></div>
        </div>
      </div>

      {/* LEFT SIDE */}
      <motion.div
        initial={{ opacity: 0, x: -50 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8 }}
        className="hidden lg:flex lg:w-1/2 relative items-center justify-center p-12"
      >
        <div className="max-w-lg z-10">

          {/* LOGO */}
          <div className="flex items-center gap-4 mb-8">
            <div className="bg-white rounded-full p-3 shadow-lg">
              <img
                src="/logo.png"
                alt="Thermal Polaris"
                className="w-16 h-16 object-contain"
              />
            </div>

            <div className="flex items-center gap-3">
              <h1 className="text-4xl font-display font-bold text-gradient">
                Thermal Polaris
              </h1>

              <span className="px-2 py-1 text-xs font-semibold bg-primary-500/20 text-primary-400 rounded-full border border-primary-500/30">
                BETA
              </span>
            </div>
          </div>

          <h2 className="text-4xl font-display font-bold text-white mb-4">
            Professional Thermal Imaging Platform
          </h2>

          <p className="text-lg text-gray-300 mb-8">
            Advanced real-time monitoring, AI-powered detection,
            and multi-camera management for modern thermal systems.
          </p>

          {/* FEATURES */}
          <div className="space-y-4">
            {[
              { icon: Shield, text: 'Enterprise-grade security' },
              { icon: Eye, text: 'Real-time AI detection' },
              { icon: ArrowRight, text: 'Multi-camera monitoring' },
            ].map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 * i }}
                className="flex items-center gap-3 text-gray-300"
              >
                <div className="w-10 h-10 rounded-lg bg-primary-500/20 flex items-center justify-center">
                  <item.icon className="text-primary-400" size={20} />
                </div>

                <span className="text-lg">{item.text}</span>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.div>

      {/* RIGHT SIDE */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md"
        >
          <div className="glass-dark rounded-2xl shadow-2xl p-8 border border-white/10">

            {/* MOBILE LOGO */}
            <div className="lg:hidden flex items-center gap-3 mb-8">
              <div className="bg-white rounded-full p-2">
                <img
                  src="/logo.png"
                  alt="Thermal Polaris"
                  className="w-10 h-10 object-contain"
                />
              </div>

              <div className="flex items-center gap-2">
                <h1 className="text-xl font-display font-bold text-gradient">
                  Thermal Polaris
                </h1>

                <span className="px-2 py-0.5 text-[10px] font-semibold bg-primary-500/20 text-primary-400 rounded-full border border-primary-500/30">
                  BETA
                </span>
              </div>
            </div>

            {/* HEADER */}
            <div className="mb-8">
              <h2 className="text-3xl font-display font-bold text-white mb-2">
                Welcome Back
              </h2>

              <p className="text-gray-400">
                Sign in to access your dashboard
              </p>
            </div>

            {/* FORM */}
            <form onSubmit={handleSubmit} className="space-y-6">

              {/* EMAIL */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Email Address
                </label>

                <div className="relative">
                  <Mail
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
                    size={20}
                  />

                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="input-field pl-11"
                    placeholder="you@example.com"
                  />
                </div>
              </div>

              {/* PASSWORD */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Password
                </label>

                <div className="relative">
                  <Lock
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
                    size={20}
                  />

                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
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
              </div>

              {/* REMEMBER */}
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    className="w-4 h-4 rounded border-gray-600 text-primary-500 focus:ring-primary-500"
                  />
                  <span className="text-sm text-gray-400">Remember me</span>
                </label>

                <Link
                  to="/forgot-password"
                  className="text-sm text-primary-400 hover:text-primary-300"
                >
                  Forgot password?
                </Link>
              </div>

              {/* SUBMIT */}
              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Signing in...
                  </>
                ) : (
                  <>
                    Sign In
                    <ArrowRight size={18} />
                  </>
                )}
              </button>
            </form>

            {/* DIVIDER */}
            <div className="relative my-8">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-white/10"></div>
              </div>

              <div className="relative flex justify-center text-sm">
                <span className="px-4 bg-secondary-900 text-gray-400">
                  New to Thermal Polaris?
                </span>
              </div>
            </div>

            {/* SIGNUP */}
            <Link to="/signup">
              <button className="btn-ghost w-full">
                Create an account
              </button>
            </Link>
          </div>

          {/* FOOTER */}
          <p className="text-center mt-6 text-sm text-gray-500">
            © 2025 Thermal Polaris. All rights reserved.
          </p>
        </motion.div>
      </div>
    </div>
  );
}