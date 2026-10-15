import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import type { AddressInput, CreateOrderPayload, DeliveryQuoteResponse } from '../types/api';
import { PriceDisplay } from '../components/ui/PriceDisplay';
import { getUserDisplayName } from '../utils/userDisplay';
import {
  ShoppingBag,
  MapPin,
  CheckCircle,
  AlertCircle,
  ArrowLeft,
  ShieldCheck,
  CreditCard,
  User as UserIcon,
  Info
} from 'lucide-react';
import './CheckoutPage.css';

export const CheckoutPage: React.FC = () => {
  const { cart, loading: isCartLoading, refreshCart } = useCart();
  const { user, isAuthenticated, addresses, addAddress } = useAuth();
  const navigate = useNavigate();

  // Step 1: Selected saved address ID or 'new'
  const [selectedAddressId, setSelectedAddressId] = useState<number | 'new'>('new');

  // New address form state
  const [newAddressForm, setNewAddressForm] = useState<AddressInput>({
    recipient_name: '',
    phone_number: '',
    address_line1: '',
    address_line2: '',
    city: '',
    county_region: '',
    postal_code: '',
    country: 'United Kingdom',
    is_default: false,
  });

  const [guestEmail, setGuestEmail] = useState('');
  const [notes, setNotes] = useState('');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRedirectingToPayment, setIsRedirectingToPayment] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [addressFieldErrors, setAddressFieldErrors] = useState<Record<string, string>>({});
  const [stripeConfig, setStripeConfig] = useState<{ is_configured: boolean; publishable_key: string; currency: string } | null>(null);
  const [deliveryQuote, setDeliveryQuote] = useState<DeliveryQuoteResponse | null>(null);
  const [isQuoteLoading, setIsQuoteLoading] = useState(false);

  useEffect(() => {
    api.getStripeConfig()
      .then((cfg) => setStripeConfig(cfg))
      .catch(() => setStripeConfig({ is_configured: false, publishable_key: '', currency: 'gbp' }));
  }, []);

  // Fetch authoritative delivery fee and order total from backend
  useEffect(() => {
    if (cart && cart.subtotal) {
      setIsQuoteLoading(true);
      api.getDeliveryQuote(cart.subtotal)
        .then((quote) => setDeliveryQuote(quote))
        .catch((err) => {
          console.error('Failed to load delivery quote:', err);
        })
        .finally(() => setIsQuoteLoading(false));
    }
  }, [cart?.subtotal]);


  // Set default address choice when addresses load
  useEffect(() => {
    if (isAuthenticated && addresses.length > 0) {
      const defaultAddr = addresses.find((a) => a.is_default) || addresses[0];
      setSelectedAddressId(defaultAddr.id);
    } else {
      setSelectedAddressId('new');
    }
  }, [isAuthenticated, addresses]);

  // Pre-fill user info if authenticated
  useEffect(() => {
    if (user) {
      setNewAddressForm((prev) => ({
        ...prev,
        recipient_name: prev.recipient_name || `${user.first_name} ${user.last_name}`.trim(),
        phone_number: prev.phone_number || user.phone_number || '',
      }));
    }
  }, [user]);

  if (isCartLoading) {
    return (
      <div className="checkout-loading-container">
        <div className="spinner"></div>
        <p>Loading checkout details...</p>
      </div>
    );
  }

  // During order submission or Stripe redirect, display active progress rather than empty-cart flash
  if (isSubmitting || isRedirectingToPayment) {
    return (
      <div className="checkout-page">
        <div className="checkout-loading-container" style={{ textAlign: 'center', minHeight: '60vh', padding: '2rem 1rem' }}>
          <div className="spinner"></div>
          <h2 style={{ color: '#0f5132', marginTop: '1.25rem', marginBottom: '0.5rem', fontSize: '1.4rem' }}>
            {isRedirectingToPayment ? 'Connecting to Stripe Checkout...' : 'Processing Your Order...'}
          </h2>
          <p style={{ color: '#475569', maxWidth: '460px', margin: '0 auto', fontSize: '0.95rem', lineHeight: '1.5' }}>
            {isRedirectingToPayment
              ? 'Securing your checkout session and transferring you to the Stripe payment portal. Please do not refresh or close this page.'
              : 'Saving your delivery address and reserving stock for your items...'}
          </p>
        </div>
      </div>
    );
  }

  if (!cart || cart.items.length === 0) {
    return (
      <div className="checkout-page">
        <div className="checkout-empty-card">
          <ShoppingBag size={56} className="empty-icon" />
          <h2>Your Cart is Empty</h2>
          <p>You need at least one item in your shopping cart to proceed to checkout.</p>
          <Link to="/shop" className="continue-shopping-btn">
            Browse Products
          </Link>
        </div>
      </div>
    );
  }

  const handlePlaceOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setAddressFieldErrors({});

    // Validate form fields
    const errors: Record<string, string> = {};

    if (!isAuthenticated && !guestEmail.trim()) {
      errors.guestEmail = 'Please enter an email address for order updates.';
    }

    if (selectedAddressId === 'new' || !isAuthenticated) {
      if (!newAddressForm.recipient_name.trim()) {
        errors.recipient_name = 'Recipient name is required.';
      }
      if (!newAddressForm.phone_number.trim()) {
        errors.phone_number = 'Contact phone number is required.';
      }
      if (!newAddressForm.address_line1.trim()) {
        errors.address_line1 = 'Address line 1 is required.';
      }
      if (!newAddressForm.city.trim()) {
        errors.city = 'Town / City is required.';
      }
      if (!newAddressForm.postal_code.trim()) {
        errors.postal_code = 'UK postal code is required.';
      }
    }

    if (Object.keys(errors).length > 0) {
      setAddressFieldErrors(errors);
      setErrorMessage('Please complete all required fields highlighted below.');
      return;
    }

    // Build payload
    const payload: CreateOrderPayload = {
      notes: notes.trim(),
      delivery_method_code: 'standard',
    };

    if (isAuthenticated) {
      if (selectedAddressId === 'new') {
        payload.recipient_name = newAddressForm.recipient_name.trim();
        payload.phone_number = newAddressForm.phone_number.trim();
        payload.address_line1 = newAddressForm.address_line1.trim();
        payload.address_line2 = newAddressForm.address_line2?.trim() || '';
        payload.city = newAddressForm.city.trim();
        payload.county_region = newAddressForm.county_region?.trim() || '';
        payload.postal_code = newAddressForm.postal_code.trim().toUpperCase();
        payload.country = newAddressForm.country?.trim() || 'United Kingdom';
      } else {
        payload.address_id = selectedAddressId as number;
      }
    } else {
      payload.guest_email = guestEmail.trim().toLowerCase();
      payload.recipient_name = newAddressForm.recipient_name.trim();
      payload.phone_number = newAddressForm.phone_number.trim();
      payload.address_line1 = newAddressForm.address_line1.trim();
      payload.address_line2 = newAddressForm.address_line2?.trim() || '';
      payload.city = newAddressForm.city.trim();
      payload.county_region = newAddressForm.county_region?.trim() || '';
      payload.postal_code = newAddressForm.postal_code.trim().toUpperCase();
      payload.country = newAddressForm.country?.trim() || 'United Kingdom';
    }

    setIsSubmitting(true);

    try {
      if (isAuthenticated && selectedAddressId === 'new') {
        try {
          await addAddress(newAddressForm);
        } catch {
          // Address save failure is non-fatal to order placement
        }
      }

      const createdOrder = await api.createOrder(payload);

      // If Stripe is configured, create Checkout Session and redirect to Stripe portal
      if (stripeConfig?.is_configured) {
        setIsRedirectingToPayment(true);
        try {
          const session = await api.createCheckoutSession(createdOrder.order_reference);
          if (session && session.checkout_url && session.checkout_url.startsWith('https://checkout.stripe.com/')) {
            // Trigger cart refresh without awaiting to clear in-memory state before page redirect
            refreshCart().catch(() => {});
            window.location.href = session.checkout_url;
            return;
          } else {
            throw new Error('Received an invalid or untrusted Stripe Checkout redirect URL.');
          }
        } catch (paymentErr) {
          console.error('Could not redirect to Stripe Checkout directly:', paymentErr);
          setIsRedirectingToPayment(false);
          const paymentMsg = paymentErr instanceof Error ? paymentErr.message : 'Could not initialize Stripe Checkout.';
          await refreshCart();
          navigate(`/orders/confirmation/${createdOrder.order_reference}?payment_status=cancelled`, {
            state: {
              order: createdOrder,
              paymentError: `${paymentMsg} You can complete payment for your order using the button below.`,
            },
          });
          return;
        }
      }

      await refreshCart();
      navigate(`/orders/confirmation/${createdOrder.order_reference}`, {
        state: { order: createdOrder },
      });
    } catch (err: unknown) {
      setIsRedirectingToPayment(false);
      if (err && typeof err === 'object' && 'fieldErrors' in err) {
        const apiErrors = (err as { fieldErrors?: Record<string, string> }).fieldErrors;
        if (apiErrors) setAddressFieldErrors(apiErrors);
      }
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to place order. Please verify stock availability and try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="checkout-page">
      <div className="checkout-container">
        {/* Navigation Breadcrumb */}
        <div className="checkout-nav">
          <Link to="/cart" className="back-link">
            <ArrowLeft size={16} /> Return to Cart
          </Link>
          <span className="checkout-step-badge">Checkout</span>
        </div>

        {errorMessage && (
          <div className="checkout-error-banner" role="alert">
            <AlertCircle size={20} />
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handlePlaceOrder} className="checkout-grid">
          {/* Main Left Column: Account, Address, Payment Status */}
          <div className="checkout-main-column">
            {/* Step 1: Customer Info */}
            <section className="checkout-section">
              <div className="section-header">
                <UserIcon className="section-icon" size={20} />
                <h2>1. Customer Account</h2>
              </div>

              {isAuthenticated ? (
                <div className="account-recognized-banner">
                  <CheckCircle size={18} className="success-icon" />
                  <div>
                    <p className="account-name">Logged in as <strong>{getUserDisplayName(user)}</strong></p>
                    <p className="account-subtext">This order will be saved to your AdesHub account order history.</p>
                  </div>
                </div>
              ) : (
                <div className="guest-login-prompt">
                  <div className="prompt-content">
                    <p>Already have an AdesHub account?</p>
                    <Link to="/login" state={{ from: '/checkout' }} className="login-link">
                      Sign In Now
                    </Link>
                  </div>
                  <div className="form-group margin-top">
                    <label htmlFor="guestEmail">
                      Email Address for Order Confirmation <span className="req-star" aria-hidden="true">*</span>
                    </label>
                    <div className="input-wrapper">
                      <input
                        id="guestEmail"
                        type="email"
                        value={guestEmail}
                        onChange={(e) => {
                          setGuestEmail(e.target.value);
                          if (addressFieldErrors.guestEmail) {
                            setAddressFieldErrors((prev) => {
                              const next = { ...prev };
                              delete next.guestEmail;
                              return next;
                            });
                          }
                        }}
                        required={!isAuthenticated}
                        className={addressFieldErrors.guestEmail ? 'input-invalid' : ''}
                      />
                    </div>
                    {addressFieldErrors.guestEmail && (
                      <span className="field-error-message">{addressFieldErrors.guestEmail}</span>
                    )}
                  </div>
                </div>
              )}
            </section>

            {/* Step 2: Delivery Address */}
            <section className="checkout-section">
              <div className="section-header">
                <MapPin className="section-icon" size={20} />
                <h2>2. UK Delivery Address</h2>
              </div>

              {isAuthenticated && addresses.length > 0 && (
                <div className="saved-addresses-selector">
                  <p className="selector-title">Select from your saved addresses:</p>
                  <div className="address-options-list">
                    {addresses.map((addr) => (
                      <label
                        key={addr.id}
                        className={`address-option-card ${selectedAddressId === addr.id ? 'selected' : ''}`}
                      >
                        <input
                          type="radio"
                          name="deliveryAddress"
                          value={addr.id}
                          checked={selectedAddressId === addr.id}
                          onChange={() => setSelectedAddressId(addr.id)}
                        />
                        <div className="option-details">
                          <span className="option-name">{addr.recipient_name}</span>
                          <span className="option-line">{addr.address_line1}, {addr.city}</span>
                          <span className="option-postcode">{addr.postal_code}, {addr.country}</span>
                        </div>
                      </label>
                    ))}

                    <label className={`address-option-card ${selectedAddressId === 'new' ? 'selected' : ''}`}>
                      <input
                        type="radio"
                        name="deliveryAddress"
                        value="new"
                        checked={selectedAddressId === 'new'}
                        onChange={() => setSelectedAddressId('new')}
                      />
                      <div className="option-details">
                        <span className="option-name">+ Enter a new delivery address</span>
                      </div>
                    </label>
                  </div>
                </div>
              )}

              {(selectedAddressId === 'new' || !isAuthenticated || addresses.length === 0) && (
                <div className="new-address-form">
                  <div className="form-group">
                    <label htmlFor="checkout_recipient_name">
                      Recipient Name <span className="req-star" aria-hidden="true">*</span>
                    </label>
                    <div className="input-wrapper">
                      <input
                        id="checkout_recipient_name"
                        type="text"
                        value={newAddressForm.recipient_name}
                        onChange={(e) => {
                          setNewAddressForm({ ...newAddressForm, recipient_name: e.target.value });
                          if (addressFieldErrors.recipient_name) {
                            setAddressFieldErrors((prev) => {
                              const next = { ...prev };
                              delete next.recipient_name;
                              return next;
                            });
                          }
                        }}
                        required
                        className={addressFieldErrors.recipient_name ? 'input-invalid' : ''}
                      />
                    </div>
                    {addressFieldErrors.recipient_name && (
                      <span className="field-error-message">{addressFieldErrors.recipient_name}</span>
                    )}
                  </div>

                  <div className="form-group">
                    <label htmlFor="checkout_phone_number">
                      Contact Phone Number <span className="req-star" aria-hidden="true">*</span>
                    </label>
                    <div className="input-wrapper">
                      <input
                        id="checkout_phone_number"
                        type="tel"
                        value={newAddressForm.phone_number}
                        onChange={(e) => {
                          setNewAddressForm({ ...newAddressForm, phone_number: e.target.value });
                          if (addressFieldErrors.phone_number) {
                            setAddressFieldErrors((prev) => {
                              const next = { ...prev };
                              delete next.phone_number;
                              return next;
                            });
                          }
                        }}
                        required
                        className={addressFieldErrors.phone_number ? 'input-invalid' : ''}
                      />
                    </div>
                    {addressFieldErrors.phone_number && (
                      <span className="field-error-message">{addressFieldErrors.phone_number}</span>
                    )}
                  </div>

                  <div className="form-group">
                    <label htmlFor="checkout_address_line1">
                      Address Line 1 <span className="req-star" aria-hidden="true">*</span>
                    </label>
                    <div className="input-wrapper">
                      <input
                        id="checkout_address_line1"
                        type="text"
                        value={newAddressForm.address_line1}
                        onChange={(e) => {
                          setNewAddressForm({ ...newAddressForm, address_line1: e.target.value });
                          if (addressFieldErrors.address_line1) {
                            setAddressFieldErrors((prev) => {
                              const next = { ...prev };
                              delete next.address_line1;
                              return next;
                            });
                          }
                        }}
                        required
                        className={addressFieldErrors.address_line1 ? 'input-invalid' : ''}
                      />
                    </div>
                    {addressFieldErrors.address_line1 && (
                      <span className="field-error-message">{addressFieldErrors.address_line1}</span>
                    )}
                  </div>

                  <div className="form-group">
                    <label htmlFor="checkout_address_line2">
                      Address Line 2 (Optional)
                    </label>
                    <div className="input-wrapper">
                      <input
                        id="checkout_address_line2"
                        type="text"
                        value={newAddressForm.address_line2 || ''}
                        onChange={(e) => setNewAddressForm({ ...newAddressForm, address_line2: e.target.value })}
                      />
                    </div>
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label htmlFor="checkout_city">
                        Town / City <span className="req-star" aria-hidden="true">*</span>
                      </label>
                      <div className="input-wrapper">
                        <input
                          id="checkout_city"
                          type="text"
                          value={newAddressForm.city}
                          onChange={(e) => {
                            setNewAddressForm({ ...newAddressForm, city: e.target.value });
                            if (addressFieldErrors.city) {
                              setAddressFieldErrors((prev) => {
                                const next = { ...prev };
                                delete next.city;
                                return next;
                              });
                            }
                          }}
                          required
                          className={addressFieldErrors.city ? 'input-invalid' : ''}
                        />
                      </div>
                      {addressFieldErrors.city && (
                        <span className="field-error-message">{addressFieldErrors.city}</span>
                      )}
                    </div>

                    <div className="form-group">
                      <label htmlFor="checkout_county">
                        County / Region
                      </label>
                      <div className="input-wrapper">
                        <input
                          id="checkout_county"
                          type="text"
                          value={newAddressForm.county_region || ''}
                          onChange={(e) => setNewAddressForm({ ...newAddressForm, county_region: e.target.value })}
                        />
                      </div>
                    </div>
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label htmlFor="checkout_postal_code">
                        UK Postal Code <span className="req-star" aria-hidden="true">*</span>
                      </label>
                      <div className="input-wrapper">
                        <input
                          id="checkout_postal_code"
                          type="text"
                          value={newAddressForm.postal_code}
                          onChange={(e) => {
                            setNewAddressForm({ ...newAddressForm, postal_code: e.target.value.toUpperCase() });
                            if (addressFieldErrors.postal_code) {
                              setAddressFieldErrors((prev) => {
                                const next = { ...prev };
                                delete next.postal_code;
                                return next;
                              });
                            }
                          }}
                          required
                          className={addressFieldErrors.postal_code ? 'input-invalid' : ''}
                        />
                      </div>
                      {addressFieldErrors.postal_code && (
                        <span className="field-error-message">{addressFieldErrors.postal_code}</span>
                      )}
                    </div>

                    <div className="form-group">
                      <label htmlFor="checkout_country">
                        Country <span className="req-star" aria-hidden="true">*</span>
                      </label>
                      <div className="input-wrapper">
                        <input
                          id="checkout_country"
                          type="text"
                          value={newAddressForm.country || 'United Kingdom'}
                          onChange={(e) => setNewAddressForm({ ...newAddressForm, country: e.target.value })}
                          required
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </section>

            {/* Step 3: Payment Notice */}
            <section className="checkout-section">
              <div className="section-header">
                <CreditCard className="section-icon" size={20} />
                <h2>3. Payment Method</h2>
              </div>

              <div className="payment-notice-card" style={{ borderColor: stripeConfig?.is_configured ? '#86efac' : '#bfdbfe', backgroundColor: stripeConfig?.is_configured ? '#f0fdf4' : '#eff6ff' }}>
                <div className="notice-header">
                  {stripeConfig?.is_configured ? (
                    <>
                      <ShieldCheck size={20} style={{ color: '#16a34a' }} />
                      <h4 style={{ color: '#166534' }}>Stripe Checkout (One-Time Card Payment in GBP £)</h4>
                    </>
                  ) : (
                    <>
                      <Info size={20} className="info-icon" />
                      <h4>Payment Gateway: Stripe Test Mode / Configuration Pending</h4>
                    </>
                  )}
                </div>
                {stripeConfig?.is_configured ? (
                  <p style={{ color: '#14532d' }}>
                    Upon confirming your order, you will be redirected to the secure Stripe Checkout portal to complete payment by Credit / Debit Card in GBP (£).
                  </p>
                ) : (
                  <p>
                    Stripe payment gateway credentials are being configured in the environment. Confirming this order will atomically reserve your stock and generate your official Order Reference with an <strong>Awaiting Payment (PENDING)</strong> status.
                  </p>
                )}
                <p className="notice-subtext">
                  All monetary calculations and currency rules are authoritatively enforced by the backend database.
                </p>
              </div>

              <div className="form-group margin-top">
                <label htmlFor="notes">Order Delivery Notes (Optional)</label>
                <textarea
                  id="notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                />
              </div>
            </section>
          </div>

          {/* Right Column: Order Summary & Confirmation */}
          <div className="checkout-summary-column">
            <div className="order-summary-sticky">
              <h3>Order Summary</h3>

              <div className="summary-items-list">
                {cart.items.map((item) => (
                  <div key={item.id} className="summary-item-row">
                    <div className="item-info">
                      <span className="item-name">{item.product.name}</span>
                      {item.variant && <span className="item-variant">Variant: {item.variant.name}</span>}
                      <span className="item-qty">Qty: {item.quantity} × £{parseFloat(item.unit_price).toFixed(2)}</span>
                    </div>
                    <div className="item-line-total">
                      <PriceDisplay amount={item.line_total} />
                    </div>
                  </div>
                ))}
              </div>

              <div className="summary-calculations">
                <div className="calc-row">
                  <span>Cart Subtotal</span>
                  <PriceDisplay amount={cart.subtotal} />
                </div>
                <div className="calc-row">
                  <span>Delivery Fee</span>
                  {deliveryQuote ? (
                    deliveryQuote.is_free_delivery ? (
                      <span className="free-tag">Free UK Standard</span>
                    ) : (
                      <PriceDisplay amount={deliveryQuote.delivery_fee} />
                    )
                  ) : isQuoteLoading ? (
                    <span className="free-tag">Calculating...</span>
                  ) : (
                    <span className="free-tag">Free UK Standard</span>
                  )}
                </div>

                {deliveryQuote?.amount_needed_for_free_delivery && parseFloat(deliveryQuote.amount_needed_for_free_delivery) > 0 && (
                  <div className="free-delivery-hint" style={{ fontSize: '0.8rem', color: '#0369a1', background: '#f0f9ff', border: '1px solid #bae6fd', padding: '6px 10px', borderRadius: '6px', margin: '6px 0' }}>
                    <Info size={14} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '4px' }} />
                    Add £{parseFloat(deliveryQuote.amount_needed_for_free_delivery).toFixed(2)} more for <strong>Free Delivery</strong>!
                  </div>
                )}

                <div className="calc-row total-row">
                  <span>Final Total</span>
                  <PriceDisplay
                    amount={deliveryQuote ? deliveryQuote.final_total : cart.subtotal}
                    className="final-price"
                  />
                </div>
              </div>

              <div className="guarantee-box">
                <ShieldCheck size={18} />
                <span>Authoritative DB Price Check & Atomic Stock Reservation</span>
              </div>

              <button type="submit" className="place-order-btn" disabled={isSubmitting}>
                {isSubmitting ? (
                  <span className="spinner-inline">Processing Order...</span>
                ) : stripeConfig?.is_configured ? (
                  <span>Place Order & Pay with Card (£)</span>
                ) : (
                  <span>Confirm Order & Reserve Stock</span>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
