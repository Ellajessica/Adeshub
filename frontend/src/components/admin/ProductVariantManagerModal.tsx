import React, { useState } from 'react';
import type { ProductDetail, ProductVariant } from '../../types/api';
import { api, ApiError } from '../../services/api';
import { X, Plus, Edit2, Trash2, Save, AlertCircle } from 'lucide-react';
import './ProductVariantManagerModal.css';

interface ProductVariantManagerModalProps {
  product: ProductDetail | null;
  isOpen: boolean;
  onClose: () => void;
  onVariantsChanged: (updatedProduct: ProductDetail) => void;
}

export const ProductVariantManagerModal: React.FC<ProductVariantManagerModalProps> = ({
  product,
  isOpen,
  onClose,
  onVariantsChanged,
}) => {
  const [editingVariantId, setEditingVariantId] = useState<number | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [variantForm, setVariantForm] = useState({
    name: '',
    sku: '',
    price: '',
    compare_at_price: '',
    stock_quantity: 0,
    is_active: true,
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !product) return null;

  const handleStartAdd = () => {
    setEditingVariantId(null);
    setVariantForm({
      name: '',
      sku: `${product.sku}-`,
      price: product.price,
      compare_at_price: '',
      stock_quantity: 0,
      is_active: true,
    });
    setShowAddForm(true);
    setError(null);
  };

  const handleStartEdit = (v: ProductVariant) => {
    setShowAddForm(false);
    setEditingVariantId(v.id);
    setVariantForm({
      name: v.name,
      sku: v.sku,
      price: v.price,
      compare_at_price: v.compare_at_price || '',
      stock_quantity: v.stock_quantity,
      is_active: v.is_active,
    });
    setError(null);
  };

  const handleCancelForm = () => {
    setShowAddForm(false);
    setEditingVariantId(null);
    setError(null);
  };

  const handleSaveVariant = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!variantForm.name.trim()) {
      setError('Variant name is required (e.g. 5kg Bag).');
      return;
    }
    if (!variantForm.sku.trim()) {
      setError('Variant SKU is required.');
      return;
    }
    if (!variantForm.price || parseFloat(variantForm.price) < 0) {
      setError('Valid price is required.');
      return;
    }
    if (variantForm.stock_quantity < 0) {
      setError('Stock quantity cannot be negative.');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: Partial<ProductVariant> = {
        name: variantForm.name.trim(),
        sku: variantForm.sku.trim().toUpperCase(),
        price: variantForm.price.trim(),
        compare_at_price: variantForm.compare_at_price.trim() || null,
        stock_quantity: variantForm.stock_quantity,
        is_active: variantForm.is_active,
      };

      if (editingVariantId) {
        await api.updateProductVariant(product.slug, editingVariantId, payload);
      } else {
        await api.createProductVariant(product.slug, payload);
      }

      const updatedProduct = await api.getProductDetail(product.slug);
      onVariantsChanged(updatedProduct);
      handleCancelForm();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to save variant.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteVariant = async (variantId: number) => {
    if (!confirm('Are you sure you want to delete this variant?')) return;
    setError(null);
    try {
      await api.deleteProductVariant(product.slug, variantId);
      const updatedProduct = await api.getProductDetail(product.slug);
      onVariantsChanged(updatedProduct);
      if (editingVariantId === variantId) handleCancelForm();
    } catch (err: unknown) {
      setError('Failed to delete variant.');
    }
  };

  return (
    <div className="variant-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="variant-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="variant-modal-header">
          <div>
            <h2 className="variant-modal-title">Product Variants: {product.name}</h2>
            <p className="variant-modal-subtitle">Manage size, weight, and volume options with independent pricing and stock</p>
          </div>
          <button type="button" className="variant-modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {error && (
          <div className="variant-modal-alert">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <div className="variant-modal-body">
          {/* Header Action */}
          <div className="variants-top-action">
            <span className="variants-count">
              Active Options: {product.variants.length}
            </span>
            {!showAddForm && !editingVariantId && (
              <button
                type="button"
                className="btn-add-variant"
                onClick={handleStartAdd}
              >
                <Plus size={14} /> Add Option (e.g. 5kg, 10kg)
              </button>
            )}
          </div>

          {/* Add / Edit Form Drawer */}
          {(showAddForm || editingVariantId) && (
            <form onSubmit={handleSaveVariant} className="variant-edit-card">
              <h4 className="edit-card-title">
                {editingVariantId ? 'Edit Option' : 'New Option'}
              </h4>

              <div className="variant-form-grid-3">
                <div className="v-group">
                  <label>Option Name *</label>
                  <input
                    type="text"
                    placeholder="e.g. 5kg Bag, 1 Litre"
                    value={variantForm.name}
                    onChange={(e) => setVariantForm({ ...variantForm, name: e.target.value })}
                  />
                </div>

                <div className="v-group">
                  <label>Option SKU *</label>
                  <input
                    type="text"
                    placeholder="e.g. OIL-001-5KG"
                    value={variantForm.sku}
                    onChange={(e) => setVariantForm({ ...variantForm, sku: e.target.value.toUpperCase() })}
                  />
                </div>

                <div className="v-group">
                  <label>Price (£) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="0.00"
                    value={variantForm.price}
                    onChange={(e) => setVariantForm({ ...variantForm, price: e.target.value })}
                  />
                </div>
              </div>

              <div className="variant-form-grid-2">
                <div className="v-group">
                  <label>Stock Quantity *</label>
                  <input
                    type="number"
                    min="0"
                    value={variantForm.stock_quantity}
                    onChange={(e) => setVariantForm({
                      ...variantForm,
                      stock_quantity: parseInt(e.target.value, 10) || 0
                    })}
                  />
                </div>

                <div className="v-group">
                  <label>Compare-at Price (£)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="Optional"
                    value={variantForm.compare_at_price}
                    onChange={(e) => setVariantForm({ ...variantForm, compare_at_price: e.target.value })}
                  />
                </div>
              </div>

              <div className="variant-form-actions">
                <button
                  type="button"
                  className="btn-v-cancel"
                  onClick={handleCancelForm}
                  disabled={isSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-v-save"
                  disabled={isSubmitting}
                >
                  <Save size={14} />
                  {isSubmitting ? 'Saving...' : editingVariantId ? 'Update Option' : 'Create Option'}
                </button>
              </div>
            </form>
          )}

          {/* Variants Table */}
          <div className="variants-table-wrap">
            <table className="variants-table">
              <thead>
                <tr>
                  <th>Option</th>
                  <th>SKU</th>
                  <th className="text-right">Price</th>
                  <th className="text-center">Stock</th>
                  <th className="text-center">Status</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {product.variants.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center empty-v-row">
                      No variants added yet. This is currently treated as a simple product.
                    </td>
                  </tr>
                ) : (
                  product.variants.map((v) => (
                    <tr key={v.id}>
                      <td className="font-bold">{v.name}</td>
                      <td className="sku-cell">{v.sku}</td>
                      <td className="text-right">£{parseFloat(v.price).toFixed(2)}</td>
                      <td className="text-center font-bold">{v.stock_quantity}</td>
                      <td className="text-center">
                        <span className={`v-status-pill ${v.is_active ? 'v-active' : 'v-inactive'}`}>
                          {v.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="text-right">
                        <div className="v-action-btn-group">
                          <button
                            type="button"
                            className="v-action-btn edit"
                            onClick={() => handleStartEdit(v)}
                            title="Edit variant"
                          >
                            <Edit2 size={13} />
                          </button>
                          <button
                            type="button"
                            className="v-action-btn delete"
                            onClick={() => handleDeleteVariant(v.id)}
                            title="Delete variant"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="variant-modal-footer">
          <button type="button" className="btn-modal-close" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
