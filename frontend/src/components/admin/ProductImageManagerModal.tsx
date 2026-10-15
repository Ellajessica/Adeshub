import React, { useState } from 'react';
import type { ProductDetail } from '../../types/api';
import { api, ApiError } from '../../services/api';
import { X, Upload, Trash2, Star, AlertCircle, Image as ImageIcon } from 'lucide-react';
import './ProductImageManagerModal.css';

interface ProductImageManagerModalProps {
  product: ProductDetail | null;
  isOpen: boolean;
  onClose: () => void;
  onImagesChanged: (updatedProduct: ProductDetail) => void;
}

export const ProductImageManagerModal: React.FC<ProductImageManagerModalProps> = ({
  product,
  isOpen,
  onClose,
  onImagesChanged,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [altText, setAltText] = useState('');
  const [isPrimary, setIsPrimary] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !product) return null;

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Please select an image file to upload.');
      return;
    }

    setError(null);
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('image', selectedFile);
      if (altText.trim()) formData.append('alt_text', altText.trim());
      formData.append('is_primary', isPrimary ? 'true' : 'false');

      await api.createProductImage(product.slug, formData);

      // Re-fetch product to get updated images list
      const updatedProduct = await api.getProductDetail(product.slug);
      onImagesChanged(updatedProduct);

      setSelectedFile(null);
      setAltText('');
      setIsPrimary(false);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to upload image. Please try again.');
      }
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (imageId: number) => {
    if (!confirm('Are you sure you want to delete this product image?')) return;
    setError(null);
    try {
      await api.deleteProductImage(product.slug, imageId);
      const updatedProduct = await api.getProductDetail(product.slug);
      onImagesChanged(updatedProduct);
    } catch (err: unknown) {
      setError('Failed to delete image.');
    }
  };

  return (
    <div className="img-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="img-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="img-modal-header">
          <div>
            <h2 className="img-modal-title">Manage Images: {product.name}</h2>
            <p className="img-modal-subtitle">Upload product photos, choose primary thumbnail, or remove images</p>
          </div>
          <button type="button" className="img-modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {error && (
          <div className="img-modal-alert">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <div className="img-modal-body">
          {/* Current Images Grid */}
          <div className="current-images-section">
            <h4 className="section-label">Uploaded Images ({product.images.length})</h4>
            {product.images.length === 0 ? (
              <div className="empty-images-placeholder">
                <ImageIcon size={32} className="text-muted" />
                <p>No product images uploaded yet.</p>
              </div>
            ) : (
              <div className="images-grid">
                {product.images.map((img) => (
                  <div key={img.id} className="image-card">
                    <div className="image-thumb-wrap">
                      <img src={img.image} alt={img.alt_text || product.name} className="image-thumb" />
                      {img.is_primary && (
                        <span className="primary-pill" title="Primary Catalog Thumbnail">
                          <Star size={10} /> Primary
                        </span>
                      )}
                    </div>
                    <div className="image-card-actions">
                      <span className="image-alt-caption">{img.alt_text || 'No alt text'}</span>
                      <button
                        type="button"
                        className="btn-delete-img"
                        onClick={() => handleDelete(img.id)}
                        title="Delete image"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Upload New Image Form */}
          <div className="upload-form-section">
            <h4 className="section-label">Upload New Photo</h4>
            <form onSubmit={handleUpload} className="upload-form">
              <div className="file-input-wrapper">
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/avif"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  id="img-file-input"
                />
              </div>

              <div className="upload-meta-row">
                <input
                  type="text"
                  placeholder="Alt text (e.g. Front view of 5kg bag)"
                  value={altText}
                  onChange={(e) => setAltText(e.target.value)}
                  className="alt-input"
                />

                <label className="primary-toggle-label">
                  <input
                    type="checkbox"
                    checked={isPrimary}
                    onChange={(e) => setIsPrimary(e.target.checked)}
                  />
                  <span>Set as Primary Thumbnail</span>
                </label>
              </div>

              <button
                type="submit"
                className="btn-upload-submit"
                disabled={isUploading || !selectedFile}
              >
                <Upload size={14} />
                {isUploading ? 'Uploading Image...' : 'Upload Image'}
              </button>
            </form>
          </div>
        </div>

        <div className="img-modal-footer">
          <button type="button" className="btn-modal-close" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
