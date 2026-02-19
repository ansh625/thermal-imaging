import { useState } from 'react';
import { Link } from 'react-router-dom';
import { authAPI } from '../services/api';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';
import { Mail, ArrowLeft, CheckCircle, Copy, Code } from 'lucide-react';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [useDirectCode, setUseDirectCode] = useState(false);
  const [resetToken, setResetToken] = useState(null);
  const [emailSent, setEmailSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (useDirectCode) {
        // Direct code method - get reset token without email
        console.log('Requesting reset code for:', email);
        const response = await authAPI.getResetCode(email);
        console.log('Reset code response:', response);
        
        const data = response.data || response;
        console.log('Reset code data:', data);
        
        if (data.reset_token) {
          console.log('✓ Reset token received successfully');
          setResetToken(data.reset_token);
          setEmailSent(false);
          toast.success('Reset code generated! See below.');
        } else {
          console.log('✗ No reset token in response');
          const errorMsg = data.message || 'Could not generate reset code';
          console.log('Error message:', errorMsg);
          toast.error(errorMsg);
        }
      } else {
        // Email method
        console.log('Sending forgot password email for:', email);
        const response = await authAPI.forgotPassword(email);
        console.log('Forgot password response:', response);
        
        const data = response.data || response;
        console.log('Forgot password data:', data);
        
        if (data.success || data.success === undefined) {
          setEmailSent(true);
          setSent(true);
          toast.success('Reset link sent to your email!');
        } else {
          // Email failed but token was generated - offer direct code option
          toast.error('Email sending failed. Use the reset code option below.');
          setUseDirectCode(true);
          // Try to get the code directly
          try {
            const codeResponse = await authAPI.getResetCode(email);
            const codeData = codeResponse.data || codeResponse;
            if (codeData.reset_token) {
              setResetToken(codeData.reset_token);
              setEmailSent(false);
            }
          } catch (err) {
            console.error('Failed to get reset code:', err);
          }
        }
      }
    } catch (error) {
      console.error('Error:', error);
      let errorMsg = 'Failed to process request';
      
      if (error.response?.data?.message) {
        errorMsg = error.response.data.message;
      } else if (error.response?.data?.detail) {
        errorMsg = error.response.data.detail;
      } else if (error.message) {
        errorMsg = error.message;
      }
      
      console.log('Final error message:', errorMsg);
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Reset token copied to clipboard!');
  };

  // Email method success screen
  if (sent && emailSent && !resetToken) {
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
          <h2 className="text-2xl font-bold text-white mb-3">Check Your Email</h2>
          <p className="text-gray-300 mb-6">
            We've sent a password reset link to <strong>{email}</strong>
          </p>
          <p className="text-sm text-gray-400 mb-6">
            The link will expire in 1 hour. Didn't receive it? Check your spam folder.
          </p>
          <div className="space-y-3">
            <button
              onClick={() => {
                setSent(false);
                setEmailSent(false);
              }}
              className="btn-secondary w-full"
            >
              Try Another Method
            </button>
            <Link to="/login" className="block">
              <button className="btn-primary w-full">
                Back to Login
              </button>
            </Link>
          </div>
        </motion.div>
      </div>
    );
  }

  // Direct code method success screen
  if (resetToken) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-dark-500 via-secondary-900 to-dark-600 p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="glass-dark rounded-2xl p-8 w-full max-w-md text-center border border-white/10"
        >
          <div className="w-20 h-20 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <Code size={40} className="text-blue-500" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-3">Your Reset Token</h2>
          <p className="text-gray-400 mb-6">
            Use this token to reset your password. It expires in 1 hour.
          </p>
          
          <div className="bg-dark-400 border border-blue-500/30 rounded-lg p-4 mb-6 font-mono text-sm break-all">
            <p className="text-gray-300">{resetToken}</p>
          </div>

          <button
            onClick={() => copyToClipboard(resetToken)}
            className="flex items-center justify-center gap-2 w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors mb-4"
          >
            <Copy size={18} />
            Copy Token
          </button>

          <p className="text-xs text-gray-500 mb-6">
            Go to <Link to="/reset-password" className="text-blue-400 hover:underline">Reset Password</Link> page and paste this token
          </p>

          <Link to="/login">
            <button className="btn-primary w-full">
              Back to Login
            </button>
          </Link>
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
          <ArrowLeft size={18} />
          <span className="text-sm">Back to login</span>
        </Link>

        <div className="mb-8">
          <h2 className="text-3xl font-display font-bold text-white mb-2">
            Forgot Password?
          </h2>
          <p className="text-gray-400">
            {useDirectCode 
              ? "Get a temporary reset code (if email is not working)"
              : "Enter your email and we'll send you a reset link"}
          </p>
        </div>

        {/* Method Toggle */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setUseDirectCode(false)}
            className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
              !useDirectCode
                ? 'bg-primary-500 text-white'
                : 'bg-dark-400 text-gray-400 hover:text-white'
            }`}
          >
            <Mail size={16} />
            Email
          </button>
          <button
            onClick={() => setUseDirectCode(true)}
            className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
              useDirectCode
                ? 'bg-primary-500 text-white'
                : 'bg-dark-400 text-gray-400 hover:text-white'
            }`}
          >
            <Code size={16} />
            Code
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Email Address
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={20} />
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

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full"
          >
            {loading ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                {useDirectCode ? 'Generating...' : 'Sending...'}
              </>
            ) : (
              useDirectCode ? 'Get Reset Code' : 'Send Reset Link'
            )}
          </button>
        </form>

        <p className="text-center mt-6 text-sm text-gray-400">
          Remember your password?{' '}
          <Link to="/login" className="text-primary-400 hover:underline">
            Sign in
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
