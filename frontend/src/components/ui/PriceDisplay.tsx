import React from 'react';
import './PriceDisplay.css';

interface PriceDisplayProps {
  price?: string | number;
  amount?: string | number;
  compareAtPrice?: string | number | null;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showDiscountBadge?: boolean;
  className?: string;
}

export const formatCurrency = (amount: string | number): string => {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  if (isNaN(num)) return '£0.00';
  return '£' + num.toLocaleString('en-GB', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
};

export const PriceDisplay: React.FC<PriceDisplayProps> = ({
  price,
  amount,
  compareAtPrice,
  size = 'md',
  showDiscountBadge = true,
  className = '',
}) => {
  const effectivePrice = price !== undefined ? price : (amount !== undefined ? amount : 0);
  const currentPriceNum = typeof effectivePrice === 'string' ? parseFloat(effectivePrice) : effectivePrice;
  const comparePriceNum = compareAtPrice ? (typeof compareAtPrice === 'string' ? parseFloat(compareAtPrice) : compareAtPrice) : null;

  const isOnSale = comparePriceNum !== null && comparePriceNum > currentPriceNum;
  
  let discountPercentage = 0;
  if (isOnSale && comparePriceNum) {
    discountPercentage = Math.round(((comparePriceNum - currentPriceNum) / comparePriceNum) * 100);
  }

  return (
    <div className={`price-display price-display--${size} ${className}`.trim()}>
      <span className="price-display__current">{formatCurrency(effectivePrice)}</span>
      
      {isOnSale && compareAtPrice && (
        <span className="price-display__compare">
          {formatCurrency(compareAtPrice)}
        </span>
      )}

      {showDiscountBadge && isOnSale && discountPercentage > 0 && (
        <span className="price-display__discount">
          -{discountPercentage}%
        </span>
      )}
    </div>
  );
};
