import React from 'react';
import { PackageX, SearchX, FolderX } from 'lucide-react';
import { Button } from './Button';
import './EmptyState.css';

interface EmptyStateProps {
  title?: string;
  message?: string;
  type?: 'products' | 'search' | 'categories';
  actionLabel?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  message,
  type = 'products',
  actionLabel,
  onAction,
}) => {
  const renderIcon = () => {
    switch (type) {
      case 'search':
        return <SearchX size={48} className="empty-state__icon" />;
      case 'categories':
        return <FolderX size={48} className="empty-state__icon" />;
      default:
        return <PackageX size={48} className="empty-state__icon" />;
    }
  };

  const defaultTitle = {
    products: 'No products found',
    search: 'No matching search results',
    categories: 'No categories available yet',
  }[type];

  const defaultMessage = {
    products: 'We could not find any products in this catalog view.',
    search: 'Try checking for typos or searching for a broader item name.',
    categories: 'Categories will appear here once added to the AdesHub catalog.',
  }[type];

  return (
    <div className="empty-state">
      <div className="empty-state__icon-wrapper">
        {renderIcon()}
      </div>
      <h3 className="empty-state__title">{title || defaultTitle}</h3>
      <p className="empty-state__message">{message || defaultMessage}</p>

      {actionLabel && onAction && (
        <Button variant="outline" size="sm" onClick={onAction} className="empty-state__btn">
          {actionLabel}
        </Button>
      )}
    </div>
  );
};
