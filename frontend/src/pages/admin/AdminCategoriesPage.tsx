import React, { useState, useEffect, useCallback } from 'react';
import { api, ApiError } from '../../services/api';
import type { Category } from '../../types/api';
import {
  Layers,
  Plus,
  Edit2,
  Trash2,
  Save,
  X,
  AlertCircle,
  RefreshCw,
  FolderTree
} from 'lucide-react';
import './AdminCategoriesPage.css';

export const AdminCategoriesPage: React.FC = () => {
  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [categoryForm, setCategoryForm] = useState({
    name: '',
    description: '',
    is_active: true,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const fetchCategories = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const cats = await api.getCategories();
      setCategories(cats);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to load categories.');
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  const handleOpenCreate = () => {
    setEditingCategory(null);
    setCategoryForm({ name: '', description: '', is_active: true });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (c: Category) => {
    setEditingCategory(c);
    setCategoryForm({
      name: c.name,
      description: c.description || '',
      is_active: c.is_active,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSubmitForm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!categoryForm.name.trim()) {
      setFormError('Category name is required.');
      return;
    }

    setFormError(null);
    setIsSubmitting(true);
    try {
      if (editingCategory) {
        await api.updateCategory(editingCategory.slug, {
          name: categoryForm.name.trim(),
          description: categoryForm.description.trim(),
          is_active: categoryForm.is_active,
        });
      } else {
        await api.createCategory({
          name: categoryForm.name.trim(),
          description: categoryForm.description.trim(),
          is_active: categoryForm.is_active,
        });
      }
      setIsModalOpen(false);
      fetchCategories();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setFormError(err.message);
      } else {
        setFormError('Failed to save category.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteCategory = async (c: Category) => {
    if (!confirm(`Are you sure you want to delete category "${c.name}"? Products assigned to this category will become uncategorized.`)) {
      return;
    }
    try {
      await api.deleteCategory(c.slug);
      fetchCategories();
    } catch {
      alert('Failed to delete category.');
    }
  };

  return (
    <div className="admin-categories-page">
      <div className="categories-page-header">
        <div>
          <h1 className="categories-page-title">Category Management</h1>
          <p className="categories-page-subtitle">
            Organize products into intuitive collections for grocery shoppers
          </p>
        </div>

        <div className="categories-header-actions">
          <button
            type="button"
            className="btn-refresh-cats"
            onClick={fetchCategories}
            disabled={isLoading}
            title="Refresh categories"
          >
            <RefreshCw size={15} />
            <span>Refresh</span>
          </button>
          <button type="button" className="btn-add-cat" onClick={handleOpenCreate}>
            <Plus size={16} />
            <span>Add Category</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="categories-alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Categories Cards Grid */}
      <div className="categories-table-card">
        <div className="categories-table-scroll">
          <table className="categories-table">
            <thead>
              <tr>
                <th>Category Name</th>
                <th>Slug</th>
                <th>Description</th>
                <th className="text-center">Products Count</th>
                <th className="text-center">Visibility</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="table-loading-cell">
                    <div className="admin-spinner" />
                    <span>Loading categories...</span>
                  </td>
                </tr>
              ) : categories.length === 0 ? (
                <tr>
                  <td colSpan={6} className="table-empty-cell">
                    <Layers size={32} className="text-muted" />
                    <p>No categories created yet.</p>
                  </td>
                </tr>
              ) : (
                categories.map((cat) => (
                  <tr key={cat.id} className="category-row">
                    <td className="cat-name-cell font-bold">
                      <FolderTree size={16} className="cat-icon" />
                      <span>{cat.name}</span>
                    </td>
                    <td className="cat-slug-cell font-mono">{cat.slug}</td>
                    <td className="cat-desc-cell">{cat.description || '—'}</td>
                    <td className="text-center font-bold">{cat.product_count ?? '—'}</td>
                    <td className="text-center">
                      <span className={`cat-status-pill ${cat.is_active ? 'cat-active' : 'cat-inactive'}`}>
                        {cat.is_active ? 'Active' : 'Hidden'}
                      </span>
                    </td>
                    <td className="text-right">
                      <div className="cat-actions-group">
                        <button
                          type="button"
                          className="btn-cat-action edit"
                          onClick={() => handleOpenEdit(cat)}
                          title="Edit Category"
                        >
                          <Edit2 size={14} />
                        </button>
                        <button
                          type="button"
                          className="btn-cat-action delete"
                          onClick={() => handleDeleteCategory(cat)}
                          title="Delete Category"
                        >
                          <Trash2 size={14} />
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

      {/* Category Create/Edit Modal */}
      {isModalOpen && (
        <div className="cat-modal-backdrop" onClick={() => setIsModalOpen(false)}>
          <div className="cat-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="cat-modal-header">
              <h3 className="cat-modal-title">
                {editingCategory ? `Edit Category: ${editingCategory.name}` : 'New Category'}
              </h3>
              <button type="button" className="cat-modal-close" onClick={() => setIsModalOpen(false)}>
                <X size={18} />
              </button>
            </div>

            {formError && (
              <div className="cat-modal-alert">
                <AlertCircle size={16} />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleSubmitForm} className="cat-modal-form">
              <div className="cat-form-group">
                <label htmlFor="cat-name-input">Category Name *</label>
                <input
                  id="cat-name-input"
                  type="text"
                  placeholder="e.g. Fresh Tubers & Vegetables"
                  value={categoryForm.name}
                  onChange={(e) => setCategoryForm({ ...categoryForm, name: e.target.value })}
                  autoFocus
                />
              </div>

              <div className="cat-form-group">
                <label htmlFor="cat-desc-input">Description</label>
                <textarea
                  id="cat-desc-input"
                  rows={3}
                  placeholder="Brief description for category banner and SEO"
                  value={categoryForm.description}
                  onChange={(e) => setCategoryForm({ ...categoryForm, description: e.target.value })}
                />
              </div>

              <div className="cat-form-group">
                <label className="toggle-label">
                  <input
                    type="checkbox"
                    checked={categoryForm.is_active}
                    onChange={(e) => setCategoryForm({ ...categoryForm, is_active: e.target.checked })}
                  />
                  <span>Active & Visible in Navigation</span>
                </label>
              </div>

              <div className="cat-modal-footer">
                <button
                  type="button"
                  className="btn-cat-cancel"
                  onClick={() => setIsModalOpen(false)}
                  disabled={isSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-cat-save"
                  disabled={isSubmitting}
                >
                  <Save size={15} />
                  {isSubmitting ? 'Saving...' : editingCategory ? 'Update Category' : 'Create Category'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
