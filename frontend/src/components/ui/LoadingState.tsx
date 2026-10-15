import React from 'react';
import './LoadingState.css';

interface LoadingStateProps {
  type?: 'product-grid' | 'category-grid' | 'detail' | 'inline' | 'spinner';
  count?: number;
  message?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  type = 'product-grid',
  count = 8,
  message = 'Loading AdesHub catalog...'
}) => {
  if (type === 'spinner' || type === 'inline') {
    return (
      <div className="loading-inline" role="status">
        <div className="loading-spinner" />
        {message && <span className="loading-message">{message}</span>}
      </div>
    );
  }

  if (type === 'category-grid') {
    return (
      <div className="skeleton-grid skeleton-grid--categories" aria-label="Loading categories">
        {Array.from({ length: count }).map((_, idx) => (
          <div key={idx} className="skeleton-card skeleton-category">
            <div className="skeleton-box skeleton-category__image" />
            <div className="skeleton-box skeleton-title" />
            <div className="skeleton-box skeleton-text" />
          </div>
        ))}
      </div>
    );
  }

  if (type === 'detail') {
    return (
      <div className="skeleton-detail-layout" aria-label="Loading product details">
        <div className="skeleton-box skeleton-detail__image" />
        <div className="skeleton-detail__info">
          <div className="skeleton-box skeleton-badge" />
          <div className="skeleton-box skeleton-title-lg" />
          <div className="skeleton-box skeleton-price" />
          <div className="skeleton-box skeleton-text" />
          <div className="skeleton-box skeleton-text" />
          <div className="skeleton-box skeleton-btn" />
        </div>
      </div>
    );
  }

  return (
    <div className="skeleton-grid skeleton-grid--products" aria-label="Loading products">
      {Array.from({ length: count }).map((_, idx) => (
        <div key={idx} className="skeleton-card skeleton-product">
          <div className="skeleton-box skeleton-product__image" />
          <div className="skeleton-product__content">
            <div className="skeleton-box skeleton-badge" />
            <div className="skeleton-box skeleton-title" />
            <div className="skeleton-box skeleton-price" />
            <div className="skeleton-box skeleton-btn" />
          </div>
        </div>
      ))}
    </div>
  );
};
