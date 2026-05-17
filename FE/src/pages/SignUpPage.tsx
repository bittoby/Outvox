// Sign Up Page - Modern & Clean

import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, Lock, User, Mic, ArrowRight, Loader2, Building } from 'lucide-react';
import Button from '../components/Button/Button';

const SignUpPage: React.FC = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    company: '',
    password: '',
    confirmPassword: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validation
    if (!formData.name || !formData.email || !formData.password) {
      setError('Please fill in all required fields');
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setLoading(true);

    // Simulate signup
    setTimeout(() => {
      navigate('/login');
    }, 1500);
  };

  return (
    <div className="min-h-screen bg-dark-bg flex items-center justify-center p-4 relative overflow-hidden">
      {/* Animated Background */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-success/10 rounded-full blur-3xl animate-pulse-slow"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }}></div>
      </div>

      {/* Sign Up Card */}
      <div className="relative w-full max-w-md">
        <div className="bg-dark-surface border-2 border-dark-border rounded-2xl p-8 shadow-modern-xl animate-scale-in">
          {/* Logo & Title */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-success to-success-dark text-white shadow-glow-success mb-4 animate-float">
              <Mic className="w-8 h-8" />
            </div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-dark-text-primary via-success-light to-success bg-clip-text text-transparent mb-2">
              Create Account
            </h1>
            <p className="text-sm text-dark-text-muted">
              Get started with Outvox today
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-6 p-3 bg-danger/10 border border-danger/30 rounded-lg animate-shake">
              <p className="text-sm text-danger-light text-center">{error}</p>
            </div>
          )}

          {/* Sign Up Form */}
          <form onSubmit={handleSignUp} className="space-y-4">
            {/* Name */}
            <div>
              <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                Full Name *
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-text-muted" />
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="John Doe"
                  className="w-full pl-11 pr-4 py-3 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary placeholder-dark-text-muted font-medium transition-all outline-none"
                  required
                />
              </div>
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                Email Address *
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-text-muted" />
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="john@company.com"
                  className="w-full pl-11 pr-4 py-3 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary placeholder-dark-text-muted font-medium transition-all outline-none"
                  required
                />
              </div>
            </div>

            {/* Company */}
            <div>
              <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                Company Name (Optional)
              </label>
              <div className="relative">
                <Building className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-text-muted" />
                <input
                  type="text"
                  value={formData.company}
                  onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                  placeholder="Acme Inc."
                  className="w-full pl-11 pr-4 py-3 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary placeholder-dark-text-muted font-medium transition-all outline-none"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                Password *
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-text-muted" />
                <input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  placeholder="At least 8 characters"
                  className="w-full pl-11 pr-4 py-3 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary placeholder-dark-text-muted font-medium transition-all outline-none"
                  required
                />
              </div>
            </div>

            {/* Confirm Password */}
            <div>
              <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                Confirm Password *
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-text-muted" />
                <input
                  type="password"
                  value={formData.confirmPassword}
                  onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                  placeholder="Re-enter password"
                  className="w-full pl-11 pr-4 py-3 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary placeholder-dark-text-muted font-medium transition-all outline-none"
                  required
                />
              </div>
            </div>

            {/* Terms */}
            <div className="pt-2">
              <label className="flex items-start cursor-pointer group">
                <input
                  type="checkbox"
                  className="mt-0.5 w-4 h-4 rounded border-2 border-dark-border checked:bg-success checked:border-success transition-all cursor-pointer"
                  required
                />
                <span className="ml-2 text-sm text-dark-text-muted group-hover:text-dark-text-primary transition-colors">
                  I agree to the{' '}
                  <a href="#" className="text-success-light hover:text-success font-semibold">
                    Terms of Service
                  </a>{' '}
                  and{' '}
                  <a href="#" className="text-success-light hover:text-success font-semibold">
                    Privacy Policy
                  </a>
                </span>
              </label>
            </div>

            {/* Sign Up Button */}
            <Button
              type="submit"
              variant="success"
              className="w-full"
              isLoading={loading}
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Creating account...
                </>
              ) : (
                <>
                  Create Account
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

          {/* Login Link */}
          <div className="text-center">
            <p className="text-sm text-dark-text-muted">
              Already have an account?{' '}
              <Link
                to="/login"
                className="font-semibold text-success-light hover:text-success transition-colors"
              >
                Sign in
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

export default SignUpPage;

