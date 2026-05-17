// Login Page - Modern & Clean

import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, Lock, Mic, ArrowRight, Loader2 } from 'lucide-react';
import Button from '../components/Button/Button';

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    // Simulate login
    setTimeout(() => {
      if (email && password) {
        navigate('/');
      } else {
        setError('Please enter email and password');
        setLoading(false);
      }
    }, 1000);
  };

  return (
    <div className="min-h-screen bg-dark-bg flex items-center justify-center p-4 relative overflow-hidden">
      {/* Animated Background */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl animate-pulse-slow"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-success/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }}></div>
      </div>

      {/* Login Card */}
      <div className="relative w-full max-w-md">
        <div className="bg-dark-surface border-2 border-dark-border rounded-2xl p-8 shadow-modern-xl animate-scale-in">
          {/* Logo & Title */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-primary-dark text-white shadow-glow-primary mb-4 animate-float">
              <Mic className="w-8 h-8" />
            </div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-dark-text-primary via-primary-light to-primary bg-clip-text text-transparent mb-2">
              Outvox
            </h1>
            <p className="text-sm text-dark-text-muted">
              Sign in to your account
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-6 p-3 bg-danger/10 border border-danger/30 rounded-lg animate-shake">
              <p className="text-sm text-danger-light text-center">{error}</p>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleLogin} className="space-y-5">
            {/* Email */}
            <div>
              <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-text-muted" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@outvox.dev"
                  className="w-full pl-11 pr-4 py-3 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary placeholder-dark-text-muted font-medium transition-all outline-none"
                  required
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-text-muted" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full pl-11 pr-4 py-3 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary placeholder-dark-text-muted font-medium transition-all outline-none"
                  required
                />
              </div>
            </div>

            {/* Remember & Forgot */}
            <div className="flex items-center justify-between">
              <label className="flex items-center cursor-pointer group">
                <input
                  type="checkbox"
                  className="w-4 h-4 rounded border-2 border-dark-border checked:bg-primary checked:border-primary transition-all cursor-pointer"
                />
                <span className="ml-2 text-sm text-dark-text-muted group-hover:text-dark-text-primary transition-colors">
                  Remember me
                </span>
              </label>
              <a href="#" className="text-sm font-semibold text-primary-light hover:text-primary transition-colors">
                Forgot password?
              </a>
            </div>

            {/* Login Button */}
            <Button
              type="submit"
              variant="primary"
              className="w-full"
              isLoading={loading}
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Signing in...
                </>
              ) : (
                <>
                  Sign In
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </Button>
          </form>

          {/* Divider */}
          <div className="my-6 flex items-center gap-4">
            <div className="flex-1 h-px bg-dark-border"></div>
            <span className="text-xs font-medium text-dark-text-muted uppercase">Or</span>
            <div className="flex-1 h-px bg-dark-border"></div>
          </div>

          {/* Sign Up Link */}
          <div className="text-center">
            <p className="text-sm text-dark-text-muted">
              Don't have an account?{' '}
              <Link
                to="/signup"
                className="font-semibold text-primary-light hover:text-primary transition-colors"
              >
                Sign up
              </Link>
            </p>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-dark-text-muted mt-6">
          © 2026 Outvox contributors · Apache-2.0
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
