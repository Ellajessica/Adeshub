import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, ArrowRight, ArrowLeft, AlertCircle, CheckCircle, RefreshCw } from 'lucide-react';
import { authApi, ApiError } from '../services/api';
import './AuthPages.css';

export const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [submittedEmail, setSubmittedEmail] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;

    setError(null);
    setFieldError(null);

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setFieldError('Email address is required.');
      return;
    }

    // Basic email format check
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmedEmail)) {
      setFieldError('Please enter a valid email address.');
      return;
    }

    setIsSubmitting(true);

    try {
      await authApi.requestPasswordReset(trimmedEmail);
      setSubmittedEmail(trimmedEmail);
      setIsSubmitted(true);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.fieldErrors?.email) {
          setFieldError(err.fieldErrors.email);
        } else {
          setError(err.message);
        }
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred while requesting a password reset. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResetAnother = () => {
    setIsSubmitted(false);
    setEmail('');
    setError(null);
    setFieldError(null);
  };

  return (
    <div className="auth-page-container">
      <div className="auth-card">
        {isSubmitted ? (
          <div className="auth-state-card">
            <div className="auth-state-icon success">
              <CheckCircle size={36} />
            </div>
            <h2 className="auth-state-title">Check Your Inbox</h2>
            <p className="auth-state-description">
              If an account is associated with <strong>{submittedEmail}</strong>, we have sent instructions to reset your password.
              Please check your inbox and spam folder.
            </p>
            <div className="auth-state-actions">
              <Link to="/login" className="auth-submit-btn btn-auth-full">
                <ArrowLeft size={18} />
                <span>Return to Sign In</span>
              </Link>
              <button
                type="button"
                onClick={handleResetAnother}
                className="btn-link"
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#0f5132',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  padding: '0.5rem',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                }}
              >
                <RefreshCw size={14} /> Send to another email
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="auth-header">
              <h2>Forgot Your Password?</h2>
              <p>
                Enter the email address associated with your AdesHub account and we'll send you a secure link to reset your password.
              </p>
            </div>

            {error && (
              <div className="auth-error-banner" role="alert">
                <AlertCircle size={20} />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="auth-form" noValidate>
              <div className="form-group">
                <label htmlFor="reset-email">Email Address</label>
                <div className="input-wrapper">
                  <Mail className="input-icon" size={18} />
                  <input
                    id="reset-email"
                    type="email"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      if (fieldError) setFieldError(null);
                    }}
                    placeholder="name@example.com"
                    required
                    disabled={isSubmitting}
                    className={fieldError ? 'input-invalid' : ''}
                    autoFocus
                  />
                </div>
                {fieldError && <span className="field-error-message">{fieldError}</span>}
              </div>

              <button type="submit" className="auth-submit-btn" disabled={isSubmitting}>
                {isSubmitting ? (
                  <span className="spinner-inline">Sending reset link...</span>
                ) : (
                  <>
                    <span>Send Reset Link</span>
                    <ArrowRight size={18} />
                  </>
                )}
              </button>
            </form>

            <div className="auth-footer">
              <p>
                Remember your password?{' '}
                <Link to="/login">
                  Back to Sign In
                </Link>
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
