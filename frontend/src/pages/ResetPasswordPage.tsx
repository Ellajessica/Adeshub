import React, { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import {
  Lock,
  ArrowRight,
  AlertCircle,
  CheckCircle,
  Eye,
  EyeOff,
  ShieldAlert,
  Check,
  X,
  Loader2
} from 'lucide-react';
import { authApi, ApiError } from '../services/api';
import './AuthPages.css';

export const ResetPasswordPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const uid = searchParams.get('uid') || '';
  const token = searchParams.get('token') || '';

  const [isValidatingToken, setIsValidatingToken] = useState(true);
  const [tokenValid, setTokenValid] = useState<boolean | null>(null);
  const [tokenError, setTokenError] = useState<string | null>(null);

  const [newPassword, setNewPassword] = useState('');
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [isSuccess, setIsSuccess] = useState(false);

  // Validate token on component mount
  const validateToken = useCallback(async () => {
    if (!uid || !token) {
      setIsValidatingToken(false);
      setTokenValid(false);
      setTokenError('The password reset link is invalid or incomplete. Please request a new link.');
      return;
    }

    try {
      const res = await authApi.validatePasswordResetToken(uid, token);
      if (res.valid) {
        setTokenValid(true);
        setTokenError(null);
      } else {
        setTokenValid(false);
        setTokenError(res.message || 'This password reset link is invalid or has expired.');
      }
    } catch (err: unknown) {
      setTokenValid(false);
      if (err instanceof ApiError) {
        setTokenError(err.message || 'This password reset link is invalid or has expired.');
      } else if (err instanceof Error) {
        setTokenError(err.message);
      } else {
        setTokenError('Unable to verify the password reset link. It may have expired or been used already.');
      }
    } finally {
      setIsValidatingToken(false);
    }
  }, [uid, token]);

  useEffect(() => {
    validateToken();
  }, [validateToken]);

  // Real-time password criteria
  const hasMinLength = newPassword.length >= 8;
  const passwordsMatch = newPassword.length > 0 && newPassword === newPasswordConfirm;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting || !tokenValid) return;

    setError(null);
    setFieldErrors({});

    const newErrors: Record<string, string> = {};
    if (!newPassword) {
      newErrors.new_password = 'New password is required.';
    } else if (newPassword.length < 8) {
      newErrors.new_password = 'Password must be at least 8 characters long.';
    }

    if (!newPasswordConfirm) {
      newErrors.new_password_confirm = 'Please confirm your new password.';
    } else if (newPassword !== newPasswordConfirm) {
      newErrors.new_password_confirm = 'Passwords do not match.';
    }

    if (Object.keys(newErrors).length > 0) {
      setFieldErrors(newErrors);
      return;
    }

    setIsSubmitting(true);

    try {
      await authApi.confirmPasswordReset({
        uid,
        token,
        new_password: newPassword,
        new_password_confirm: newPasswordConfirm,
      });

      setIsSuccess(true);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.fieldErrors) {
          const mapped: Record<string, string> = {};
          if (err.fieldErrors.new_password) mapped.new_password = err.fieldErrors.new_password;
          if (err.fieldErrors.new_password_confirm) mapped.new_password_confirm = err.fieldErrors.new_password_confirm;
          if (err.fieldErrors.token) {
            setTokenValid(false);
            setTokenError(err.fieldErrors.token);
          }
          setFieldErrors(mapped);
        }
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to reset password. Please check your inputs and try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-page-container">
      <div className="auth-card">
        {/* 1. Token Verification Loading State */}
        {isValidatingToken && (
          <div className="auth-state-card">
            <div className="auth-state-icon loading">
              <Loader2 size={36} className="spinner-rotate" />
            </div>
            <h2 className="auth-state-title">Verifying Reset Link</h2>
            <p className="auth-state-description">
              Please wait while we securely verify your password reset credentials...
            </p>
          </div>
        )}

        {/* 2. Invalid or Expired Token State */}
        {!isValidatingToken && tokenValid === false && (
          <div className="auth-state-card">
            <div className="auth-state-icon error">
              <ShieldAlert size={36} />
            </div>
            <h2 className="auth-state-title">Reset Link Expired or Invalid</h2>
            <p className="auth-state-description">
              {tokenError || 'This password reset link is invalid or has expired. Password reset links are time-limited and can only be used once.'}
            </p>
            <div className="auth-state-actions">
              <Link to="/forgot-password" className="auth-submit-btn btn-auth-full">
                <span>Request a New Reset Link</span>
                <ArrowRight size={18} />
              </Link>
              <Link to="/login" className="forgot-password-link" style={{ marginTop: '0.5rem' }}>
                Return to Sign In
              </Link>
            </div>
          </div>
        )}

        {/* 3. Successful Reset State */}
        {!isValidatingToken && isSuccess && (
          <div className="auth-state-card">
            <div className="auth-state-icon success">
              <CheckCircle size={36} />
            </div>
            <h2 className="auth-state-title">Password Reset Successfully!</h2>
            <p className="auth-state-description">
              Your password has been securely updated. You can now sign in to your AdesHub account with your new credentials.
            </p>
            <div className="auth-state-actions">
              <button
                type="button"
                onClick={() => navigate('/login', { replace: true })}
                className="auth-submit-btn btn-auth-full"
              >
                <span>Sign In to AdesHub</span>
                <ArrowRight size={18} />
              </button>
            </div>
          </div>
        )}

        {/* 4. Active Reset Password Form */}
        {!isValidatingToken && tokenValid === true && !isSuccess && (
          <>
            <div className="auth-header">
              <h2>Reset Your Password</h2>
              <p>Create a strong, new password for your AdesHub account.</p>
            </div>

            {error && (
              <div className="auth-error-banner" role="alert">
                <AlertCircle size={20} />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="auth-form" noValidate>
              {/* New Password */}
              <div className="form-group">
                <label htmlFor="new-password">New Password</label>
                <div className="input-wrapper">
                  <Lock className="input-icon" size={18} />
                  <input
                    id="new-password"
                    type={showPassword ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(e) => {
                      setNewPassword(e.target.value);
                      if (fieldErrors.new_password) {
                        setFieldErrors((prev) => ({ ...prev, new_password: '' }));
                      }
                    }}
                    placeholder="At least 8 characters"
                    required
                    disabled={isSubmitting}
                    className={fieldErrors.new_password ? 'input-invalid' : ''}
                    autoFocus
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
                {fieldErrors.new_password && (
                  <span className="field-error-message">{fieldErrors.new_password}</span>
                )}
              </div>

              {/* Confirm Password */}
              <div className="form-group">
                <label htmlFor="confirm-password">Confirm New Password</label>
                <div className="input-wrapper">
                  <Lock className="input-icon" size={18} />
                  <input
                    id="confirm-password"
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={newPasswordConfirm}
                    onChange={(e) => {
                      setNewPasswordConfirm(e.target.value);
                      if (fieldErrors.new_password_confirm) {
                        setFieldErrors((prev) => ({ ...prev, new_password_confirm: '' }));
                      }
                    }}
                    placeholder="Re-enter your new password"
                    required
                    disabled={isSubmitting}
                    className={fieldErrors.new_password_confirm ? 'input-invalid' : ''}
                  />
                  <button
                    type="button"
                    className="password-toggle-btn"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                    tabIndex={-1}
                  >
                    {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                {fieldErrors.new_password_confirm && (
                  <span className="field-error-message">{fieldErrors.new_password_confirm}</span>
                )}
              </div>

              {/* Password Requirements Guidance Box */}
              <div className="password-requirements-card">
                <span className="password-requirements-title">
                  Password Requirements:
                </span>
                <ul className="password-requirements-list">
                  <li className={`requirement-item ${hasMinLength ? 'met' : 'unmet'}`}>
                    {hasMinLength ? <Check size={14} className="text-success" /> : <X size={14} />}
                    <span>At least 8 characters long</span>
                  </li>
                  <li className={`requirement-item ${passwordsMatch ? 'met' : 'unmet'}`}>
                    {passwordsMatch ? <Check size={14} className="text-success" /> : <X size={14} />}
                    <span>Both passwords must match</span>
                  </li>
                </ul>
              </div>

              <button
                type="submit"
                className="auth-submit-btn"
                disabled={isSubmitting || !hasMinLength || !passwordsMatch}
              >
                {isSubmitting ? (
                  <span className="spinner-inline">Updating password...</span>
                ) : (
                  <>
                    <span>Reset Password</span>
                    <ArrowRight size={18} />
                  </>
                )}
              </button>
            </form>

            <div className="auth-footer">
              <p>
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
