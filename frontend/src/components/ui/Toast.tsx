import React from 'react';
import { CheckCircle, AlertCircle, Info, X } from 'lucide-react';
import type { ToastNotice } from '../../context/CartContext';
import './Toast.css';

interface ToastProps {
  toast: ToastNotice | null;
  onClose: () => void;
}

export const Toast: React.FC<ToastProps> = ({ toast, onClose }) => {
  if (!toast) return null;

  const icon = () => {
    switch (toast.type) {
      case 'success':
        return <CheckCircle className="toast__icon toast__icon--success" size={20} />;
      case 'error':
        return <AlertCircle className="toast__icon toast__icon--error" size={20} />;
      default:
        return <Info className="toast__icon toast__icon--info" size={20} />;
    }
  };

  return (
    <div className={`toast toast--${toast.type}`} role="alert">
      <div className="toast__content">
        {icon()}
        <span className="toast__message">{toast.text}</span>
      </div>
      <button onClick={onClose} className="toast__close-btn" aria-label="Close notification">
        <X size={16} />
      </button>
    </div>
  );
};
