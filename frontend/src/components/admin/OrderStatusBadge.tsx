import React from 'react';
import {
  CheckCircle2,
  Clock,
  XCircle,
  RotateCcw,
  Package,
  Truck,
  CheckCheck,
  AlertTriangle
} from 'lucide-react';
import './OrderStatusBadge.css';

interface PaymentBadgeProps {
  status: 'PENDING' | 'PAID' | 'FAILED' | 'REFUNDED' | string;
  size?: 'sm' | 'md';
}

interface FulfilmentBadgeProps {
  status: 'PENDING' | 'CONFIRMED' | 'PROCESSING' | 'SHIPPED' | 'DELIVERED' | 'CANCELLED' | string;
  size?: 'sm' | 'md';
}

export const PaymentStatusBadge: React.FC<PaymentBadgeProps> = ({ status, size = 'md' }) => {
  const norm = status?.toUpperCase() || 'PENDING';

  switch (norm) {
    case 'PAID':
      return (
        <span className={`status-badge payment-paid size-${size}`}>
          <CheckCircle2 size={size === 'sm' ? 12 : 14} className="badge-icon" />
          <span>Paid</span>
        </span>
      );
    case 'PENDING':
      return (
        <span className={`status-badge payment-pending size-${size}`}>
          <Clock size={size === 'sm' ? 12 : 14} className="badge-icon" />
          <span>Payment Pending</span>
        </span>
      );
    case 'REFUNDED':
      return (
        <span className={`status-badge payment-refunded size-${size}`}>
          <RotateCcw size={size === 'sm' ? 12 : 14} className="badge-icon" />
          <span>Refunded</span>
        </span>
      );
    case 'FAILED':
      return (
        <span className={`status-badge payment-failed size-${size}`}>
          <XCircle size={size === 'sm' ? 12 : 14} className="badge-icon" />
          <span>Failed</span>
        </span>
      );
    default:
      return (
        <span className={`status-badge payment-neutral size-${size}`}>
          <span>{norm}</span>
        </span>
      );
  }
};

export const FulfilmentStatusBadge: React.FC<FulfilmentBadgeProps> = ({ status, size = 'md' }) => {
  const norm = status?.toUpperCase() || 'PENDING';

  switch (norm) {
    case 'CONFIRMED':
      return (
        <span className={`status-badge fulfilment-confirmed size-${size}`}>
          <CheckCircle2 size={size === 'sm' ? 12 : 14} className="badge-icon" />
          <span>Confirmed</span>
        </span>
      );
    case 'PROCESSING':
      return (
        <span className={`status-badge fulfilment-processing size-${size}`}>
          <Package size={size === 'sm' ? 12 : 14} className="badge-icon" />
          <span>Processing</span>
        </span>
      );
    case 'SHIPPED':
      return (
        <span className={`status-badge fulfilment-shipped size-${size}`}>
          <Truck size={size === 'sm' ? 12 : 14} className="badge-icon" />
          <span>Dispatched / Shipped</span>
        </span>
      );
    case 'DELIVERED':
      return (
        <span className={`status-badge fulfilment-delivered size-${size}`}>
          <CheckCheck size={size === 'sm' ? 12 : 14} className="badge-icon" />
          <span>Delivered</span>
        </span>
      );
    case 'CANCELLED':
      return (
        <span className={`status-badge fulfilment-cancelled size-${size}`}>
          <XCircle size={size === 'sm' ? 12 : 14} className="badge-icon" />
          <span>Cancelled</span>
        </span>
      );
    case 'PENDING':
    default:
      return (
        <span className={`status-badge fulfilment-pending size-${size}`}>
          <AlertTriangle size={size === 'sm' ? 12 : 14} className="badge-icon" />
          <span>Pending Review</span>
        </span>
      );
  }
};
