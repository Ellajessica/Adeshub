import React, { useState, useEffect } from 'react';
import type { ProductDetail } from '../../types/api';
import { api, ApiError } from '../../services/api';
import { X, Save, AlertCircle, Package } from 'lucide-react';
import './QuickStockModal.css';

interface QuickStockModalProps {
  product: ProductDetail | null;
  isOpen: boolean;
  onClose: () => void;
  onStockUpdated: (updatedProduct: ProductDetail) => void;
}

export const QuickStockModal: React.FC<QuickStockModalProps> = ({
  product,
  isOpen,
  onClose,
  onStockUpdated,
}) => {
  const [stockQuantity, setStockQuantity] = useState<number>(0);
  const [selectedVariantId, setSelectedVariantId] = useState<number | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (product) {
      if (product.has_variants && product.variants.length > 0) {
        setSelectedVariantId(product.variants[0].id);
        setStockQuantity(product.variants[0].stock_quantity);
      } else {
        setSelectedVariantId(null);
        setStockQuantity(product.stock_quantity);
      }
    }
    setError(null);
  }, [product, isOpen]);

  if (!isOpen || !product) return null;

  const handleVariantChange = (variantId: number) => {
    setSelectedVariantId(variantId);
    const v = product.variants.find((item) => item.id === variantId);
    if (v) {
      setStockQuantity(v.stock_quantity);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (stockQuantity < 0) {
      setError('Stock quantity must be a non-negative number.');
      return;
    }

    setError(null);
    setIsUpdating(true);
    try {
      const updated = await api.updateProductStock(
        product.slug,
        stockQuantity,
        selectedVariantId || undefined
      );
      onStockUpdated(updated);
      onClose();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to update stock quantity.');
      }
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div className="stock-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="stock-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="stock-modal-header">
          <div className="header-title-flex">
            <Package size={20} className="text-primary" />
            <h3 className="stock-modal-title">Adjust Stock: {product.name}</h3>
          </div>
          <button type="button" className="stock-modal-close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {error && (
          <div className="stock-modal-alert">
            <AlertCircle size={15} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="stock-modal-form">
          {product.has_variants && product.variants.length > 0 && (
            <div className="stock-form-group">
              <label htmlFor="variant-selector">Select Variant</label>
              <select
                id="variant-selector"
                value={selectedVariantId || ''}
                onChange={(e) => handleVariantChange(parseInt(e.target.value, 10))}
              >
                {product.variants.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} (Current Stock: {v.stock_quantity})
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="stock-form-group">
            <label htmlFor="stock-qty-input">New Available Units *</label>
            <input
              id="stock-qty-input"
              type="number"
              min="0"
              value={stockQuantity}
              onChange={(e) => setStockQuantity(parseInt(e.target.value, 10) || 0)}
              autoFocus
            />
          </div>

          <div className="stock-quick-actions">
            <span>Quick Adjust:</span>
            <button
              type="button"
              className="quick-adjust-btn"
              onClick={() => setStockQuantity((prev) => Math.max(0, prev - 5))}
            >
              -5
            </button>
            <button
              type="button"
              className="quick-adjust-btn"
              onClick={() => setStockQuantity((prev) => Math.max(0, prev - 1))}
            >
              -1
            </button>
            <button
              type="button"
              className="quick-adjust-btn"
              onClick={() => setStockQuantity((prev) => prev + 5)}
            >
              +5
            </button>
            <button
              type="button"
              className="quick-adjust-btn"
              onClick={() => setStockQuantity((prev) => prev + 20)}
            >
              +20
            </button>
          </div>

          <div className="stock-modal-footer">
            <button type="button" className="btn-stock-cancel" onClick={onClose} disabled={isUpdating}>
              Cancel
            </button>
            <button type="submit" className="btn-stock-submit" disabled={isUpdating}>
              <Save size={15} />
              {isUpdating ? 'Updating Stock...' : 'Save Inventory'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
