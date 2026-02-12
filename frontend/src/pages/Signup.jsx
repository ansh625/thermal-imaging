import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authAPI } from '../services/api';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';
import { Mail, Lock, User as UserIcon, Building, ArrowRight, Eye, EyeOff } from 'lucide-react';

export default function Signup() {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    organization: '',
  });
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await authAPI.signup(formData);
      toast.success('Account created! Please login.');
      navigate('/login');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Signup failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex relative overflow-hidden">
      {/* Animated Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-dark-500 via-secondary-900 to-dark-600">
        <div className="absolute inset-0 opacity-30">
          <div className="absolute top-0 -left-4 w-72 h-72 bg-primary-500 rounded-full mix-blend-multiply filter blur-3xl animate-blob"></div>
          <div className="absolute top-0 -right-4 w-72 h-72 bg-accent-purple rounded-full mix-blend-multiply filter blur-3xl animate-blob animation-delay-2000"></div>
          <div className="absolute -bottom-8 left-20 w-72 h-72 bg-primary-600 rounded-full mix-blend-multiply filter blur-3xl animate-blob animation-delay-4000"></div>
        </div>
      </div>

      {/* Left Side - Branding */}
      <motion.div 
        initial={{ opacity: 0, x: -50 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8 }}
        className="hidden lg:flex lg:w-1/2 relative items-center justify-center p-12"
      >
        <div className="max-w-lg z-10">
          <div className="flex items-center gap-4 mb-8">
            <img src="/logo.svg" alt="CSIO" className="w-20 h-20 drop-shadow-glow" />
            <div>
              <h1 className="text-5xl font-display font-bold text-gradient">CSIO</h1>
              <p className="text-xl text-gray-300">ThermalStream Polaris</p>
            </div>
          </div>

          <h2 className="text-4xl font-display font-bold text-white mb-4">
            Join the Future of Thermal Imaging
          </h2>
          <p className="text-lg text-gray-300 mb-8">
            Get started with CSIO ThermalStream and experience next-generation 
            thermal camera management with AI-powered insights.
          </p>

          <div className="space-y-6 bg-white/5 backdrop-blur-sm rounded-xl p-6 border border-white/10">
            <h3 className="font-semibold text-white text-lg">What you'll get:</h3>
            <ul className="space-y-3 text-gray-300">
              <li className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-primary-500/20 flex items-center justify-center mt-0.5">
                  <div className="w-2 h-2 rounded-full bg-primary-400"></div>
                </div>
                <span>Real-time multi-camera monitoring dashboard</span>
              </li>
              <li className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-primary-500/20 flex items-center justify-center mt-0.5">
                  <div className="w-2 h-2 rounded-full bg-primary-400"></div>
                </div>
                <span>AI-powered object detection and tracking</span>
              </li>
              <li className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-primary-500/20 flex items-center justify-center mt-0.5">
                  <div className="w-2 h-2 rounded-full bg-primary-400"></div>
                </div>
                <span>Cloud storage and advanced analytics</span>
              </li>
              <li className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-primary-500/20 flex items-center justify-center mt-0.5">
                  <div className="w-2 h-2 rounded-full bg-primary-400"></div>
                </div>
                <span>24/7 technical support from CSIR CSIO</span>
              </li>
            </ul>
          </div>
        </div>
      </motion.div>

      {/* Right Side - Signup Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md"
        >
          <div className="glass-dark rounded-2xl shadow-2xl p-8 border border-white/10">
            {/* Mobile Logo */}
            <div className="lg:hidden flex items-center gap-3 mb-8">
              <img src="/logo.svg" alt="CSIO" className="w-12 h-12" />
              <div>
                <h1 className="text-2xl font-display font-bold text-gradient">CSIO</h1>
                <p className="text-sm text-gray-400">ThermalStream</p>
              </div>
            </div>

            <div className="mb-8">
              <h2 className="text-3xl font-display font-bold text-white mb-2">
                Create Account
              </h2>
              <p className="text-gray-400">Get started with CSIO ThermalStream</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Full Name */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Full Name
                </label>
                <div className="relative">
                  <UserIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={20} />
                  <input
                    type="text"
                    value={formData.full_name}
                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                    required
                    className="input-field pl-11"
                    placeholder="John Doe"
                  />
                </div>
              </div>

              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={20} />
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                    className="input-field pl-11"
                    placeholder="you@example.com"
                  />
                </div>
              </div>

              {/* Organization */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Organization <span className="text-gray-500">(Optional)</span>
                </label>
                <div className="relative">
                  <Building className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={20} />
                  <input
                    type="text"
                    value={formData.organization}
                    onChange={(e) => setFormData({ ...formData, organization: e.target.value })}
                    className="input-field pl-11"
                    placeholder="CSIR CSIO"
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={20} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
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

              {/* Terms */}
              <label className="flex items-start gap-2 cursor-pointer">
                <input type="checkbox" required className="w-4 h-4 mt-0.5 rounded border-gray-600 text-primary-500 focus:ring-primary-500" />
                <span className="text-sm text-gray-400">
                  I agree to the <button type="button" className="text-primary-400 hover:underline">Terms of Service</button> and <button type="button" className="text-primary-400 hover:underline">Privacy Policy</button>
                </span>
              </label>

              {/* Submit */}
              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Creating account...
                  </>
                ) : (
                  <>
                    Create Account
                    <ArrowRight size={18} />
                  </>
                )}
              </button>
            </form>

            {/* Divider */}
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-white/10"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-4 bg-secondary-900 text-gray-400">Already have an account?</span>
              </div>
            </div>

            {/* Login Link */}
            <Link to="/login">
              <button className="btn-ghost w-full">
                Sign in instead
              </button>
            </Link>
          </div>

          {/* Footer */}
          <p className="text-center mt-6 text-sm text-gray-500">
            © 2025 CSIR CSIO. All rights reserved.
          </p>
        </motion.div>
      </div>
    </div>
  );
}