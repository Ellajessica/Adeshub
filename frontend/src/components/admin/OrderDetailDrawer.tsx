import React, { useState, useEffect } from 'react';
import type { Order } from '../../types/api';
import { api, ApiError } from '../../services/api';
import { PaymentStatusBadge, FulfilmentStatusBadge } from './OrderStatusBadge';
import {
  X,
  User,
  MapPin,
  CreditCard,
  Package,
  Calendar,
  Phone,
  Mail,
  Copy,
  Check,
  AlertCircle,
  Truck,
  CheckCheck,
  Ban,
  ShieldAlert,
  ExternalLink,
  Save
} from 'lucide-react';
import './OrderDetailDrawer.css';

interface OrderDetailDrawerProps {
  order: Order | null;
  isOpen: boolean;
  onClose: () => void;
  onOrderUpdated: (updatedOrder: Order) => void;
}

export const OrderDetailDrawer: React.FC<OrderDetailDrawerProps> = ({
  order,
  isOpen,
  onClose,
  onOrderUpdated,
}) => {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [confirmCancel, setConfirmCancel] = useState(false);

  // Shipment / Courier tracking fields state
  const [courierName, setCourierName] = useState(order?.courier_name || '');
  const [shipmentReference, setShipmentReference] = useState(order?.shipment_reference || '');
  const [trackingNumber, setTrackingNumber] = useState(order?.tracking_number || '');
  const [trackingUrl, setTrackingUrl] = useState(order?.tracking_url || '');
  const [urlError, setUrlError] = useState<string | null>(null);

  // Sync state when order prop changes
  useEffect(() => {
    if (order) {
      setCourierName(order.courier_name || '');
      setShipmentReference(order.shipment_reference || '');
      setTrackingNumber(order.tracking_number || '');
      setTrackingUrl(order.tracking_url || '');
      setUrlError(null);
      setActionError(null);
      setActionSuccess(null);
      setConfirmCancel(false);
    }
  }, [order?.order_reference, order?.updated_at]);

  if (!isOpen || !order) return null;

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const isValidHttpUrl = (string: string): boolean => {
    const trimmed = string.trim();
    if (!trimmed) return true;
    try {
      const url = new URL(trimmed);
      return url.protocol === 'http:' || url.protocol === 'https:';
    } catch {
      return false;
    }
  };

  const handleTrackingUrlChange = (value: string) => {
    setTrackingUrl(value);
    if (value.trim() && !isValidHttpUrl(value)) {
      setUrlError("URL must begin with 'http://' or 'https://' and be a valid web address.");
    } else {
      setUrlError(null);
    }
  };

  const handleStatusChange = async (
    newStatus: string,
    additionalData?: {
      courier_name?: string;
      shipment_reference?: string;
      tracking_number?: string;
      tracking_url?: string;
    }
  ) => {
    setActionError(null);
    setActionSuccess(null);
    setIsUpdatingStatus(true);
    try {
      const payload = {
        order_status: newStatus,
        ...(additionalData || {}),
      };
      const updated = await api.updateAdminOrderStatus(order.order_reference, payload);
      onOrderUpdated(updated);
      setActionSuccess(`Order #${order.order_reference} status successfully updated to ${newStatus}.`);
      setConfirmCancel(false);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setActionError(err.message);
      } else if (err instanceof Error) {
        setActionError(err.message);
      } else {
        setActionError('Failed to update order status. Please try again.');
      }
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const handleDispatchOrder = async () => {
    if (order.payment_status !== 'PAID') {
      setActionError(`Cannot dispatch an unpaid order. Payment status is currently '${order.payment_status}'.`);
      return;
    }
    if (trackingUrl.trim() && !isValidHttpUrl(trackingUrl)) {
      setActionError("Tracking URL must start with 'http://' or 'https://' and be a valid web address.");
      return;
    }
    await handleStatusChange('SHIPPED', {
      courier_name: courierName.trim(),
      shipment_reference: shipmentReference.trim(),
      tracking_number: trackingNumber.trim(),
      tracking_url: trackingUrl.trim(),
    });
  };

  const handleSaveCourierDetails = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setActionError(null);
    setActionSuccess(null);

    if (trackingUrl.trim() && !isValidHttpUrl(trackingUrl)) {
      setActionError("Tracking URL must start with 'http://' or 'https://' and be a valid web address.");
      return;
    }

    setIsUpdatingStatus(true);
    try {
      const updated = await api.updateAdminOrderStatus(order.order_reference, {
        courier_name: courierName.trim(),
        shipment_reference: shipmentReference.trim(),
        tracking_number: trackingNumber.trim(),
        tracking_url: trackingUrl.trim(),
      });
      onOrderUpdated(updated);
      setActionSuccess(`Shipment tracking information saved for order #${order.order_reference}.`);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setActionError(err.message);
      } else if (err instanceof Error) {
        setActionError(err.message);
      } else {
        setActionError('Failed to save courier details. Please try again.');
      }
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const currentStatus = order.order_status;
  const isTerminal = currentStatus === 'DELIVERED' || currentStatus === 'CANCELLED';
  const hasExistingTracking = Boolean(
    order.courier_name ||
    order.tracking_number ||
    order.shipment_reference ||
    order.tracking_url ||
    order.dispatched_at
  );

  return (
    <div className="order-drawer-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="order-drawer-panel" onClick={(e) => e.stopPropagation()}>
        {/* Drawer Header */}
        <div className="order-drawer-header">
          <div className="header-title-block">
            <span className="order-drawer-badge">Order Details</span>
            <div className="header-ref-row">
              <h2 className="order-ref-title">#{order.order_reference}</h2>
              <button
                type="button"
                className="copy-btn"
                title="Copy reference number"
                onClick={() => handleCopy(order.order_reference, 'ref')}
              >
                {copiedKey === 'ref' ? <Check size={14} className="text-success" /> : <Copy size={14} />}
              </button>
            </div>
            <div className="order-date-row">
              <Calendar size={13} />
              <span>
                Placed on {new Date(order.created_at).toLocaleDateString('en-GB', {
                  day: 'numeric',
                  month: 'short',
                  year: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </span>
            </div>
          </div>
          <button
            type="button"
            className="drawer-close-btn"
            onClick={onClose}
            aria-label="Close order details"
          >
            <X size={20} />
          </button>
        </div>

        {/* Action Status Feedback */}
        {actionSuccess && (
          <div className="drawer-alert success-alert">
            <Check size={16} />
            <span>{actionSuccess}</span>
          </div>
        )}
        {actionError && (
          <div className="drawer-alert error-alert">
            <AlertCircle size={16} />
            <span>{actionError}</span>
          </div>
        )}

        {/* Drawer Scrollable Content */}
        <div className="order-drawer-content">
          {/* Status Bar */}
          <div className="drawer-status-summary-card">
            <div className="status-item">
              <span className="status-label">Fulfilment Status</span>
              <FulfilmentStatusBadge status={order.order_status} size="md" />
            </div>
            <div className="status-divider" />
            <div className="status-item">
              <span className="status-label">Payment Status</span>
              <PaymentStatusBadge status={order.payment_status} size="md" />
            </div>
          </div>

          {/* Fulfilment Status Stepper & Transition Controls */}
          <div className="drawer-section">
            <div className="section-header">
              <Package size={18} className="text-primary" />
              <h3 className="section-title">Fulfilment Actions</h3>
            </div>

            {/* Stepper overview */}
            <div className="fulfilment-stepper">
              {(['PENDING', 'CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED'] as const).map((step, idx) => {
                const stepOrder = ['PENDING', 'CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED'];
                const currentIdx = stepOrder.indexOf(currentStatus);
                const isPassed = currentIdx >= idx && currentStatus !== 'CANCELLED';
                const isCurrent = currentStatus === step;

                return (
                  <div
                    key={step}
                    className={`stepper-step ${isPassed ? 'passed' : ''} ${isCurrent ? 'active' : ''}`}
                  >
                    <div className="stepper-dot">
                      {isPassed ? <Check size={10} /> : idx + 1}
                    </div>
                    <span className="stepper-label">{step}</span>
                  </div>
                );
              })}
            </div>

            {/* Actions Buttons based on state machine */}
            {!isTerminal && (
              <div className="transition-actions-container">
                <p className="actions-helper-text">Advance order fulfilment stage:</p>
                <div className="action-buttons-cluster">
                  {currentStatus === 'PENDING' && (
                    <button
                      type="button"
                      className="btn-transition btn-confirm"
                      disabled={isUpdatingStatus}
                      onClick={() => handleStatusChange('CONFIRMED')}
                    >
                      <Package size={14} /> Confirm Order
                    </button>
                  )}

                  {currentStatus === 'CONFIRMED' && (
                    <button
                      type="button"
                      className="btn-transition btn-processing"
                      disabled={isUpdatingStatus}
                      onClick={() => handleStatusChange('PROCESSING')}
                    >
                      <Package size={14} /> Mark as Processing (Pick & Pack)
                    </button>
                  )}

                  {currentStatus === 'PROCESSING' && (
                    <div className="dispatch-action-wrapper">
                      <button
                        type="button"
                        className="btn-transition btn-shipped"
                        disabled={isUpdatingStatus || order.payment_status !== 'PAID'}
                        onClick={handleDispatchOrder}
                        title={order.payment_status !== 'PAID' ? 'Cannot dispatch unpaid order' : 'Dispatch order and attach tracking info'}
                      >
                        <Truck size={14} /> Dispatch / Mark as Shipped
                      </button>
                      {order.payment_status !== 'PAID' && (
                        <div className="dispatch-unpaid-warning">
                          <AlertCircle size={13} />
                          <span>Unpaid orders cannot be dispatched. Current payment status: <strong>{order.payment_status}</strong>.</span>
                        </div>
                      )}
                    </div>
                  )}

                  {currentStatus === 'SHIPPED' && (
                    <button
                      type="button"
                      className="btn-transition btn-delivered"
                      disabled={isUpdatingStatus}
                      onClick={() => handleStatusChange('DELIVERED')}
                    >
                      <CheckCheck size={14} /> Confirm Delivery Completed
                    </button>
                  )}

                  {!confirmCancel ? (
                    <button
                      type="button"
                      className="btn-transition btn-cancel"
                      disabled={isUpdatingStatus}
                      onClick={() => setConfirmCancel(true)}
                    >
                      <Ban size={14} /> Cancel Order
                    </button>
                  ) : (
                    <div className="confirm-cancel-box">
                      <span className="confirm-text">Cancel this order and restock items?</span>
                      <div className="confirm-btn-group">
                        <button
                          type="button"
                          className="btn-danger-confirm"
                          disabled={isUpdatingStatus}
                          onClick={() => handleStatusChange('CANCELLED')}
                        >
                          Yes, Cancel & Restock
                        </button>
                        <button
                          type="button"
                          className="btn-cancel-abort"
                          onClick={() => setConfirmCancel(false)}
                        >
                          Keep Order
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {isTerminal && (
              <div className="terminal-status-notice">
                <span>
                  This order is in terminal state (<strong>{currentStatus}</strong>). No further status transitions can be made.
                </span>
              </div>
            )}

            <div className="payment-security-notice">
              <ShieldAlert size={14} />
              <span>
                Payment status is managed authoritatively via Stripe webhooks and cannot be falsified or manually altered through dashboard inputs.
              </span>
            </div>
          </div>

          {/* Shipment & Courier Tracking Section */}
          <div className="drawer-section">
            <div className="section-header">
              <Truck size={18} className="text-primary" />
              <h3 className="section-title">Shipment & Courier Tracking</h3>
            </div>

            {/* Display Existing Shipment Information when available */}
            {hasExistingTracking && (
              <div className="shipment-summary-display">
                <div className="shipment-summary-header">
                  <span className="shipment-summary-badge">
                    <Truck size={12} /> Stored Shipment Details
                  </span>
                  {order.dispatched_at && (
                    <span className="dispatched-timestamp">
                      Dispatched on {new Date(order.dispatched_at).toLocaleDateString('en-GB', {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                      })}
                    </span>
                  )}
                </div>

                <div className="shipment-info-grid">
                  <div className="shipment-info-item">
                    <span className="shipment-info-label">Courier Provider</span>
                    <span className="shipment-info-value font-bold">
                      {order.courier_name || '—'}
                    </span>
                  </div>

                  <div className="shipment-info-item">
                    <span className="shipment-info-label">Shipment Reference</span>
                    <span className="shipment-info-value">
                      {order.shipment_reference || '—'}
                    </span>
                  </div>

                  <div className="shipment-info-item">
                    <span className="shipment-info-label">Tracking Number</span>
                    <div className="tracking-val-wrap">
                      <span className="shipment-info-value font-mono">
                        {order.tracking_number || '—'}
                      </span>
                      {order.tracking_number && (
                        <button
                          type="button"
                          className="copy-btn-sm"
                          onClick={() => handleCopy(order.tracking_number!, 'tracking')}
                          title="Copy tracking number"
                        >
                          {copiedKey === 'tracking' ? <Check size={12} className="text-success" /> : <Copy size={12} />}
                        </button>
                      )}
                    </div>
                  </div>

                  {order.delivered_at && (
                    <div className="shipment-info-item">
                      <span className="shipment-info-label">Delivered Date</span>
                      <span className="shipment-info-value text-success font-bold">
                        {new Date(order.delivered_at).toLocaleDateString('en-GB', {
                          day: 'numeric',
                          month: 'short',
                          year: 'numeric',
                        })}
                      </span>
                    </div>
                  )}
                </div>

                {order.tracking_url && (order.tracking_url.startsWith('http://') || order.tracking_url.startsWith('https://')) && (
                  <div className="tracking-external-link-row">
                    <a
                      href={order.tracking_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-courier-portal"
                    >
                      <ExternalLink size={14} /> Open Courier Tracking Portal
                    </a>
                  </div>
                )}
              </div>
            )}

            {/* Editable Shipment Form */}
            <form onSubmit={handleSaveCourierDetails} className="courier-management-form">
              <div className="courier-form-grid">
                <div className="courier-input-group">
                  <label htmlFor="courier-name-input">
                    Courier Provider
                  </label>
                  <input
                    id="courier-name-input"
                    type="text"
                    value={courierName}
                    onChange={(e) => setCourierName(e.target.value)}
                    placeholder="e.g. Royal Mail, DPD, DHL, Evri"
                    disabled={isUpdatingStatus || order.order_status === 'CANCELLED'}
                  />
                </div>

                <div className="courier-input-group">
                  <label htmlFor="shipment-ref-input">
                    Shipment Reference
                  </label>
                  <input
                    id="shipment-ref-input"
                    type="text"
                    value={shipmentReference}
                    onChange={(e) => setShipmentReference(e.target.value)}
                    placeholder="e.g. Consignment # or Internal ID"
                    disabled={isUpdatingStatus || order.order_status === 'CANCELLED'}
                  />
                </div>

                <div className="courier-input-group">
                  <label htmlFor="tracking-num-input">
                    Tracking Number
                  </label>
                  <input
                    id="tracking-num-input"
                    type="text"
                    value={trackingNumber}
                    onChange={(e) => setTrackingNumber(e.target.value)}
                    placeholder="e.g. GB123456789"
                    disabled={isUpdatingStatus || order.order_status === 'CANCELLED'}
                  />
                </div>

                <div className="courier-input-group">
                  <label htmlFor="tracking-url-input">
                    Tracking URL
                  </label>
                  <input
                    id="tracking-url-input"
                    type="url"
                    value={trackingUrl}
                    onChange={(e) => handleTrackingUrlChange(e.target.value)}
                    placeholder="https://track.courier.com/..."
                    className={urlError ? 'courier-input-invalid' : ''}
                    disabled={isUpdatingStatus || order.order_status === 'CANCELLED'}
                  />
                  {urlError && <span className="courier-field-error">{urlError}</span>}
                </div>
              </div>

              <div className="courier-actions-bar">
                <button
                  type="submit"
                  className="btn-save-courier"
                  disabled={isUpdatingStatus || !!urlError || order.order_status === 'CANCELLED'}
                >
                  <Save size={14} /> {isUpdatingStatus ? 'Saving Details...' : 'Save Tracking Information'}
                </button>
                <span className="courier-hint-text">
                  Tracking details can be saved at any time or automatically attached upon dispatch.
                </span>
              </div>
            </form>
          </div>

          {/* Line Items Table */}
          <div className="drawer-section">
            <div className="section-header">
              <Package size={18} className="text-primary" />
              <h3 className="section-title">Purchased Items ({order.items.length})</h3>
            </div>

            <div className="items-table-wrapper">
              <table className="items-table">
                <thead>
                  <tr>
                    <th>Product & Variant</th>
                    <th>SKU</th>
                    <th className="text-right">Unit Price</th>
                    <th className="text-center">Qty</th>
                    <th className="text-right">Line Total</th>
                  </tr>
                </thead>
                <tbody>
                  {order.items.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <div className="item-name-cell">
                          <span className="item-primary-name">{item.product_name}</span>
                          {item.variant_name && (
                            <span className="item-variant-tag">{item.variant_name}</span>
                          )}
                        </div>
                      </td>
                      <td className="item-sku-cell">{item.sku || '—'}</td>
                      <td className="text-right">£{parseFloat(item.unit_price).toFixed(2)}</td>
                      <td className="text-center font-bold">{item.quantity}</td>
                      <td className="text-right font-bold">£{parseFloat(item.line_total).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Financial Summary */}
            <div className="financial-summary-card">
              <div className="fin-row">
                <span className="fin-label">Subtotal</span>
                <span className="fin-val">£{parseFloat(order.subtotal).toFixed(2)}</span>
              </div>
              <div className="fin-row">
                <span className="fin-label">UK Delivery Fee</span>
                <span className="fin-val">
                  {parseFloat(order.delivery_fee) === 0 ? 'FREE' : `£${parseFloat(order.delivery_fee).toFixed(2)}`}
                </span>
              </div>
              <div className="fin-row grand-total-row">
                <span className="fin-label">Grand Total</span>
                <span className="fin-val-grand">£{parseFloat(order.total_amount).toFixed(2)}</span>
              </div>
            </div>
          </div>

          {/* Customer & Delivery Address Snapshot */}
          <div className="drawer-section">
            <div className="section-header">
              <MapPin size={18} className="text-primary" />
              <h3 className="section-title">Delivery Snapshot & Customer</h3>
            </div>

            <div className="customer-details-grid">
              <div className="info-card">
                <div className="info-card-header">
                  <User size={14} />
                  <span>Customer Details</span>
                </div>
                <div className="info-card-body">
                  <p className="customer-name">{order.customer_name || order.recipient_name}</p>
                  <p className="customer-meta-row">
                    <Mail size={13} />
                    <span>{order.customer_email || 'No email provided'}</span>
                  </p>
                  <p className="customer-meta-row">
                    <Phone size={13} />
                    <span>{order.phone_number || 'No phone provided'}</span>
                  </p>
                </div>
              </div>

              <div className="info-card">
                <div className="info-card-header">
                  <MapPin size={14} />
                  <span>Delivery Address</span>
                </div>
                <div className="info-card-body">
                  <p className="address-recipient font-bold">{order.recipient_name}</p>
                  <p>{order.address_line1}</p>
                  {order.address_line2 && <p>{order.address_line2}</p>}
                  <p>
                    {order.city}
                    {order.county_region ? `, ${order.county_region}` : ''}
                  </p>
                  <p className="postal-code font-bold">{order.postal_code}</p>
                  <p>{order.country || 'United Kingdom'}</p>
                </div>
              </div>
            </div>

            {order.notes && (
              <div className="order-notes-card">
                <span className="notes-label">Customer Delivery Notes:</span>
                <p className="notes-body">"{order.notes}"</p>
              </div>
            )}
          </div>

          {/* Stripe Gateway References */}
          <div className="drawer-section">
            <div className="section-header">
              <CreditCard size={18} className="text-primary" />
              <h3 className="section-title">Stripe Payment Gateway Details</h3>
            </div>

            <div className="stripe-reference-card">
              <div className="stripe-row">
                <span className="stripe-label">Stripe Checkout Session ID:</span>
                <div className="stripe-val-wrap">
                  <code className="stripe-code">
                    {order.stripe_checkout_session_id || 'Not generated or guest session'}
                  </code>
                  {order.stripe_checkout_session_id && (
                    <button
                      type="button"
                      className="copy-btn-sm"
                      onClick={() => handleCopy(order.stripe_checkout_session_id!, 'session')}
                      title="Copy Session ID"
                    >
                      {copiedKey === 'session' ? <Check size={12} className="text-success" /> : <Copy size={12} />}
                    </button>
                  )}
                </div>
              </div>

              <div className="stripe-row">
                <span className="stripe-label">Stripe Payment Intent ID:</span>
                <div className="stripe-val-wrap">
                  <code className="stripe-code">
                    {order.stripe_payment_intent_id || 'Awaiting Stripe confirmation'}
                  </code>
                  {order.stripe_payment_intent_id && (
                    <button
                      type="button"
                      className="copy-btn-sm"
                      onClick={() => handleCopy(order.stripe_payment_intent_id!, 'intent')}
                      title="Copy Payment Intent ID"
                    >
                      {copiedKey === 'intent' ? <Check size={12} className="text-success" /> : <Copy size={12} />}
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Drawer Footer */}
        <div className="order-drawer-footer">
          <button type="button" className="btn-close-drawer" onClick={onClose}>
            Close Order Panel
          </button>
        </div>
      </div>
    </div>
  );
};
