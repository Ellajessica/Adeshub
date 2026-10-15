import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { api } from '../services/api';
import type { OrderPaymentStatusResponse } from '../types/api';
import {
  CheckCircle2,
  Mail,
  Copy,
  Check,
  ArrowRight,
  ShoppingBag,
  RefreshCw,
  AlertTriangle,
  CreditCard,
  ShieldCheck,
  FileText
} from 'lucide-react';
import './OrderConfirmationPage.css';

export const OrderConfirmationPage: React.FC = () => {
  const { reference } = useParams<{ reference: string }>();
  const location = useLocation();
  const navigate = useNavigate();

  const searchParams = new URLSearchParams(location.search);
  const paymentQueryStatus = searchParams.get('payment_status'); // 'success' | 'cancelled' | null
  const sessionId = searchParams.get('session_id') || undefined;

  const { refreshCart } = useCart();

  const [paymentStatus, setPaymentStatus] = useState<OrderPaymentStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isVerifying, setIsVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const [isInitiatingPayment, setIsInitiatingPayment] = useState(false);
  const initialPaymentError = (location.state as { paymentError?: string })?.paymentError || null;
  const [paymentError, setPaymentError] = useState<string | null>(initialPaymentError);

  // Fetch payment status securely from backend
  const fetchStatus = useCallback(async (ref: string, sid?: string): Promise<OrderPaymentStatusResponse | null> => {
    try {
      const data = await api.getOrderPaymentStatus(ref, sid);
      setPaymentStatus(data);
      return data;
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Unable to load order payment status.');
      }
      return null;
    }
  }, []);

  useEffect(() => {
    // Synchronize cart state on confirmation page so navbar item count clears
    refreshCart().catch(() => {});

    if (!reference) return;

    let isMounted = true;

    const initialize = async () => {
      setIsLoading(true);
      setError(null);
      const data = await fetchStatus(reference, sessionId);
      if (!isMounted) return;
      setIsLoading(false);

      // If returning from Stripe with success query param and payment is not yet marked PAID,
      // poll the backend for up to 15 seconds to wait for webhook processing.
      if (paymentQueryStatus === 'success' && data && !data.is_paid) {
        setIsVerifying(true);
        let pollCount = 0;
        const maxPolls = 6;

        const interval = setInterval(async () => {
          pollCount += 1;
          const updated = await fetchStatus(reference, sessionId);
          if (updated?.is_paid || pollCount >= maxPolls) {
            clearInterval(interval);
            if (isMounted) setIsVerifying(false);
          }
        }, 2500);

        return () => clearInterval(interval);
      }
    };

    initialize();

    return () => {
      isMounted = false;
    };
  }, [reference, sessionId, paymentQueryStatus, fetchStatus]);

  const handleCopyReference = () => {
    if (!reference) return;
    navigator.clipboard.writeText(reference);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleManualCheckStatus = async () => {
    if (!reference) return;
    setIsVerifying(true);
    await fetchStatus(reference, sessionId);
    setIsVerifying(false);
  };

  const handlePayWithStripe = async () => {
    if (!reference) return;
    setIsInitiatingPayment(true);
    setPaymentError(null);

    try {
      const session = await api.createCheckoutSession(reference);
      if (session && session.checkout_url && session.checkout_url.startsWith('https://checkout.stripe.com/')) {
        window.location.href = session.checkout_url;
      } else {
        setPaymentError('Could not obtain a valid Stripe Checkout redirect URL. Please try again.');
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setPaymentError(err.message);
      } else {
        setPaymentError('Failed to initiate Stripe payment.');
      }
    } finally {
      setIsInitiatingPayment(false);
    }
  };

  const handleViewOrder = () => {
    if (!reference) return;
    const queryParams = new URLSearchParams();
    if (sessionId) {
      queryParams.set('session_id', sessionId);
    }
    if (paymentStatus?.customer_email) {
      queryParams.set('email', paymentStatus.customer_email);
    }
    const queryString = queryParams.toString();
    navigate(`/orders/${reference}${queryString ? `?${queryString}` : ''}`);
  };

  const handleContinueShopping = () => {
    navigate('/shop');
  };

  if (isLoading) {
    return (
      <div className="confirmation-page">
        <div className="confirmation-loading-card">
          <div className="confirmation-spinner" />
          <h2>Verifying Your Order...</h2>
          <p>Please wait while we confirm your payment details.</p>
        </div>
      </div>
    );
  }

  if (error && !paymentStatus) {
    return (
      <div className="confirmation-page">
        <div className="confirmation-card confirmation-card-error">
          <AlertTriangle size={52} className="error-icon" />
          <h2>Order Not Found</h2>
          <p>{error || 'The requested order confirmation could not be verified.'}</p>
          <div className="confirmation-actions">
            <button
              type="button"
              className="confirmation-btn-primary"
              onClick={handleContinueShopping}
            >
              Return to Shop
            </button>
          </div>
        </div>
      </div>
    );
  }

  const isPaid = paymentStatus?.is_paid;
  const isCancelled = paymentQueryStatus === 'cancelled' || paymentStatus?.is_cancelled;

  // Case 1: Cancelled checkout session
  if (isCancelled && !isPaid) {
    return (
      <div className="confirmation-page">
        <div className="confirmation-container">
          <div className="confirmation-card confirmation-card-cancelled">
            <div className="confirmation-icon-circle icon-circle-warning">
              <AlertTriangle size={36} />
            </div>
            <h1>Stripe Checkout Cancelled</h1>
            <p className="confirmation-intro">
              Your payment was cancelled. No money was charged. Your items remain reserved under order{' '}
              <strong>#{reference}</strong>.
            </p>

            {paymentError && (
              <div className="confirmation-alert-error">
                {paymentError}
              </div>
            )}

            <div className="confirmation-retry-box">
              <button
                type="button"
                className="confirmation-btn-stripe"
                onClick={handlePayWithStripe}
                disabled={isInitiatingPayment}
              >
                <CreditCard size={18} />
                {isInitiatingPayment ? 'Opening Stripe Checkout...' : 'Complete Payment with Stripe'}
              </button>
              <div className="secure-badge">
                <ShieldCheck size={14} />
                <span>Powered by Stripe Checkout • 256-bit SSL encrypted • GBP (£)</span>
              </div>
            </div>

            <div className="confirmation-actions">
              <button
                type="button"
                className="confirmation-btn-secondary"
                onClick={handleViewOrder}
              >
                <FileText size={16} /> View Order
              </button>
              <button
                type="button"
                className="confirmation-btn-outline"
                onClick={handleContinueShopping}
              >
                Continue Shopping
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Case 2: Returning from Stripe but webhook is still processing
  if (isVerifying && !isPaid) {
    return (
      <div className="confirmation-page">
        <div className="confirmation-container">
          <div className="confirmation-card confirmation-card-verifying">
            <div className="confirmation-icon-circle icon-circle-verifying">
              <RefreshCw size={36} className="spin" />
            </div>
            <h1>Verifying Your Payment</h1>
            <p className="confirmation-intro">
              Your Stripe Checkout session was completed. We are confirming the transaction with Stripe.
            </p>

            <div className="order-ref-box">
              <span className="order-ref-label">Order Reference</span>
              <span className="order-ref-value">{reference}</span>
            </div>

            <div className="confirmation-actions">
              <button
                type="button"
                className="confirmation-btn-secondary"
                onClick={handleManualCheckStatus}
                disabled={isVerifying}
              >
                <RefreshCw size={16} className={isVerifying ? 'spin' : ''} />
                {isVerifying ? 'Checking Status...' : 'Refresh Status'}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Case 3: Confirmed / Paid Successful Order (The primary improved experience)
  return (
    <div className="confirmation-page">
      <div className="confirmation-container">
        <div className="confirmation-card confirmation-card-success">
          {/* Success Checkmark Icon */}
          <div className="confirmation-icon-circle icon-circle-success">
            <CheckCircle2 size={44} className="success-icon" />
          </div>

          {/* Prominent Heading */}
          <h1 className="confirmation-heading">Thank You for Your Order!</h1>

          {/* Confirmation Message */}
          <p className="confirmation-message">
            Your payment was successful, and your order has been confirmed. We are preparing your order
            for delivery. You will receive an email with your order confirmation and updates on your delivery.
          </p>

          {/* Order Reference Box */}
          <div className="order-reference-card">
            <span className="order-reference-label">Order Reference</span>
            <div className="order-reference-display">
              <span className="order-reference-code">{reference}</span>
              <button
                type="button"
                className="copy-ref-btn"
                onClick={handleCopyReference}
                title="Copy order reference"
                aria-label="Copy order reference"
              >
                {copied ? <Check size={16} className="copy-done" /> : <Copy size={16} />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
          </div>

          {/* Conditional Confirmation Email Notice: Only display when accepted for sending */}
          {paymentStatus?.confirmation_email_sent && (
            <div className="email-confirmation-banner">
              <div className="email-icon-wrapper">
                <Mail size={20} />
              </div>
              <div className="email-confirmation-text">
                <strong>Order Confirmation Email Sent</strong>
                <p>
                  {paymentStatus.customer_email
                    ? `An order confirmation email has been sent to ${paymentStatus.customer_email}.`
                    : 'An order confirmation email has been sent with your full receipt and delivery details.'}
                </p>
              </div>
            </div>
          )}

          {/* Action Buttons: View Order History / View Order and Continue Shopping */}
          <div className="confirmation-actions-group">
            <button
              type="button"
              className="confirmation-btn-primary"
              onClick={handleViewOrder}
              id="view-order-btn"
            >
              <FileText size={18} />
              <span>View Order</span>
              <ArrowRight size={16} />
            </button>

            <button
              type="button"
              className="confirmation-btn-secondary"
              onClick={handleContinueShopping}
              id="continue-shopping-btn"
            >
              <ShoppingBag size={18} />
              <span>Continue Shopping</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
