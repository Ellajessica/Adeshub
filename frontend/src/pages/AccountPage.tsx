import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api, ApiError } from '../services/api';
import type { Order, AddressInput, Address } from '../types/api';
import { PriceDisplay } from '../components/ui/PriceDisplay';
import { getUserDisplayName, getUserAvatarInitial } from '../utils/userDisplay';
import {
  User as UserIcon,
  MapPin,
  ShoppingBag,
  Lock,
  Plus,
  Edit2,
  Trash2,
  CheckCircle,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  LogOut,
  Building,
  Phone,
  Mail,
  Calendar,
  ExternalLink,
  PackageCheck,
  CreditCard,
  Truck
} from 'lucide-react';
import './AccountPage.css';

export const AccountPage: React.FC = () => {
  const {
    user,
    isAuthenticated,
    isLoading: isAuthLoading,
    logout,
    updateProfile,
    changePassword,
    addresses,
    addAddress,
    editAddress,
    removeAddress,
  } = useAuth();

  const navigate = useNavigate();
  const location = useLocation();

  const [activeTab, setActiveTab] = useState<'profile' | 'addresses' | 'orders' | 'security'>('profile');

  // Profile Form state
  const [profileForm, setProfileForm] = useState({
    email: '',
    first_name: '',
    last_name: '',
    phone_number: '',
  });
  const [profileStatus, setProfileStatus] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);
  const [profileErrors, setProfileErrors] = useState<Record<string, string>>({});
  const [isUpdatingProfile, setIsUpdatingProfile] = useState(false);

  // Address Form state
  const [showAddressModal, setShowAddressModal] = useState(false);
  const [editingAddressId, setEditingAddressId] = useState<number | null>(null);
  const [addressForm, setAddressForm] = useState<AddressInput>({
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
  const [addressStatus, setAddressStatus] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);
  const [isSubmittingAddress, setIsSubmittingAddress] = useState(false);

  // Orders state
  const [orders, setOrders] = useState<Order[]>([]);
  const [isOrdersLoading, setIsOrdersLoading] = useState(false);
  const [ordersError, setOrdersError] = useState<string | null>(null);
  const [expandedOrderId, setExpandedOrderId] = useState<number | null>(null);

  // Password state
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [passwordStatus, setPasswordStatus] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);
  const [passwordErrors, setPasswordErrors] = useState<Record<string, string>>({});
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  const profileTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const passwordTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (profileTimerRef.current) clearTimeout(profileTimerRef.current);
      if (passwordTimerRef.current) clearTimeout(passwordTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (!isAuthLoading && !isAuthenticated) {
      navigate('/login', { state: { from: location.pathname } });
    }
  }, [isAuthenticated, isAuthLoading, navigate, location]);

  useEffect(() => {
    if (user) {
      setProfileForm({
        email: user.email || '',
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        phone_number: user.phone_number || '',
      });
    }
  }, [user]);

  useEffect(() => {
    if (activeTab === 'orders' && isAuthenticated) {
      fetchOrders();
    }
  }, [activeTab, isAuthenticated]);

  const fetchOrders = async () => {
    setIsOrdersLoading(true);
    setOrdersError(null);
    try {
      const res = await api.getMyOrders();
      if (Array.isArray(res)) {
        setOrders(res);
      } else {
        setOrders(res.results || []);
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setOrdersError(err.message);
      } else {
        setOrdersError('Failed to load order history.');
      }
    } finally {
      setIsOrdersLoading(false);
    }
  };

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isUpdatingProfile) return;
    if (profileTimerRef.current) {
      clearTimeout(profileTimerRef.current);
      profileTimerRef.current = null;
    }
    setProfileStatus(null);
    setProfileErrors({});
    setIsUpdatingProfile(true);

    try {
      const updatedUser = await updateProfile(profileForm);
      if (updatedUser) {
        setProfileForm({
          email: updatedUser.email || '',
          first_name: updatedUser.first_name || '',
          last_name: updatedUser.last_name || '',
          phone_number: updatedUser.phone_number || '',
        });
      }
      setProfileStatus({ type: 'success', msg: 'Profile updated successfully.' });
      profileTimerRef.current = setTimeout(() => {
        setProfileStatus((current) => (current?.type === 'success' ? null : current));
      }, 4000);
    } catch (err: unknown) {
      if (err instanceof ApiError && err.fieldErrors) {
        setProfileErrors(err.fieldErrors);
      }
      const msg = err instanceof Error ? err.message : 'Failed to update profile.';
      setProfileStatus({ type: 'error', msg });
    } finally {
      setIsUpdatingProfile(false);
    }
  };

  const handleOpenAddAddress = () => {
    setEditingAddressId(null);
    setAddressForm({
      recipient_name: user ? `${user.first_name} ${user.last_name}`.trim() : '',
      phone_number: user?.phone_number || '',
      address_line1: '',
      address_line2: '',
      city: '',
      county_region: '',
      postal_code: '',
      country: 'United Kingdom',
      is_default: addresses.length === 0,
    });
    setShowAddressModal(true);
  };

  const handleOpenEditAddress = (addr: Address) => {
    setEditingAddressId(addr.id);
    setAddressForm({
      recipient_name: addr.recipient_name,
      phone_number: addr.phone_number,
      address_line1: addr.address_line1,
      address_line2: addr.address_line2 || '',
      city: addr.city,
      county_region: addr.county_region || '',
      postal_code: addr.postal_code,
      country: addr.country || 'United Kingdom',
      is_default: addr.is_default,
    });
    setShowAddressModal(true);
  };

  const handleAddressSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddressStatus(null);
    setIsSubmittingAddress(true);

    try {
      if (editingAddressId) {
        await editAddress(editingAddressId, addressForm);
        setAddressStatus({ type: 'success', msg: 'Address updated successfully!' });
      } else {
        await addAddress(addressForm);
        setAddressStatus({ type: 'success', msg: 'Address added successfully!' });
      }
      setShowAddressModal(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to save address.';
      setAddressStatus({ type: 'error', msg });
    } finally {
      setIsSubmittingAddress(false);
    }
  };

  const handleDeleteAddress = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this address?')) return;
    try {
      await removeAddress(id);
      setAddressStatus({ type: 'success', msg: 'Address deleted.' });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to delete address.';
      setAddressStatus({ type: 'error', msg });
    }
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isChangingPassword) return;
    if (passwordTimerRef.current) {
      clearTimeout(passwordTimerRef.current);
      passwordTimerRef.current = null;
    }
    setPasswordStatus(null);
    setPasswordErrors({});

    const errors: Record<string, string> = {};
    if (!passwordForm.currentPassword.trim()) {
      errors.currentPassword = 'This field is required.';
    }
    if (!passwordForm.newPassword) {
      errors.newPassword = 'This field is required.';
    } else if (passwordForm.newPassword.length < 8) {
      errors.newPassword = 'New password must be at least 8 characters long.';
    }
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      errors.confirmPassword = 'New passwords do not match.';
    }

    if (Object.keys(errors).length > 0) {
      setPasswordErrors(errors);
      setPasswordStatus({ type: 'error', msg: 'Please resolve the highlighted password errors.' });
      return;
    }

    setIsChangingPassword(true);

    try {
      await changePassword(passwordForm.currentPassword, passwordForm.newPassword, passwordForm.confirmPassword);
      setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
      setPasswordErrors({});
      setPasswordStatus({ type: 'success', msg: 'Password updated successfully.' });
      passwordTimerRef.current = setTimeout(() => {
        setPasswordStatus((current) => (current?.type === 'success' ? null : current));
      }, 4000);
    } catch (err: unknown) {
      if (err instanceof ApiError && err.fieldErrors) {
        const mappedErrors: Record<string, string> = {};
        if (err.fieldErrors.current_password) mappedErrors.currentPassword = err.fieldErrors.current_password;
        if (err.fieldErrors.old_password) mappedErrors.currentPassword = err.fieldErrors.old_password;
        if (err.fieldErrors.new_password) mappedErrors.newPassword = err.fieldErrors.new_password;
        if (err.fieldErrors.new_password_confirm) mappedErrors.confirmPassword = err.fieldErrors.new_password_confirm;
        setPasswordErrors(mappedErrors);
      }
      const msg = err instanceof Error ? err.message : 'Failed to change password.';
      setPasswordStatus({ type: 'error', msg });
    } finally {
      setIsChangingPassword(false);
    }
  };

  if (isAuthLoading || !user) {
    return (
      <div className="account-loading-container">
        <div className="spinner"></div>
        <p>Loading your account details...</p>
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

  const getPaymentBadgeClass = (status: string) => {
    switch (status) {
      case 'PAID':
        return 'badge-success';
      case 'PENDING':
        return 'badge-warning';
      case 'FAILED':
      case 'REFUNDED':
        return 'badge-danger';
      default:
        return 'badge-info';
    }
  };

  return (
    <div className="account-page">
      <div className="account-container">
        {/* Sidebar Navigation */}
        <aside className="account-sidebar">
          <div className="user-profile-summary">
            <div className="avatar-circle">
              {getUserAvatarInitial(user)}
            </div>
            <div className="user-info">
              <h3>{getUserDisplayName(user)}</h3>
              <p className="user-email">{user.email}</p>
              {user.is_staff && <span className="staff-badge">Staff Account</span>}
            </div>
          </div>

          <nav className="account-tabs-nav">
            <button
              className={`tab-btn ${activeTab === 'profile' ? 'active' : ''}`}
              onClick={() => setActiveTab('profile')}
            >
              <UserIcon size={18} />
              <span>Profile Details</span>
            </button>
            <button
              className={`tab-btn ${activeTab === 'addresses' ? 'active' : ''}`}
              onClick={() => setActiveTab('addresses')}
            >
              <MapPin size={18} />
              <span>Saved Addresses</span>
              {addresses.length > 0 && <span className="count-pill">{addresses.length}</span>}
            </button>
            <button
              className={`tab-btn ${activeTab === 'orders' ? 'active' : ''}`}
              onClick={() => setActiveTab('orders')}
            >
              <ShoppingBag size={18} />
              <span>Order History</span>
            </button>
            <button
              className={`tab-btn ${activeTab === 'security' ? 'active' : ''}`}
              onClick={() => setActiveTab('security')}
            >
              <Lock size={18} />
              <span>Password & Security</span>
            </button>
            <button className="tab-btn logout-btn" onClick={() => logout().then(() => navigate('/'))}>
              <LogOut size={18} />
              <span>Log Out</span>
            </button>
          </nav>
        </aside>

        {/* Main Content Area */}
        <main className="account-main">
          {/* TAB 1: PROFILE */}
          {activeTab === 'profile' && (
            <div className="account-tab-content">
              <div className="tab-header">
                <h2>Profile Information</h2>
                <p>View and update your personal details.</p>
              </div>

              {profileStatus && (
                <div
                  className={`status-banner ${profileStatus.type}`}
                  role={profileStatus.type === 'error' ? 'alert' : 'status'}
                  aria-live="polite"
                >
                  {profileStatus.type === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
                  <span>{profileStatus.msg}</span>
                </div>
              )}

              <form onSubmit={handleProfileSubmit} className="profile-form">
                <div className="form-group">
                  <label htmlFor="profile_email">
                    Email Address <span className="req-star" aria-hidden="true">*</span>
                  </label>
                  <div className="input-wrapper">
                    <Mail className="input-icon" size={18} />
                    <input
                      id="profile_email"
                      type="email"
                      value={profileForm.email}
                      onChange={(e) => {
                        setProfileForm({ ...profileForm, email: e.target.value });
                        if (profileErrors.email) {
                          setProfileErrors((prev) => {
                            const next = { ...prev };
                            delete next.email;
                            return next;
                          });
                        }
                      }}
                      placeholder="your.email@example.com"
                      required
                      className={profileErrors.email ? 'input-invalid' : ''}
                    />
                  </div>
                  {profileErrors.email && (
                    <span className="field-error-message">{profileErrors.email}</span>
                  )}
                  <small className="field-hint">Used for sign in and order confirmation updates.</small>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="first_name">First Name</label>
                    <div className="input-wrapper">
                      <UserIcon className="input-icon" size={18} />
                      <input
                        id="first_name"
                        type="text"
                        value={profileForm.first_name}
                        onChange={(e) => {
                          setProfileForm({ ...profileForm, first_name: e.target.value });
                          if (profileErrors.first_name) {
                            setProfileErrors((prev) => {
                              const next = { ...prev };
                              delete next.first_name;
                              return next;
                            });
                          }
                        }}
                        placeholder="First name"
                        className={profileErrors.first_name ? 'input-invalid' : ''}
                      />
                    </div>
                    {profileErrors.first_name && (
                      <span className="field-error-message">{profileErrors.first_name}</span>
                    )}
                  </div>

                  <div className="form-group">
                    <label htmlFor="last_name">Last Name</label>
                    <div className="input-wrapper">
                      <UserIcon className="input-icon" size={18} />
                      <input
                        id="last_name"
                        type="text"
                        value={profileForm.last_name}
                        onChange={(e) => {
                          setProfileForm({ ...profileForm, last_name: e.target.value });
                          if (profileErrors.last_name) {
                            setProfileErrors((prev) => {
                              const next = { ...prev };
                              delete next.last_name;
                              return next;
                            });
                          }
                        }}
                        placeholder="Last name"
                        className={profileErrors.last_name ? 'input-invalid' : ''}
                      />
                    </div>
                    {profileErrors.last_name && (
                      <span className="field-error-message">{profileErrors.last_name}</span>
                    )}
                  </div>
                </div>

                <div className="form-group">
                  <label htmlFor="phone_number">Phone Number</label>
                  <div className="input-wrapper">
                    <Phone className="input-icon" size={18} />
                    <input
                      id="phone_number"
                      type="tel"
                      value={profileForm.phone_number}
                      onChange={(e) => {
                        setProfileForm({ ...profileForm, phone_number: e.target.value });
                        if (profileErrors.phone_number) {
                          setProfileErrors((prev) => {
                            const next = { ...prev };
                            delete next.phone_number;
                            return next;
                          });
                        }
                      }}
                      placeholder="Enter your phone number"
                      className={profileErrors.phone_number ? 'input-invalid' : ''}
                    />
                  </div>
                  {profileErrors.phone_number && (
                    <span className="field-error-message">{profileErrors.phone_number}</span>
                  )}
                </div>

                <button type="submit" className="save-btn" disabled={isUpdatingProfile}>
                  {isUpdatingProfile ? 'Saving Changes...' : 'Save Profile Changes'}
                </button>
              </form>
            </div>
          )}

          {/* TAB 2: ADDRESSES */}
          {activeTab === 'addresses' && (
            <div className="account-tab-content">
              <div className="tab-header address-header">
                <div>
                  <h2>Saved Delivery Addresses</h2>
                  <p>Manage your UK delivery addresses for quick checkout.</p>
                </div>
                <button className="add-address-btn" onClick={handleOpenAddAddress}>
                  <Plus size={18} />
                  <span>Add New Address</span>
                </button>
              </div>

              {addressStatus && (
                <div className={`status-banner ${addressStatus.type}`} role="alert">
                  {addressStatus.type === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
                  <span>{addressStatus.msg}</span>
                </div>
              )}

              {addresses.length === 0 ? (
                <div className="empty-state">
                  <MapPin size={48} className="empty-icon" />
                  <h3>No Delivery Addresses Saved</h3>
                  <p>Add a delivery address now to speed up future checkouts.</p>
                  <button className="primary-action-btn" onClick={handleOpenAddAddress}>
                    Add Address Now
                  </button>
                </div>
              ) : (
                <div className="address-grid">
                  {addresses.map((addr) => (
                    <div key={addr.id} className={`address-card ${addr.is_default ? 'default-card' : ''}`}>
                      {addr.is_default && <span className="default-badge">Default Delivery</span>}
                      <h4 className="recipient-name">{addr.recipient_name}</h4>
                      <p className="addr-line">{addr.address_line1}</p>
                      {addr.address_line2 && <p className="addr-line">{addr.address_line2}</p>}
                      <p className="addr-line">
                        {addr.city}, {addr.postal_code}
                      </p>
                      {addr.county_region && <p className="addr-line">{addr.county_region}</p>}
                      <p className="addr-country">{addr.country}</p>
                      {addr.phone_number && <p className="addr-phone">Phone: {addr.phone_number}</p>}

                      <div className="address-actions">
                        <button className="edit-btn" onClick={() => handleOpenEditAddress(addr)}>
                          <Edit2 size={16} /> Edit
                        </button>
                        <button className="delete-btn" onClick={() => handleDeleteAddress(addr.id)}>
                          <Trash2 size={16} /> Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: ORDERS */}
          {activeTab === 'orders' && (
            <div className="account-tab-content">
              <div className="tab-header">
                <h2>Order History</h2>
                <p>View your past orders, delivery status, and stored order records.</p>
              </div>

              {isOrdersLoading ? (
                <div className="account-loading-container">
                  <div className="spinner"></div>
                  <p>Fetching your orders...</p>
                </div>
              ) : ordersError ? (
                <div className="status-banner error" role="alert">
                  <AlertCircle size={18} />
                  <span>{ordersError}</span>
                </div>
              ) : orders.length === 0 ? (
                <div className="empty-state">
                  <ShoppingBag size={48} className="empty-icon" />
                  <h3>No Orders Found</h3>
                  <p>You haven't placed any orders with AdesHub yet. Explore our authentic African groceries and products!</p>
                  <button className="primary-action-btn" onClick={() => navigate('/shop')}>
                    Start Shopping
                  </button>
                </div>
              ) : (
                <div className="orders-list">
                  {orders.map((order) => {
                    const isExpanded = expandedOrderId === order.id;
                    const orderDate = new Date(order.created_at);
                    const formattedDate = orderDate.toLocaleDateString('en-GB', {
                      day: 'numeric',
                      month: 'short',
                      year: 'numeric',
                    });
                    const formattedTime = orderDate.toLocaleTimeString('en-GB', {
                      hour: '2-digit',
                      minute: '2-digit',
                    });

                    return (
                      <div key={order.id} className={`order-summary-card ${isExpanded ? 'card-expanded' : ''}`}>
                        <div className="order-card-header">
                          <div className="order-header-info">
                            <span className="order-ref">Order #{order.order_reference}</span>
                            <span className="order-date">
                              <Calendar size={14} className="order-date-icon" />
                              Placed on {formattedDate} at {formattedTime}
                            </span>
                          </div>
                          <div className="order-status-group">
                            <span className={`status-badge ${getStatusBadgeClass(order.order_status)}`}>
                              {order.order_status}
                            </span>
                            <span className={`payment-badge ${getPaymentBadgeClass(order.payment_status)}`}>
                              Payment: {order.payment_status}
                            </span>
                          </div>
                        </div>

                        <div className="order-card-body">
                          <div className="order-items-preview">
                            <div className="items-summary-header">
                              <PackageCheck size={16} className="pkg-icon" />
                              <strong>{order.items.length} item{order.items.length === 1 ? '' : 's'} in order</strong>
                            </div>
                            <div className="order-items-chips-list">
                              {order.items.map((item) => (
                                <div key={item.id} className="order-item-chip">
                                  <span className="chip-qty">{item.quantity}×</span>
                                  <span className="chip-name">{item.product_name}</span>
                                  {item.variant_name && (
                                    <span className="chip-variant">({item.variant_name})</span>
                                  )}
                                  <span className="chip-price">£{parseFloat(item.line_total).toFixed(2)}</span>
                                </div>
                              ))}
                            </div>
                            <div className="order-delivery-destination">
                              <MapPin size={16} className="pin-icon" />
                              <span className="dest-text" title={`${order.recipient_name}, ${order.address_line1}, ${order.city}, ${order.postal_code}`}>
                                <strong>Deliver to:</strong> {order.recipient_name} • {order.address_line1}, {order.city}, {order.postal_code}, UK
                              </span>
                            </div>
                          </div>

                          <div className="order-card-price">
                            <span className="total-label">Total Amount</span>
                            <PriceDisplay amount={order.total_amount} className="total-amount" />
                          </div>
                        </div>

                        {/* Expandable Structured Details */}
                        {isExpanded && (
                          <div className="order-expanded-details">
                            <div className="expanded-section">
                              <h4 className="expanded-section-title">
                                <ShoppingBag size={16} /> Ordered Products & Pricing
                              </h4>
                              <div className="details-table-wrapper">
                                <table className="details-items-table">
                                  <thead>
                                    <tr>
                                      <th>Product Details</th>
                                      <th>Qty</th>
                                      <th>Unit Price</th>
                                      <th>Subtotal</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {order.items.map((item) => (
                                      <tr key={item.id}>
                                        <td>
                                          <div className="item-table-cell">
                                            <strong>{item.product_name}</strong>
                                            {item.variant_name && (
                                              <span className="table-variant-badge">Variant: {item.variant_name}</span>
                                            )}
                                            {item.sku && <span className="table-sku">SKU: {item.sku}</span>}
                                          </div>
                                        </td>
                                        <td>{item.quantity}</td>
                                        <td>£{parseFloat(item.unit_price).toFixed(2)}</td>
                                        <td className="item-cell-total">£{parseFloat(item.line_total).toFixed(2)}</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>

                            <div className="expanded-grid-two">
                              <div className="expanded-section">
                                <h4 className="expanded-section-title">
                                  <MapPin size={16} /> Delivery Address Snapshot
                                </h4>
                                <div className="address-snapshot-box">
                                  <p className="snap-name"><strong>{order.recipient_name}</strong></p>
                                  <p className="snap-line">{order.address_line1}</p>
                                  {order.address_line2 && <p className="snap-line">{order.address_line2}</p>}
                                  <p className="snap-line">{order.city}, {order.postal_code}</p>
                                  {order.county_region && <p className="snap-line">{order.county_region}</p>}
                                  <p className="snap-line country">{order.country || 'United Kingdom'}</p>
                                  <p className="snap-phone"><Phone size={14} /> {order.phone_number}</p>
                                </div>
                              </div>

                              <div className="expanded-section">
                                <h4 className="expanded-section-title">
                                  <CreditCard size={16} /> Financial Breakdown
                                </h4>
                                <div className="financial-snapshot-box">
                                  <div className="fin-row">
                                    <span>Items Subtotal:</span>
                                    <span>£{parseFloat(order.subtotal).toFixed(2)}</span>
                                  </div>
                                  <div className="fin-row">
                                    <span>Delivery Fee:</span>
                                    <span>{parseFloat(order.delivery_fee) > 0 ? `£${parseFloat(order.delivery_fee).toFixed(2)}` : 'Free UK Standard'}</span>
                                  </div>
                                  <div className="fin-row total-row">
                                    <span>Final Total:</span>
                                    <span className="fin-total">£{parseFloat(order.total_amount).toFixed(2)}</span>
                                  </div>
                                  {order.notes && (
                                    <div className="order-notes-box">
                                      <strong>Delivery Notes:</strong> {order.notes}
                                    </div>
                                  )}
                                </div>
                              </div>

                              {/* Shipment Tracking Section (Only rendered when real tracking values exist) */}
                              {Boolean(order.courier_name || order.tracking_number || order.tracking_url || order.dispatched_at) && (
                                <div className="expanded-section" style={{ gridColumn: '1 / -1' }}>
                                  <h4 className="expanded-section-title">
                                    <Truck size={16} /> Shipment & Courier Tracking
                                  </h4>
                                  <div
                                    className="tracking-snapshot-box"
                                    style={{
                                      background: '#f8fafc',
                                      border: '1px solid #e2e8f0',
                                      borderRadius: '8px',
                                      padding: '1rem',
                                      display: 'grid',
                                      gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                                      gap: '0.75rem',
                                      fontSize: '0.85rem'
                                    }}
                                  >
                                    {order.courier_name && (
                                      <div>
                                        <span style={{ display: 'block', fontSize: '0.72rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>
                                          Delivery Provider
                                        </span>
                                        <strong style={{ color: '#0f172a' }}>{order.courier_name}</strong>
                                      </div>
                                    )}

                                    {order.tracking_number && (
                                      <div>
                                        <span style={{ display: 'block', fontSize: '0.72rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>
                                          Tracking Number
                                        </span>
                                        <code style={{ background: '#f1f5f9', padding: '0.2rem 0.4rem', borderRadius: '4px', fontFamily: 'monospace' }}>
                                          {order.tracking_number}
                                        </code>
                                      </div>
                                    )}

                                    {order.shipment_reference && (
                                      <div>
                                        <span style={{ display: 'block', fontSize: '0.72rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>
                                          Shipment Ref
                                        </span>
                                        <span style={{ color: '#334155' }}>{order.shipment_reference}</span>
                                      </div>
                                    )}

                                    {order.dispatched_at && (
                                      <div>
                                        <span style={{ display: 'block', fontSize: '0.72rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>
                                          Dispatched On
                                        </span>
                                        <span style={{ color: '#334155' }}>
                                          {new Date(order.dispatched_at).toLocaleDateString('en-GB', {
                                            day: 'numeric',
                                            month: 'short',
                                            year: 'numeric',
                                          })}
                                        </span>
                                      </div>
                                    )}

                                    <div>
                                      <span style={{ display: 'block', fontSize: '0.72rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>
                                        Delivery Status
                                      </span>
                                      <span
                                        style={{
                                          fontWeight: 700,
                                          color: order.order_status === 'DELIVERED' ? '#15803d' : '#0284c7'
                                        }}
                                      >
                                        {order.order_status === 'DELIVERED' ? 'Delivered' : 'Dispatched — In Transit'}
                                      </span>
                                    </div>

                                    {order.tracking_url && (order.tracking_url.startsWith('http://') || order.tracking_url.startsWith('https://')) && (
                                      <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                                        <a
                                          href={order.tracking_url}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          style={{
                                            display: 'inline-flex',
                                            alignItems: 'center',
                                            gap: '0.35rem',
                                            background: '#0f172a',
                                            color: '#ffffff',
                                            padding: '0.4rem 0.8rem',
                                            borderRadius: '6px',
                                            fontSize: '0.8rem',
                                            fontWeight: 600,
                                            textDecoration: 'none'
                                          }}
                                        >
                                          <ExternalLink size={13} /> Track Package
                                        </a>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        )}

                        <div className="order-card-footer">
                          <button
                            className="view-order-btn"
                            onClick={() => setExpandedOrderId(isExpanded ? null : order.id)}
                            aria-expanded={isExpanded}
                          >
                            {isExpanded ? (
                              <>
                                <span>Hide Details</span> <ChevronUp size={16} />
                              </>
                            ) : (
                              <>
                                <span>View Full Details</span> <ChevronDown size={16} />
                              </>
                            )}
                          </button>

                          <button
                            className="direct-page-btn"
                            onClick={() => navigate(`/orders/${order.order_reference}`)}
                            title="Open standalone order page"
                          >
                            <span>Dedicated Page</span> <ExternalLink size={14} />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* TAB 4: SECURITY */}
          {activeTab === 'security' && (
            <div className="account-tab-content">
              <div className="tab-header">
                <h2>Password & Security</h2>
                <p>Change your account password securely using Django's password controls.</p>
              </div>

              {passwordStatus && (
                <div
                  className={`status-banner ${passwordStatus.type}`}
                  role={passwordStatus.type === 'error' ? 'alert' : 'status'}
                  aria-live="polite"
                >
                  {passwordStatus.type === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
                  <span>{passwordStatus.msg}</span>
                </div>
              )}

              <form onSubmit={handlePasswordSubmit} className="password-form">
                <div className="form-group">
                  <label htmlFor="currentPassword">
                    Current Password <span className="req-star" aria-hidden="true">*</span>
                  </label>
                  <div className="input-wrapper">
                    <Lock className="input-icon" size={18} />
                    <input
                      id="currentPassword"
                      type="password"
                      value={passwordForm.currentPassword}
                      onChange={(e) => {
                        setPasswordForm({ ...passwordForm, currentPassword: e.target.value });
                        if (passwordErrors.currentPassword) {
                          setPasswordErrors((prev) => {
                            const next = { ...prev };
                            delete next.currentPassword;
                            return next;
                          });
                        }
                      }}
                      placeholder="Enter current password"
                      required
                      className={passwordErrors.currentPassword ? 'input-invalid' : ''}
                    />
                  </div>
                  {passwordErrors.currentPassword && (
                    <span className="field-error-message">{passwordErrors.currentPassword}</span>
                  )}
                </div>

                <div className="form-group">
                  <label htmlFor="newPassword">
                    New Password <span className="req-star" aria-hidden="true">*</span>
                  </label>
                  <div className="input-wrapper">
                    <Lock className="input-icon" size={18} />
                    <input
                      id="newPassword"
                      type="password"
                      value={passwordForm.newPassword}
                      onChange={(e) => {
                        setPasswordForm({ ...passwordForm, newPassword: e.target.value });
                        if (passwordErrors.newPassword) {
                          setPasswordErrors((prev) => {
                            const next = { ...prev };
                            delete next.newPassword;
                            return next;
                          });
                        }
                      }}
                      placeholder="At least 8 characters"
                      required
                      className={passwordErrors.newPassword ? 'input-invalid' : ''}
                    />
                  </div>
                  {passwordErrors.newPassword && (
                    <span className="field-error-message">{passwordErrors.newPassword}</span>
                  )}
                  <small className="field-hint">Must be at least 8 characters and not too common.</small>
                </div>

                <div className="form-group">
                  <label htmlFor="confirmPassword">
                    Confirm New Password <span className="req-star" aria-hidden="true">*</span>
                  </label>
                  <div className="input-wrapper">
                    <Lock className="input-icon" size={18} />
                    <input
                      id="confirmPassword"
                      type="password"
                      value={passwordForm.confirmPassword}
                      onChange={(e) => {
                        setPasswordForm({ ...passwordForm, confirmPassword: e.target.value });
                        if (passwordErrors.confirmPassword) {
                          setPasswordErrors((prev) => {
                            const next = { ...prev };
                            delete next.confirmPassword;
                            return next;
                          });
                        }
                      }}
                      placeholder="Repeat new password"
                      required
                      className={passwordErrors.confirmPassword ? 'input-invalid' : ''}
                    />
                  </div>
                  {passwordErrors.confirmPassword && (
                    <span className="field-error-message">{passwordErrors.confirmPassword}</span>
                  )}
                </div>

                <button type="submit" className="save-btn" disabled={isChangingPassword}>
                  {isChangingPassword ? 'Updating Password...' : 'Update Password'}
                </button>
              </form>
            </div>
          )}
        </main>
      </div>

      {/* ADDRESS MODAL */}
      {showAddressModal && (
        <div className="modal-overlay">
          <div className="modal-container">
            <div className="modal-header">
              <h3>{editingAddressId ? 'Edit Delivery Address' : 'Add New UK Delivery Address'}</h3>
              <button className="close-modal-btn" onClick={() => setShowAddressModal(false)}>
                &times;
              </button>
            </div>

            <form onSubmit={handleAddressSubmit} className="modal-form">
              <div className="form-group">
                <label>Recipient Name *</label>
                <div className="input-wrapper">
                  <UserIcon className="input-icon" size={18} />
                  <input
                    type="text"
                    value={addressForm.recipient_name}
                    onChange={(e) => setAddressForm({ ...addressForm, recipient_name: e.target.value })}
                    placeholder="Full name of recipient"
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Phone Number *</label>
                <div className="input-wrapper">
                  <Phone className="input-icon" size={18} />
                  <input
                    type="tel"
                    value={addressForm.phone_number}
                    onChange={(e) => setAddressForm({ ...addressForm, phone_number: e.target.value })}
                    placeholder="Enter your phone number"
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Address Line 1 *</label>
                <div className="input-wrapper">
                  <Building className="input-icon" size={18} />
                  <input
                    type="text"
                    value={addressForm.address_line1}
                    onChange={(e) => setAddressForm({ ...addressForm, address_line1: e.target.value })}
                    placeholder="House number and street name"
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Address Line 2 (Optional)</label>
                <div className="input-wrapper">
                  <Building className="input-icon" size={18} />
                  <input
                    type="text"
                    value={addressForm.address_line2 || ''}
                    onChange={(e) => setAddressForm({ ...addressForm, address_line2: e.target.value })}
                    placeholder="Apartment, suite, unit, etc."
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Town / City *</label>
                  <input
                    type="text"
                    value={addressForm.city}
                    onChange={(e) => setAddressForm({ ...addressForm, city: e.target.value })}
                    placeholder="London, Manchester, etc."
                    required
                  />
                </div>

                <div className="form-group">
                  <label>County / Region</label>
                  <input
                    type="text"
                    value={addressForm.county_region || ''}
                    onChange={(e) => setAddressForm({ ...addressForm, county_region: e.target.value })}
                    placeholder="Greater London, Yorkshire, etc."
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>UK Postal Code *</label>
                  <input
                    type="text"
                    value={addressForm.postal_code}
                    onChange={(e) => setAddressForm({ ...addressForm, postal_code: e.target.value.toUpperCase() })}
                    placeholder="SW1A 1AA"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Country *</label>
                  <input
                    type="text"
                    value={addressForm.country || 'United Kingdom'}
                    onChange={(e) => setAddressForm({ ...addressForm, country: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="checkbox-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={addressForm.is_default || false}
                    onChange={(e) => setAddressForm({ ...addressForm, is_default: e.target.checked })}
                  />
                  <span>Set as default delivery address</span>
                </label>
              </div>

              <div className="modal-actions">
                <button type="button" className="cancel-btn" onClick={() => setShowAddressModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="save-btn" disabled={isSubmittingAddress}>
                  {isSubmittingAddress ? 'Saving...' : 'Save Address'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
