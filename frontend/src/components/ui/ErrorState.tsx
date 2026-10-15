import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './Button';
import './ErrorState.css';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Unable to load products',
  message = 'We encountered a connection issue while reaching the AdesHub store. Please check your network connection or try again.',
  onRetry,
}) => {
  return (
    <div className="error-state" role="alert">
      <div className="error-state__header">
        <AlertTriangle className="error-state__icon" size={24} />
        <h4 className="error-state__title">{title}</h4>
      </div>
      <p className="error-state__message">{message}</p>
      {onRetry && (
        <Button
          variant="outline"
          size="sm"
          onClick={onRetry}
          icon={<RefreshCw size={14} />}
          className="error-state__retry"
        >
          Try Again
        </Button>
      )}
    </div>
  );
};
