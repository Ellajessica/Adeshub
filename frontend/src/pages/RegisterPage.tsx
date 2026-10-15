import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Lock, Mail, User as UserIcon, Phone, ArrowRight, AlertCircle, CheckCircle } from 'lucide-react';
import { ApiError } from '../services/api';
import './AuthPages.css';

export const RegisterPage: React.FC = () => {
  const { register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    firstName: '',
    lastName: '',
    phoneNumber: '',
  });

  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const from = (location.state as { from?: string })?.from || '/account';

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));

    if (fieldErrors[name]) {
      setFieldErrors((prev) => {
        const updated = { ...prev };
        delete updated[name];
        return updated;
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;

    setError(null);
    setFieldErrors({});
    setSuccessMessage(null);

    const newFieldErrors: Record<string, string> = {};
    if (!formData.email.trim()) newFieldErrors.email = 'Email address is required.';
    if (!formData.password) newFieldErrors.password = 'Password is required.';
    if (!formData.confirmPassword) newFieldErrors.confirmPassword = 'Password confirmation is required.';

    if (Object.keys(newFieldErrors).length > 0) {
      setFieldErrors(newFieldErrors);
      setError('Please fill in all required fields.');
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setFieldErrors({
        password: 'Passwords do not match.',
        confirmPassword: 'Passwords do not match.',
      });
      setError('Passwords do not match.');
      return;
    }

    if (formData.password.length < 8) {
      setFieldErrors({ password: 'Password must be at least 8 characters long.' });
      setError('Password must be at least 8 characters long.');
      return;
    }

    setIsSubmitting(true);

    try {
      await register({
        email: formData.email.trim(),
        password: formData.password,
        password_confirm: formData.confirmPassword,
        first_name: formData.firstName.trim(),
        last_name: formData.lastName.trim(),
        phone_number: formData.phoneNumber.trim(),
      });
      setSuccessMessage('Account created successfully! Redirecting...');
      setTimeout(() => {
        navigate(from, { replace: true });
      }, 1000);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.fieldErrors) {
          const mapped: Record<string, string> = {};
          if (err.fieldErrors.email) mapped.email = err.fieldErrors.email;
          if (err.fieldErrors.password) mapped.password = err.fieldErrors.password;
          if (err.fieldErrors.password_confirm) mapped.confirmPassword = err.fieldErrors.password_confirm;
          if (err.fieldErrors.first_name) mapped.firstName = err.fieldErrors.first_name;
          if (err.fieldErrors.last_name) mapped.lastName = err.fieldErrors.last_name;
          if (err.fieldErrors.phone_number) mapped.phoneNumber = err.fieldErrors.phone_number;
          setFieldErrors(mapped);
        }
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Registration failed. Please check your details and try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-page-container">
      <div className="auth-card">
        <div className="auth-header">
          <h2>Create an AdesHub Account</h2>
          <p>Join AdesHub for fast UK delivery, order tracking, and address management.</p>
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
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="firstName">First Name</label>
              <div className="input-wrapper">
                <UserIcon className="input-icon" size={18} />
                <input
                  id="firstName"
                  name="firstName"
                  type="text"
                  value={formData.firstName}
                  onChange={handleChange}
                  placeholder="John"
                  disabled={isSubmitting}
                  className={fieldErrors.firstName ? 'input-invalid' : ''}
                />
              </div>
              {fieldErrors.firstName && <span className="field-error-message">{fieldErrors.firstName}</span>}
            </div>

            <div className="form-group">
              <label htmlFor="lastName">Last Name</label>
              <div className="input-wrapper">
                <UserIcon className="input-icon" size={18} />
                <input
                  id="lastName"
                  name="lastName"
                  type="text"
                  value={formData.lastName}
                  onChange={handleChange}
                  placeholder="Doe"
                  disabled={isSubmitting}
                  className={fieldErrors.lastName ? 'input-invalid' : ''}
                />
              </div>
              {fieldErrors.lastName && <span className="field-error-message">{fieldErrors.lastName}</span>}
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="email">Email Address *</label>
            <div className="input-wrapper">
              <Mail className="input-icon" size={18} />
              <input
                id="email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="name@example.com"
                required
                disabled={isSubmitting}
                className={fieldErrors.email ? 'input-invalid' : ''}
              />
            </div>
            {fieldErrors.email && <span className="field-error-message">{fieldErrors.email}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="phoneNumber">Phone Number</label>
            <div className="input-wrapper">
              <Phone className="input-icon" size={18} />
              <input
                id="phoneNumber"
                name="phoneNumber"
                type="tel"
                value={formData.phoneNumber}
                onChange={handleChange}
                placeholder="Enter your phone number"
                disabled={isSubmitting}
                className={fieldErrors.phoneNumber ? 'input-invalid' : ''}
              />
            </div>
            {fieldErrors.phoneNumber && <span className="field-error-message">{fieldErrors.phoneNumber}</span>}
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="password">Password *</label>
              <div className="input-wrapper">
                <Lock className="input-icon" size={18} />
                <input
                  id="password"
                  name="password"
                  type="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="At least 8 characters"
                  required
                  disabled={isSubmitting}
                  className={fieldErrors.password ? 'input-invalid' : ''}
                />
              </div>
              {fieldErrors.password && <span className="field-error-message">{fieldErrors.password}</span>}
            </div>

            <div className="form-group">
              <label htmlFor="confirmPassword">Confirm Password *</label>
              <div className="input-wrapper">
                <Lock className="input-icon" size={18} />
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder="Re-enter your password"
                  required
                  disabled={isSubmitting}
                  className={fieldErrors.confirmPassword ? 'input-invalid' : ''}
                />
              </div>
              {fieldErrors.confirmPassword && <span className="field-error-message">{fieldErrors.confirmPassword}</span>}
            </div>
          </div>

          <button type="submit" className="auth-submit-btn" disabled={isSubmitting}>
            {isSubmitting ? (
              <span className="spinner-inline">Creating Account...</span>
            ) : (
              <>
                <span>Register Account</span>
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        <div className="auth-footer">
          <p>
            Already have an account?{' '}
            <Link to="/login" state={{ from }}>
              Sign In Here
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};
