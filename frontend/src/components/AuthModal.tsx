import React, { useState } from 'react';
import { X, Lock, Mail, User as UserIcon, Shield, AlertCircle, ArrowRight, CheckCircle2, Eye, EyeOff, KeyRound, ArrowLeft } from 'lucide-react';
import { apiService } from '../services/api';
import { User } from '../types';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (user: User) => void;
  initialMode?: 'login' | 'register';
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  initialMode = 'login',
}) => {
  const [mode, setMode] = useState<'login' | 'register' | 'forgot-password'>(initialMode);
  
  // Login fields
  const [loginIdentifier, setLoginIdentifier] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [showLoginPassword, setShowLoginPassword] = useState(false);

  // Register fields
  const [regUsername, setRegUsername] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regFullName, setRegFullName] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirmPassword, setRegConfirmPassword] = useState('');
  const [showRegPassword, setShowRegPassword] = useState(false);
  const [showRegConfirmPassword, setShowRegConfirmPassword] = useState(false);

  // Forgot password fields
  const [forgotIdentifier, setForgotIdentifier] = useState('');
  const [forgotNewPassword, setForgotNewPassword] = useState('');
  const [forgotConfirmPassword, setForgotConfirmPassword] = useState('');
  const [showForgotNewPassword, setShowForgotNewPassword] = useState(false);
  const [showForgotConfirmPassword, setShowForgotConfirmPassword] = useState(false);

  // Status
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const resetForm = () => {
    setError(null);
    setSuccessMessage(null);
    setShowLoginPassword(false);
    setShowRegPassword(false);
    setShowRegConfirmPassword(false);
    setShowForgotNewPassword(false);
    setShowForgotConfirmPassword(false);
    setForgotNewPassword('');
    setForgotConfirmPassword('');
  };

  const switchMode = (newMode: 'login' | 'register' | 'forgot-password') => {
    resetForm();
    setMode(newMode);
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginIdentifier.trim() || !loginPassword) {
      setError('Please provide your username/email and password.');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const response = await apiService.login({
        username_or_email: loginIdentifier.trim(),
        password: loginPassword,
      });
      setSuccessMessage('Authentication successful!');
      setTimeout(() => {
        onSuccess(response.user);
        onClose();
        resetForm();
      }, 500);
    } catch (err: any) {
      setError(err.message || 'Invalid username and email id');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regUsername.trim() || !regEmail.trim() || !regPassword) {
      setError('Please fill in all required fields.');
      return;
    }

    if (regPassword.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    if (regPassword !== regConfirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const response = await apiService.register({
        username: regUsername.trim(),
        email: regEmail.trim(),
        password: regPassword,
        full_name: regFullName.trim() || undefined,
      });
      setSuccessMessage('Account created successfully!');
      setTimeout(() => {
        onSuccess(response.user);
        onClose();
        resetForm();
      }, 600);
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please check your details.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!forgotIdentifier.trim()) {
      setError('Please provide your username or email address.');
      return;
    }

    if (!forgotNewPassword) {
      setError('Please enter a new password.');
      return;
    }

    if (forgotNewPassword.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    if (forgotNewPassword !== forgotConfirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const res = await apiService.resetPassword({
        email_or_username: forgotIdentifier.trim(),
        new_password: forgotNewPassword,
      });
      setSuccessMessage(res.message || 'Password reset successfully!');
      setLoginIdentifier(forgotIdentifier.trim());
      setLoginPassword('');
      setTimeout(() => {
        switchMode('login');
        setSuccessMessage('Password reset successfully! You can now sign in with your new password.');
      }, 1200);
    } catch (err: any) {
      setError(err.message || 'Failed to reset password. Please check your username/email.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="relative w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl shadow-black/80 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Header Glow */}
        <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-indigo-500 via-cyan-500 to-indigo-500" />

        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4">
          <div className="flex items-center space-x-2">
            <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white tracking-tight">
                {mode === 'login' ? 'Sign In' : 'Create Account'}
              </h3>
              <p className="text-xs text-slate-400">
                {mode === 'login' ? 'Access your career intelligence workspace' : 'Get started with isolated career analytics'}
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              resetForm();
              onClose();
            }}
            aria-label="Close modal"
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Switcher */}
        {mode !== 'forgot-password' ? (
          <div className="px-6 pb-2">
            <div className="grid grid-cols-2 p-1 bg-slate-950/70 border border-slate-800/80 rounded-xl text-xs font-semibold">
              <button
                type="button"
                onClick={() => switchMode('login')}
                className={`py-2 rounded-lg transition-all cursor-pointer ${
                  mode === 'login'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => switchMode('register')}
                className={`py-2 rounded-lg transition-all cursor-pointer ${
                  mode === 'register'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Register
              </button>
            </div>
          </div>
        ) : (
          <div className="px-6 pb-2">
            <button
              type="button"
              onClick={() => switchMode('login')}
              className="flex items-center space-x-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-medium transition-colors cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Sign In</span>
            </button>
          </div>
        )}

        {/* Alert / Error / Success notification */}
        <div className="px-6 pt-2">
          {error && (
            <div className="flex items-start space-x-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-xs animate-in fade-in">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-red-400" />
              <span>{error}</span>
            </div>
          )}
          {successMessage && (
            <div className="flex items-start space-x-2 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs animate-in fade-in">
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-emerald-400" />
              <span>{successMessage}</span>
            </div>
          )}
        </div>

        {/* Form Body */}
        {mode === 'login' ? (
          <form onSubmit={handleLogin} className="p-6 space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Username or Email
              </label>
              <div className="relative">
                <input
                  type="text"
                  required
                  value={loginIdentifier}
                  onChange={(e) => setLoginIdentifier(e.target.value)}
                  placeholder="demo_user or name@example.com"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all pl-10"
                />
                <UserIcon className="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-medium text-slate-300">
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => {
                    setForgotIdentifier(loginIdentifier);
                    switchMode('forgot-password');
                  }}
                  className="text-[11px] text-indigo-400 hover:text-indigo-300 font-medium transition-colors cursor-pointer"
                >
                  Forgot Password?
                </button>
              </div>
              <div className="relative">
                <input
                  type={showLoginPassword ? "text" : "password"}
                  required
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all pl-10 pr-10"
                />
                <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" />
                <button
                  type="button"
                  onClick={() => setShowLoginPassword((prev) => !prev)}
                  className="absolute right-3.5 top-3 text-slate-400 hover:text-slate-200 transition-colors p-0.5 rounded cursor-pointer"
                  aria-label={showLoginPassword ? "Hide password" : "Show password"}
                  title={showLoginPassword ? "Hide password" : "Show password"}
                >
                  {showLoginPassword ? (
                    <EyeOff className="w-4 h-4 text-indigo-400" />
                  ) : (
                    <Eye className="w-4 h-4 text-slate-400 hover:text-slate-200" />
                  )}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-semibold text-sm shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer mt-2"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        ) : mode === 'register' ? (
          <form onSubmit={handleRegister} className="p-6 space-y-3.5">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Username <span className="text-indigo-400">*</span>
              </label>
              <div className="relative">
                <input
                  type="text"
                  required
                  value={regUsername}
                  onChange={(e) => setRegUsername(e.target.value)}
                  placeholder="alex_dev"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all pl-10"
                />
                <UserIcon className="w-4 h-4 text-slate-500 absolute left-3.5 top-2.5" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Email Address <span className="text-indigo-400">*</span>
              </label>
              <div className="relative">
                <input
                  type="email"
                  required
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                  placeholder="alex@example.com"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all pl-10"
                />
                <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-2.5" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Full Name (Optional)
              </label>
              <input
                type="text"
                value={regFullName}
                onChange={(e) => setRegFullName(e.target.value)}
                placeholder="Alex Mercer"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Password <span className="text-indigo-400">*</span>
                </label>
                <div className="relative">
                  <input
                    type={showRegPassword ? "text" : "password"}
                    required
                    value={regPassword}
                    onChange={(e) => setRegPassword(e.target.value)}
                    placeholder="min. 8 chars"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-3 pr-8 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowRegPassword((prev) => !prev)}
                    className="absolute right-2 top-2.5 text-slate-400 hover:text-slate-200 transition-colors p-0.5 rounded cursor-pointer"
                    aria-label={showRegPassword ? "Hide password" : "Show password"}
                    title={showRegPassword ? "Hide password" : "Show password"}
                  >
                    {showRegPassword ? (
                      <EyeOff className="w-3.5 h-3.5 text-indigo-400" />
                    ) : (
                      <Eye className="w-3.5 h-3.5 text-slate-400 hover:text-slate-200" />
                    )}
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Confirm <span className="text-indigo-400">*</span>
                </label>
                <div className="relative">
                  <input
                    type={showRegConfirmPassword ? "text" : "password"}
                    required
                    value={regConfirmPassword}
                    onChange={(e) => setRegConfirmPassword(e.target.value)}
                    placeholder="repeat password"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-3 pr-8 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowRegConfirmPassword((prev) => !prev)}
                    className="absolute right-2 top-2.5 text-slate-400 hover:text-slate-200 transition-colors p-0.5 rounded cursor-pointer"
                    aria-label={showRegConfirmPassword ? "Hide password" : "Show password"}
                    title={showRegConfirmPassword ? "Hide password" : "Show password"}
                  >
                    {showRegConfirmPassword ? (
                      <EyeOff className="w-3.5 h-3.5 text-indigo-400" />
                    ) : (
                      <Eye className="w-3.5 h-3.5 text-slate-400 hover:text-slate-200" />
                    )}
                  </button>
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-semibold text-sm shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer mt-3"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <span>Create Account</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        ) : (
          <form onSubmit={handleResetPassword} className="p-6 space-y-3.5">
            <div className="text-center pb-1">
              <div className="w-9 h-9 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center mx-auto mb-2 border border-indigo-500/20">
                <KeyRound className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-semibold text-white">Reset Forgotten Password</h3>
              <p className="text-[11px] text-slate-400 mt-0.5">Enter your username or email and choose your new password.</p>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Username or Email ID <span className="text-indigo-400">*</span>
              </label>
              <div className="relative">
                <input
                  type="text"
                  required
                  value={forgotIdentifier}
                  onChange={(e) => setForgotIdentifier(e.target.value)}
                  placeholder="demo_user or name@example.com"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all pl-10"
                />
                <UserIcon className="w-4 h-4 text-slate-500 absolute left-3.5 top-2.5" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                New Password <span className="text-indigo-400">*</span>
              </label>
              <div className="relative">
                <input
                  type={showForgotNewPassword ? "text" : "password"}
                  required
                  value={forgotNewPassword}
                  onChange={(e) => setForgotNewPassword(e.target.value)}
                  placeholder="min. 8 characters"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 pr-10 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all pl-10"
                />
                <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-2.5" />
                <button
                  type="button"
                  onClick={() => setShowForgotNewPassword((prev) => !prev)}
                  className="absolute right-3 top-2 text-slate-400 hover:text-slate-200 transition-colors p-0.5 rounded cursor-pointer"
                  aria-label={showForgotNewPassword ? "Hide password" : "Show password"}
                  title={showForgotNewPassword ? "Hide password" : "Show password"}
                >
                  {showForgotNewPassword ? (
                    <EyeOff className="w-4 h-4 text-indigo-400" />
                  ) : (
                    <Eye className="w-4 h-4 text-slate-400 hover:text-slate-200" />
                  )}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Confirm New Password <span className="text-indigo-400">*</span>
              </label>
              <div className="relative">
                <input
                  type={showForgotConfirmPassword ? "text" : "password"}
                  required
                  value={forgotConfirmPassword}
                  onChange={(e) => setForgotConfirmPassword(e.target.value)}
                  placeholder="repeat new password"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 pr-10 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all pl-10"
                />
                <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-2.5" />
                <button
                  type="button"
                  onClick={() => setShowForgotConfirmPassword((prev) => !prev)}
                  className="absolute right-3 top-2 text-slate-400 hover:text-slate-200 transition-colors p-0.5 rounded cursor-pointer"
                  aria-label={showForgotConfirmPassword ? "Hide password" : "Show password"}
                  title={showForgotConfirmPassword ? "Hide password" : "Show password"}
                >
                  {showForgotConfirmPassword ? (
                    <EyeOff className="w-4 h-4 text-indigo-400" />
                  ) : (
                    <Eye className="w-4 h-4 text-slate-400 hover:text-slate-200" />
                  )}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-semibold text-sm shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer mt-3"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <span>Reset Password</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        )}

        {/* Footer info */}
        <div className="px-6 py-3.5 bg-slate-950/80 border-t border-slate-800/60 text-center text-[11px] text-slate-400">
          Secured with salted bcrypt password hashing and token session revocation.
        </div>
      </div>
    </div>
  );
};
