import React, { useState, useEffect } from 'react';
import type { Category, ProductDetail } from '../../types/api';
import type { ProductFormData } from '../../types/admin';
import { api, ApiError } from '../../services/api';
import { X, Save, AlertCircle } from 'lucide-react';
import './ProductFormModal.css';

interface ProductFormModalProps {
  product: ProductDetail | null; // null means create mode
  categories: Category[];
  isOpen: boolean;
  onClose: () => void;
  onSaved: (savedProduct: ProductDetail) => void;
}

export const ProductFormModal: React.FC<ProductFormModalProps> = ({
  product,
  categories,
  isOpen,
  onClose,
  onSaved,
}) => {
  const isEditMode = Boolean(product);

  const [formData, setFormData] = useState<ProductFormData>({
    name: '',
    category_id: null,
    sku: '',
    price: '',
    compare_at_price: '',
    stock_quantity: 0,
    low_stock_threshold: 5,
    is_active: true,
    is_featured: false,
    description: '',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (product) {
      setFormData({
        name: product.name,
        category_id: product.category ? product.category.id : null,
        sku: product.sku,
        price: product.price,
        compare_at_price: product.compare_at_price || '',
        stock_quantity: product.stock_quantity,
        low_stock_threshold: product.low_stock_threshold || 5,
        is_active: product.is_active,
        is_featured: product.is_featured,
        description: product.description || '',
      });
    } else {
      setFormData({
        name: '',
        category_id: categories.length > 0 ? categories[0].id : null,
        sku: '',
        price: '',
        compare_at_price: '',
        stock_quantity: 0,
        low_stock_threshold: 5,
        is_active: true,
        is_featured: false,
        description: '',
      });
    }
    setErrorMessage(null);
    setFieldErrors({});
  }, [product, categories, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setFieldErrors({});

    // Client-side quick checks
    const errors: Record<string, string> = {};
    if (!formData.name.trim()) errors.name = 'Product name is required.';
    if (!formData.sku.trim()) errors.sku = 'SKU is required.';
    if (!formData.price.trim() || parseFloat(formData.price) < 0) errors.price = 'Valid price is required (0.00 or higher).';
    if (formData.stock_quantity < 0) errors.stock_quantity = 'Stock quantity cannot be negative.';
    if (formData.low_stock_threshold < 0) errors.low_stock_threshold = 'Threshold cannot be negative.';

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: Record<string, unknown> = {
        name: formData.name.trim(),
        sku: formData.sku.trim().toUpperCase(),
        price: formData.price.trim(),
        stock_quantity: formData.stock_quantity,
        low_stock_threshold: formData.low_stock_threshold,
        is_active: formData.is_active,
        is_featured: formData.is_featured,
        description: formData.description.trim(),
      };

      if (formData.category_id) {
        payload.category_id = formData.category_id;
      }
      if (formData.compare_at_price.trim()) {
        payload.compare_at_price = formData.compare_at_price.trim();
      } else {
        payload.compare_at_price = null;
      }

      let res: ProductDetail;
      if (isEditMode && product) {
        res = await api.updateProduct(product.slug, payload);
      } else {
        res = await api.createProduct(payload);
      }

      onSaved(res);
      onClose();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
        if (err.fieldErrors) setFieldErrors(err.fieldErrors);
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to save product. Please check input values.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="product-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="product-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="product-modal-header">
          <div>
            <h2 className="product-modal-title">
              {isEditMode ? `Edit Product: ${product?.name}` : 'Add New Product'}
            </h2>
            <p className="product-modal-subtitle">
              {isEditMode ? 'Update product pricing, inventory thresholds, and catalog details.' : 'Create a new grocery item in the catalog.'}
            </p>
          </div>
          <button type="button" className="product-modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {errorMessage && (
          <div className="modal-alert-error">
            <AlertCircle size={16} />
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="product-modal-form">
          <div className="form-grid-2">
            <div className="form-group">
              <label htmlFor="prod-name">Product Name *</label>
              <input
                id="prod-name"
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., Premium Nigerian Brown Beans"
                className={fieldErrors.name ? 'input-error' : ''}
              />
              {fieldErrors.name && <span className="field-error-text">{fieldErrors.name}</span>}
            </div>

            <div className="form-group">
              <label htmlFor="prod-sku">Stock Keeping Unit (SKU) *</label>
              <input
                id="prod-sku"
                type="text"
                value={formData.sku}
                onChange={(e) => setFormData({ ...formData, sku: e.target.value.toUpperCase() })}
                placeholder="e.g., BNS-001"
                className={fieldErrors.sku ? 'input-error' : ''}
              />
              {fieldErrors.sku && <span className="field-error-text">{fieldErrors.sku}</span>}
            </div>
          </div>

          <div className="form-grid-3">
            <div className="form-group">
              <label htmlFor="prod-cat">Category</label>
              <select
                id="prod-cat"
                value={formData.category_id || ''}
                onChange={(e) => setFormData({
                  ...formData,
                  category_id: e.target.value ? parseInt(e.target.value, 10) : null
                })}
              >
                <option value="">No Category</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="prod-price">Price (£) *</label>
              <input
                id="prod-price"
                type="number"
                step="0.01"
                min="0"
                value={formData.price}
                onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                placeholder="0.00"
                className={fieldErrors.price ? 'input-error' : ''}
              />
              {fieldErrors.price && <span className="field-error-text">{fieldErrors.price}</span>}
            </div>

            <div className="form-group">
              <label htmlFor="prod-compare-price">Compare-at Price (£)</label>
              <input
                id="prod-compare-price"
                type="number"
                step="0.01"
                min="0"
                value={formData.compare_at_price}
                onChange={(e) => setFormData({ ...formData, compare_at_price: e.target.value })}
                placeholder="Original / Was Price"
              />
            </div>
          </div>

          <div className="form-grid-2">
            <div className="form-group">
              <label htmlFor="prod-stock">Stock Quantity *</label>
              <input
                id="prod-stock"
                type="number"
                min="0"
                value={formData.stock_quantity}
                onChange={(e) => setFormData({
                  ...formData,
                  stock_quantity: parseInt(e.target.value, 10) || 0
                })}
                className={fieldErrors.stock_quantity ? 'input-error' : ''}
              />
              {fieldErrors.stock_quantity && <span className="field-error-text">{fieldErrors.stock_quantity}</span>}
            </div>

            <div className="form-group">
              <label htmlFor="prod-threshold">Low Stock Alert Threshold *</label>
              <input
                id="prod-threshold"
                type="number"
                min="0"
                value={formData.low_stock_threshold}
                onChange={(e) => setFormData({
                  ...formData,
                  low_stock_threshold: parseInt(e.target.value, 10) || 0
                })}
                className={fieldErrors.low_stock_threshold ? 'input-error' : ''}
              />
              {fieldErrors.low_stock_threshold && <span className="field-error-text">{fieldErrors.low_stock_threshold}</span>}
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="prod-desc">Description</label>
            <textarea
              id="prod-desc"
              rows={3}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Product details, origins, storage instructions..."
            />
          </div>

          <div className="form-toggles-row">
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              />
              <span>Active in Storefront (Visible to Customers)</span>
            </label>

            <label className="toggle-label">
              <input
                type="checkbox"
                checked={formData.is_featured}
                onChange={(e) => setFormData({ ...formData, is_featured: e.target.checked })}
              />
              <span>Featured on Homepage</span>
            </label>
          </div>

          <div className="product-modal-footer">
            <button
              type="button"
              className="btn-modal-cancel"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-modal-submit"
              disabled={isSubmitting}
            >
              <Save size={16} />
              {isSubmitting ? 'Saving Product...' : isEditMode ? 'Save Changes' : 'Create Product'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
