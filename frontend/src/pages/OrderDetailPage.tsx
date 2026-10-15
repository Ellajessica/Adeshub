import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useLocation, Link, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type { Order } from '../types/api';
import { PriceDisplay } from '../components/ui/PriceDisplay';
import {
  ArrowLeft,
  MapPin,
  ShoppingBag,
  AlertCircle,
  Calendar,
  CreditCard,
  ShieldCheck,
  Lock,
  Mail,
  Truck,
  ExternalLink,
  Copy,
  Check
} from 'lucide-react';
import './OrderConfirmationPage.css';

export const OrderDetailPage: React.FC = () => {
  const { reference } = useParams<{ reference: string }>();
  const location = useLocation();
  const navigate = useNavigate();

  const searchParams = new URLSearchParams(location.search);
  const initialEmail = searchParams.get('email') || '';
  const initialSessionId = searchParams.get('session_id') || '';

  const [order, setOrder] = useState<Order | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Guest order verification state
  const [isGuestVerificationRequired, setIsGuestVerificationRequired] = useState(false);
  const [guestEmailInput, setGuestEmailInput] = useState(initialEmail);
  const [guestVerificationError, setGuestVerificationError] = useState<string | null>(null);
  const [isVerifyingGuest, setIsVerifyingGuest] = useState(false);

  const [isInitiatingPayment, setIsInitiatingPayment] = useState(false);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [copiedTracking, setCopiedTracking] = useState(false);

  const fetchOrder = useCallback(async (ref: string, email?: string, sessionId?: string) => {
    setIsLoading(true);
    setError(null);
    setGuestVerificationError(null);

    try {
      const data = await api.getOrderDetail(ref, email, sessionId);
      setOrder(data);
      setIsGuestVerificationRequired(false);
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : '';
      if (
        errMsg.toLowerCase().includes('guest') ||
        errMsg.toLowerCase().includes('permission') ||
        errMsg.toLowerCase().includes('email address')
      ) {
        setIsGuestVerificationRequired(true);
        if (email) {
          setGuestVerificationError('The email address provided does not match this guest order.');
        }
      } else {
        setError(errMsg || 'Unable to load order details.');
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (reference) {
      fetchOrder(reference, initialEmail || undefined, initialSessionId || undefined);
    }
  }, [reference, initialEmail, initialSessionId, fetchOrder]);

  const handleGuestVerificationSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reference) return;

    const trimmedEmail = guestEmailInput.trim();
    if (!trimmedEmail) {
      setGuestVerificationError('Please enter your email address.');
      return;
    }

    setIsVerifyingGuest(true);
    setGuestVerificationError(null);

    try {
      const data = await api.getOrderDetail(reference, trimmedEmail);
      setOrder(data);
      setIsGuestVerificationRequired(false);
      // Update URL query parameter cleanly without reloading
      const updatedParams = new URLSearchParams(location.search);
      updatedParams.set('email', trimmedEmail);
      navigate({ search: updatedParams.toString() }, { replace: true });
    } catch {
      setGuestVerificationError('The email address provided does not match this guest order.');
    } finally {
      setIsVerifyingGuest(false);
    }
  };

  if (isLoading) {
    return (
      <div className="confirmation-page">
        <div className="confirmation-loading">
          <div className="spinner" />
          <p>Loading order details...</p>
        </div>
      </div>
    );
  }

  // Guest Email Verification Required
  if (isGuestVerificationRequired) {
    return (
      <div className="confirmation-page">
        <div className="confirmation-container">
          <div className="guest-verification-card">
            <div className="confirmation-icon-circle" style={{ background: '#f8fafc', border: '2px solid #e2e8f0', color: '#0f5132' }}>
              <Lock size={32} />
            </div>
            <h2>Guest Order Verification</h2>
            <p>
              For your security and privacy, please enter the email address used when placing Order{' '}
              <strong>#{reference}</strong>.
            </p>

            <form onSubmit={handleGuestVerificationSubmit} className="guest-verification-form">
              <div className="guest-form-group">
                <label htmlFor="guest-email-field">Order Email Address</label>
                <div style={{ position: 'relative' }}>
                  <input
                    id="guest-email-field"
                    type="email"
                    className="guest-form-input"
                    placeholder="e.g. name@example.com"
                    value={guestEmailInput}
                    onChange={(e) => setGuestEmailInput(e.target.value)}
                    required
                    autoFocus
                  />
                  <Mail size={18} style={{ position: 'absolute', right: '12px', top: '12px', color: '#94a3b8' }} />
                </div>
                {guestVerificationError && (
                  <div className="guest-form-error">{guestVerificationError}</div>
                )}
              </div>

              <button
                type="submit"
                className="confirmation-btn-primary"
                style={{ width: '100%', marginTop: '0.5rem' }}
                disabled={isVerifyingGuest}
              >
                {isVerifyingGuest ? 'Verifying...' : 'View Order Details'}
              </button>
            </form>

            <div style={{ marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid #f1f5f9' }}>
              <Link to="/shop" className="back-link">
                <ArrowLeft size={16} /> Return to Shop
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="confirmation-page">
        <div className="confirmation-card error-card">
          <AlertCircle size={48} className="error-icon" />
          <h2>Order Not Found</h2>
          <p>{error || 'The requested order details could not be found or you do not have permission to view them.'}</p>
          <div className="confirmation-actions-group" style={{ marginTop: '1.5rem' }}>
            <button className="confirmation-btn-primary" onClick={() => navigate('/shop')}>
              Return to Shop
            </button>
          </div>
        </div>
      </div>
    );
  }

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'DELIVERED':
        return 'badge-success';
      case 'SHIPPED':
      case 'PROCESSING':
      case 'CONFIRMED':
        return 'badge-info';
      case 'CANCELLED':
        return 'badge-danger';
      default:
        return 'badge-warning';
    }
  };

  return (
    <div className="confirmation-page">
      <div className="order-detail-container">
        {/* Navigation Link */}
        <div className="checkout-nav">
          <Link to="/shop" className="back-link">
            <ArrowLeft size={16} /> Continue Shopping
          </Link>
          <span className="checkout-step-badge">Order Details</span>
        </div>

        {/* Top Header Card */}
        <div className="order-detail-header-card">
          <div className="order-header-info">
            <h1>Order #{order.order_reference}</h1>
            <p className="order-date">
              <Calendar size={14} />
              Placed on{' '}
              {new Date(order.created_at).toLocaleDateString('en-GB', {
                day: 'numeric',
                month: 'long',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
              })}
            </p>
          </div>
          <div className="order-status-group">
            <span className={`status-badge ${getStatusBadgeClass(order.order_status)}`}>
              Status: {order.order_status}
            </span>
            <span className="payment-status-badge">
              Payment: {order.payment_status}
            </span>
          </div>
        </div>

        <div className="confirmation-grid">
          {/* Left Column: Order Items */}
          <div className="items-column">
            <div className="card-box">
              <div className="card-box-header">
                <ShoppingBag size={20} className="header-icon" />
                <h2>Ordered Products ({order.items.length})</h2>
              </div>

              <div className="order-items-table">
                {order.items.map((item) => (
                  <div key={item.id} className="order-item-row">
                    <div className="item-details">
                      <h4 className="item-title">{item.product_name}</h4>
                      {item.variant_name && (
                        <span className="item-variant-tag">Variant: {item.variant_name}</span>
                      )}
                      {item.sku && <span className="item-sku">SKU: {item.sku}</span>}
                    </div>
                    <div className="item-qty-price">
                      <span>
                        Qty: {item.quantity} × £{parseFloat(item.unit_price).toFixed(2)}
                      </span>
                    </div>
                    <div className="item-total">
                      <PriceDisplay amount={item.line_total} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column: Address & Totals Breakdown */}
          <div className="summary-column">
            <div className="card-box">
              <div className="card-box-header">
                <MapPin size={20} className="header-icon" />
                <h2>Delivery Address</h2>
              </div>

              <div className="address-snapshot">
                <p className="addr-recipient">
                  <strong>{order.recipient_name}</strong>
                </p>
                <p className="addr-text">{order.address_line1}</p>
                {order.address_line2 && <p className="addr-text">{order.address_line2}</p>}
                <p className="addr-text">
                  {order.city}, {order.postal_code}
                </p>
                {order.county_region && <p className="addr-text">{order.county_region}</p>}
                <p className="addr-text country">{order.country}</p>
                <p className="addr-phone">Phone: {order.phone_number}</p>
              </div>
            </div>

            {/* Shipment Tracking Card (Displayed when real tracking values exist) */}
            {Boolean(order.courier_name || order.tracking_number || order.tracking_url || order.dispatched_at) && (
              <div className="card-box margin-top shipment-tracking-card">
                <div className="card-box-header">
                  <Truck size={20} className="header-icon" />
                  <h2>Shipment Tracking</h2>
                </div>

                <div className="shipment-tracking-body" style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.65rem', fontSize: '0.88rem' }}>
                  {order.courier_name && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ color: '#64748b', fontWeight: 600 }}>Delivery Provider:</span>
                      <strong style={{ color: '#0f172a' }}>{order.courier_name}</strong>
                    </div>
                  )}

                  {order.tracking_number && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ color: '#64748b', fontWeight: 600 }}>Tracking Number:</span>
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                        <code style={{ background: '#f1f5f9', padding: '0.2rem 0.5rem', borderRadius: '4px', fontFamily: 'monospace', fontSize: '0.85rem' }}>
                          {order.tracking_number}
                        </code>
                        <button
                          type="button"
                          onClick={() => {
                            navigator.clipboard.writeText(order.tracking_number!);
                            setCopiedTracking(true);
                            setTimeout(() => setCopiedTracking(false), 2000);
                          }}
                          style={{
                            background: '#e2e8f0',
                            border: 'none',
                            padding: '0.2rem 0.4rem',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center'
                          }}
                          title="Copy tracking number"
                        >
                          {copiedTracking ? <Check size={12} className="text-success" /> : <Copy size={12} />}
                        </button>
                      </div>
                    </div>
                  )}

                  {order.shipment_reference && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ color: '#64748b', fontWeight: 600 }}>Shipment Ref:</span>
                      <span style={{ color: '#334155' }}>{order.shipment_reference}</span>
                    </div>
                  )}

                  {order.dispatched_at && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ color: '#64748b', fontWeight: 600 }}>Dispatched Date:</span>
                      <span style={{ color: '#334155' }}>
                        {new Date(order.dispatched_at).toLocaleDateString('en-GB', {
                          day: 'numeric',
                          month: 'short',
                          year: 'numeric',
                        })}
                      </span>
                    </div>
                  )}

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ color: '#64748b', fontWeight: 600 }}>Delivery Status:</span>
                    <span
                      style={{
                        fontWeight: 700,
                        color: order.order_status === 'DELIVERED' ? '#15803d' : '#0284c7',
                        background: order.order_status === 'DELIVERED' ? '#ecfdf5' : '#f0f9ff',
                        padding: '0.2rem 0.6rem',
                        borderRadius: '9999px',
                        fontSize: '0.78rem'
                      }}
                    >
                      {order.order_status === 'DELIVERED' ? 'Delivered' : 'Dispatched — In Transit'}
                    </span>
                  </div>

                  {order.tracking_url && (order.tracking_url.startsWith('http://') || order.tracking_url.startsWith('https://')) && (
                    <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid #f1f5f9' }}>
                      <a
                        href={order.tracking_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.4rem',
                          backgroundColor: '#0f172a',
                          color: '#ffffff',
                          padding: '0.55rem 1rem',
                          borderRadius: '6px',
                          fontSize: '0.82rem',
                          fontWeight: 600,
                          textDecoration: 'none',
                          width: '100%',
                          justifyContent: 'center'
                        }}
                      >
                        <ExternalLink size={14} /> Track Package with Courier &rarr;
                      </a>
                    </div>
                  )}
                </div>
              </div>
            )}

            <div className="card-box margin-top">
              <div className="card-box-header">
                <h2>Financial Summary</h2>
              </div>

              <div className="financial-breakdown">
                <div className="breakdown-row">
                  <span>Subtotal</span>
                  <PriceDisplay amount={order.subtotal} />
                </div>
                <div className="breakdown-row">
                  <span>Delivery Fee</span>
                  {parseFloat(order.delivery_fee) > 0 ? (
                    <PriceDisplay amount={order.delivery_fee} />
                  ) : (
                    <span className="free-text">Free UK Standard</span>
                  )}
                </div>
                <div className="breakdown-row total-row">
                  <span>Order Total</span>
                  <PriceDisplay amount={order.total_amount} className="final-total" />
                </div>

                {order.notes && (
                  <div
                    style={{
                      marginTop: '1rem',
                      paddingTop: '0.75rem',
                      borderTop: '1px dashed #e2e8f0',
                      fontSize: '0.85rem',
                      color: '#64748b'
                    }}
                  >
                    <strong>Delivery Notes:</strong> {order.notes}
                  </div>
                )}

                {/* Stripe Payment Status */}
                {order.payment_status === 'PAID' ? (
                  <div
                    style={{
                      marginTop: '1.25rem',
                      padding: '0.85rem',
                      background: '#f0fdf4',
                      border: '1px solid #86efac',
                      borderRadius: '8px',
                      fontSize: '0.875rem',
                      color: '#166534'
                    }}
                  >
                    <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      ✓ Payment Verified (Paid in GBP £)
                    </div>
                  </div>
                ) : order.order_status !== 'CANCELLED' ? (
                  <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid #e2e8f0' }}>
                    {paymentError && (
                      <p style={{ color: '#b91c1c', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                        {paymentError}
                      </p>
                    )}
                    <button
                      type="button"
                      className="confirmation-btn-stripe"
                      onClick={async () => {
                        setIsInitiatingPayment(true);
                        setPaymentError(null);
                        try {
                          const session = await api.createCheckoutSession(order.order_reference);
                          if (session && session.checkout_url) {
                            window.location.href = session.checkout_url;
                          } else {
                            setPaymentError('Could not obtain Stripe Checkout URL.');
                          }
                        } catch (err: unknown) {
                          if (err instanceof Error) {
                            setPaymentError(err.message);
                          } else {
                            setPaymentError('Failed to initiate payment.');
                          }
                        } finally {
                          setIsInitiatingPayment(false);
                        }
                      }}
                      disabled={isInitiatingPayment}
                    >
                      <CreditCard size={16} />
                      {isInitiatingPayment
                        ? 'Opening Stripe Checkout...'
                        : `Pay with Card (£${parseFloat(order.total_amount).toFixed(2)})`}
                    </button>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.35rem',
                        fontSize: '0.75rem',
                        color: '#64748b',
                        marginTop: '0.5rem',
                        justifyContent: 'center'
                      }}
                    >
                      <ShieldCheck size={14} />
                      <span>Stripe Checkout • Secure One-Time Payment</span>
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
