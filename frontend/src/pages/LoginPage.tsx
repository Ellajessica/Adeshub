import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Lock, Mail, ArrowRight, AlertCircle, CheckCircle, Eye, EyeOff } from 'lucide-react';
import { ApiError } from '../services/api';
import './AuthPages.css';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const queryRedirect = new URLSearchParams(location.search).get('redirect');
  const from = (location.state as { from?: string })?.from || queryRedirect || '/account';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;

    setError(null);
    setFieldErrors({});
    setSuccessMessage(null);

    const newFieldErrors: Record<string, string> = {};
    if (!email.trim()) newFieldErrors.email = 'Email address is required.';
    if (!password) newFieldErrors.password = 'Password is required.';

    if (Object.keys(newFieldErrors).length > 0) {
      setFieldErrors(newFieldErrors);
      setError('Please fill in both email and password.');
      return;
    }

    setIsSubmitting(true);

    try {
      await login(email.trim(), password);
      setSuccessMessage('Sign in successful! Redirecting...');
      setTimeout(() => {
        navigate(from, { replace: true });
      }, 800);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.fieldErrors) {
          const mapped: Record<string, string> = {};
          if (err.fieldErrors.email) mapped.email = err.fieldErrors.email;
          if (err.fieldErrors.password) mapped.password = err.fieldErrors.password;
          setFieldErrors(mapped);
        }
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Login failed. Please check your credentials and try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-page-container">
      <div className="auth-card">
        <div className="auth-header">
          <h2>Welcome Back to AdesHub</h2>
          <p>Sign in to your customer account to manage orders & checkout faster.</p>
        </div>

        {error && (
          <div className="auth-error-banner" role="alert">
            <AlertCircle size={20} />
            <span>{error}</span>
          </div>
        )}

        {successMessage && (
          <div className="auth-success-banner" role="status">
            <CheckCircle size={20} />
            <span>{successMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form" noValidate>
          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <div className="input-wrapper">
              <Mail className="input-icon" size={18} />
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (fieldErrors.email) {
                    setFieldErrors((prev) => ({ ...prev, email: '' }));
                  }
                }}
                placeholder="name@example.com"
                required
                disabled={isSubmitting}
                className={fieldErrors.email ? 'input-invalid' : ''}
              />
            </div>
            {fieldErrors.email && <span className="field-error-message">{fieldErrors.email}</span>}
          </div>

          <div className="form-group">
            <div className="form-label-row">
              <label htmlFor="password">Password</label>
              <Link to="/forgot-password" className="forgot-password-link">
                Forgot Password?
              </Link>
            </div>
            <div className="input-wrapper">
              <Lock className="input-icon" size={18} />
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (fieldErrors.password) {
                    setFieldErrors((prev) => ({ ...prev, password: '' }));
                  }
                }}
                placeholder="Enter your password"
                required
                disabled={isSubmitting}
                className={fieldErrors.password ? 'input-invalid' : ''}
              />
              <button
                type="button"
                className="password-toggle-btn"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {fieldErrors.password && <span className="field-error-message">{fieldErrors.password}</span>}
          </div>

          <button type="submit" className="auth-submit-btn" disabled={isSubmitting}>
            {isSubmitting ? (
              <span className="spinner-inline">Signing in...</span>
            ) : (
              <>
                <span>Sign In</span>
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        <div className="auth-footer">
          <p>
            Don't have an account yet?{' '}
            <Link to="/register" state={{ from }}>
              Create an Account
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};
