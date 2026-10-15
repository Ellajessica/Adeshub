import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api, ApiError } from '../../services/api';
import type { Category, ProductDetail, PaginatedResponse } from '../../types/api';
import type { AdminProductFilterParams } from '../../types/admin';
import { ProductFormModal } from '../../components/admin/ProductFormModal';
import { ProductImageManagerModal } from '../../components/admin/ProductImageManagerModal';
import { ProductVariantManagerModal } from '../../components/admin/ProductVariantManagerModal';
import { QuickStockModal } from '../../components/admin/QuickStockModal';
import {
  Package,
  Plus,
  Search,
  Edit2,
  Trash2,
  Image as ImageIcon,
  Layers,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  X,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Star
} from 'lucide-react';
import './AdminProductsPage.css';

export const AdminProductsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  const [selectedCategory, setSelectedCategory] = useState(searchParams.get('category') || '');
  const [stockStatus, setStockStatus] = useState(searchParams.get('stock_status') || 'all');
  const [isActiveFilter, setIsActiveFilter] = useState(searchParams.get('is_active') || 'all');
  const [currentPage, setCurrentPage] = useState(parseInt(searchParams.get('page') || '1', 10));
  const [pageSize, setPageSize] = useState(10);

  // Data
  const [productsData, setProductsData] = useState<PaginatedResponse<ProductDetail>>({
    count: 0,
    next: null,
    previous: null,
    results: [],
  });
  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals state
  const [isFormModalOpen, setIsFormModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<ProductDetail | null>(null);

  const [isImageModalOpen, setIsImageModalOpen] = useState(false);
  const [imageProduct, setImageProduct] = useState<ProductDetail | null>(null);

  const [isVariantModalOpen, setIsVariantModalOpen] = useState(false);
  const [variantProduct, setVariantProduct] = useState<ProductDetail | null>(null);

  const [isStockModalOpen, setIsStockModalOpen] = useState(false);
  const [stockProduct, setStockProduct] = useState<ProductDetail | null>(null);

  // Load categories
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const cats = await api.getCategories();
        setCategories(cats);
      } catch {
        // ignore
      }
    };
    fetchCategories();
  }, []);

  const fetchProducts = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params: AdminProductFilterParams = {
        page: currentPage,
        page_size: pageSize,
      };
      if (searchQuery.trim()) params.search = searchQuery.trim();
      if (selectedCategory) params.category = selectedCategory;
      if (stockStatus && stockStatus !== 'all') params.stock_status = stockStatus;
      if (isActiveFilter && isActiveFilter !== 'all') params.is_active = isActiveFilter;

      const res = await api.getAdminProducts(params);
      setProductsData(res);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to load products.');
      }
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, pageSize, searchQuery, selectedCategory, stockStatus, isActiveFilter]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  // Sync with searchParams
  useEffect(() => {
    const params: Record<string, string> = {};
    if (searchQuery) params.search = searchQuery;
    if (selectedCategory) params.category = selectedCategory;
    if (stockStatus && stockStatus !== 'all') params.stock_status = stockStatus;
    if (isActiveFilter && isActiveFilter !== 'all') params.is_active = isActiveFilter;
    if (currentPage > 1) params.page = String(currentPage);
    setSearchParams(params, { replace: true });
  }, [searchQuery, selectedCategory, stockStatus, isActiveFilter, currentPage, setSearchParams]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    fetchProducts();
  };

  const handleClearFilters = () => {
    setSearchQuery('');
    setSelectedCategory('');
    setStockStatus('all');
    setIsActiveFilter('all');
    setCurrentPage(1);
  };

  // Create Product handler
  const handleAddNew = () => {
    setEditingProduct(null);
    setIsFormModalOpen(true);
  };

  // Edit Product handler
  const handleEdit = (p: ProductDetail) => {
    setEditingProduct(p);
    setIsFormModalOpen(true);
  };

  // Manage Images handler
  const handleManageImages = (p: ProductDetail) => {
    setImageProduct(p);
    setIsImageModalOpen(true);
  };

  // Manage Variants handler
  const handleManageVariants = (p: ProductDetail) => {
    setVariantProduct(p);
    setIsVariantModalOpen(true);
  };

  // Quick Stock handler
  const handleAdjustStock = (p: ProductDetail) => {
    setStockProduct(p);
    setIsStockModalOpen(true);
  };

  // Delete product handler
  const handleDeleteProduct = async (p: ProductDetail) => {
    if (!confirm(`Are you sure you want to delete product "${p.name}"? This action cannot be undone.`)) {
      return;
    }
    try {
      await api.deleteProduct(p.slug);
      fetchProducts();
    } catch {
      alert('Failed to delete product. Please try again.');
    }
  };

  // Callback when product is created or edited
  const handleProductSaved = () => {
    fetchProducts();
  };

  // Callback when images/variants/stock updated
  const handleProductUpdated = (updated: ProductDetail) => {
    setProductsData((prev) => ({
      ...prev,
      results: prev.results.map((p) => (p.slug === updated.slug ? updated : p)),
    }));
  };

  const hasActiveFilters = Boolean(
    searchQuery ||
    selectedCategory ||
    (stockStatus && stockStatus !== 'all') ||
    (isActiveFilter && isActiveFilter !== 'all')
  );

  const totalCount = productsData.count;
  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  return (
    <div className="admin-products-page">
      {/* Header Row */}
      <div className="products-page-header">
        <div>
          <h1 className="products-page-title">Products & Inventory</h1>
          <p className="products-page-subtitle">
            Manage catalogue items, stock thresholds, pricing, product options, and visual gallery
          </p>
        </div>

        <div className="products-header-actions">
          <button
            type="button"
            className="btn-refresh-products"
            onClick={fetchProducts}
            disabled={isLoading}
            title="Refresh product list"
          >
            <RefreshCw size={15} />
            <span>Refresh</span>
          </button>
          <button type="button" className="btn-add-product" onClick={handleAddNew}>
            <Plus size={16} />
            <span>Add New Product</span>
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="products-filter-card">
        <form onSubmit={handleSearchSubmit} className="search-row">
          <div className="search-wrap">
            <Search size={18} className="search-icon" />
            <input
              type="text"
              placeholder="Search product by name, SKU, description..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
            {searchQuery && (
              <button
                type="button"
                className="clear-search-btn"
                onClick={() => {
                  setSearchQuery('');
                  setCurrentPage(1);
                }}
              >
                <X size={15} />
              </button>
            )}
          </div>
          <button type="submit" className="btn-search-apply">
            Search
          </button>
        </form>

        <div className="filters-row">
          {/* Category Dropdown */}
          <div className="filter-select-group">
            <label htmlFor="cat-filter">Category</label>
            <select
              id="cat-filter"
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="">All Categories</option>
              {categories.map((c) => (
                <option key={c.id} value={c.slug}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          {/* Stock Status Dropdown */}
          <div className="filter-select-group">
            <label htmlFor="stock-filter">Stock Status</label>
            <select
              id="stock-filter"
              value={stockStatus}
              onChange={(e) => {
                setStockStatus(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="all">All Inventory States</option>
              <option value="in_stock">In Stock (&gt; 0)</option>
              <option value="low_stock">Low Stock Alerts</option>
              <option value="out_of_stock">Out of Stock (0)</option>
            </select>
          </div>

          {/* Visibility Dropdown */}
          <div className="filter-select-group">
            <label htmlFor="active-filter">Storefront Visibility</label>
            <select
              id="active-filter"
              value={isActiveFilter}
              onChange={(e) => {
                setIsActiveFilter(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="all">All Visibility States</option>
              <option value="true">Active (Published)</option>
              <option value="false">Inactive (Draft / Hidden)</option>
            </select>
          </div>
        </div>

        {hasActiveFilters && (
          <div className="active-filters-bar">
            <span>Filter parameters active</span>
            <button type="button" className="btn-reset-filters" onClick={handleClearFilters}>
              <X size={13} /> Reset Filters
            </button>
          </div>
        )}
      </div>

      {/* Products Table Card */}
      <div className="products-table-card">
        {error && (
          <div className="table-error-banner">
            <AlertTriangle size={16} />
            <span>{error}</span>
          </div>
        )}

        <div className="products-table-scroll">
          <table className="products-table">
            <thead>
              <tr>
                <th>Product</th>
                <th>SKU</th>
                <th>Category</th>
                <th className="text-right">Price</th>
                <th className="text-center">Stock Level</th>
                <th className="text-center">Visibility</th>
                <th className="text-right">Manage</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="table-loading-cell">
                    <div className="admin-spinner" />
                    <span>Loading products catalogue...</span>
                  </td>
                </tr>
              ) : productsData.results.length === 0 ? (
                <tr>
                  <td colSpan={7} className="table-empty-cell">
                    <Package size={32} className="text-muted" />
                    <p>No products match your current catalogue filter.</p>
                  </td>
                </tr>
              ) : (
                productsData.results.map((p) => {
                  const isOutOfStock = !p.is_in_stock;
                  const isLow = p.is_low_stock;

                  return (
                    <tr key={p.id} className="product-row">
                      {/* Product Name & Thumbnail */}
                      <td className="product-name-col">
                        <div className="product-info-wrap">
                          <div className="product-thumb-box">
                            {p.primary_image ? (
                              <img src={p.primary_image} alt={p.name} className="product-thumb-img" />
                            ) : (
                              <ImageIcon size={18} className="text-muted" />
                            )}
                          </div>
                          <div className="product-meta-texts">
                            <span className="product-title font-bold">{p.name}</span>
                            <div className="product-sub-flags">
                              {p.is_featured && (
                                <span className="featured-badge" title="Featured on Homepage">
                                  <Star size={10} /> Featured
                                </span>
                              )}
                              {p.has_variants && (
                                <span className="variants-badge" title="Has variant options">
                                  {p.variants?.length || 'Has'} Options
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* SKU */}
                      <td className="sku-cell font-mono">{p.sku}</td>

                      {/* Category */}
                      <td>
                        <span className="category-pill">
                          {p.category ? p.category.name : 'Uncategorized'}
                        </span>
                      </td>

                      {/* Price */}
                      <td className="text-right font-bold price-cell">
                        £{parseFloat(p.price).toFixed(2)}
                        {p.compare_at_price && (
                          <span className="compare-at-text">
                            Was £{parseFloat(p.compare_at_price).toFixed(2)}
                          </span>
                        )}
                      </td>

                      {/* Stock Level with Low Stock Indicator */}
                      <td className="text-center">
                        <div className="stock-level-cell">
                          <button
                            type="button"
                            className={`stock-badge-btn ${
                              isOutOfStock ? 'stock-zero' : isLow ? 'stock-low' : 'stock-healthy'
                            }`}
                            onClick={() => handleAdjustStock(p)}
                            title="Click to adjust stock quantity"
                          >
                            {isOutOfStock ? (
                              <>
                                <XCircle size={12} /> Out of Stock (0)
                              </>
                            ) : isLow ? (
                              <>
                                <AlertTriangle size={12} /> Low: {p.total_stock} left
                              </>
                            ) : (
                              <>
                                <CheckCircle2 size={12} /> {p.total_stock} units
                              </>
                            )}
                          </button>
                          <span className="threshold-sub">Thresh: {p.low_stock_threshold}</span>
                        </div>
                      </td>

                      {/* Visibility Status */}
                      <td className="text-center">
                        <span className={`visibility-pill ${p.is_active ? 'pill-active' : 'pill-inactive'}`}>
                          {p.is_active ? 'Active' : 'Draft / Inactive'}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="text-right">
                        <div className="actions-cluster">
                          <button
                            type="button"
                            className="btn-action-icon btn-edit"
                            onClick={() => handleEdit(p)}
                            title="Edit product details & pricing"
                          >
                            <Edit2 size={14} />
                          </button>
                          <button
                            type="button"
                            className="btn-action-icon btn-images"
                            onClick={() => handleManageImages(p)}
                            title="Manage product photos"
                          >
                            <ImageIcon size={14} />
                          </button>
                          <button
                            type="button"
                            className="btn-action-icon btn-variants"
                            onClick={() => handleManageVariants(p)}
                            title="Manage options & sizes"
                          >
                            <Layers size={14} />
                          </button>
                          <button
                            type="button"
                            className="btn-action-icon btn-delete"
                            onClick={() => handleDeleteProduct(p)}
                            title="Delete product"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Toolbar */}
        {!isLoading && totalCount > 0 && (
          <div className="products-pagination-bar">
            <div className="pagination-text">
              Showing <strong>{(currentPage - 1) * pageSize + 1}</strong> to{' '}
              <strong>{Math.min(currentPage * pageSize, totalCount)}</strong> of{' '}
              <strong>{totalCount}</strong> products
            </div>

            <div className="pagination-buttons">
              <div className="page-size-select-wrap">
                <span>Show:</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(parseInt(e.target.value, 10));
                    setCurrentPage(1);
                  }}
                >
                  <option value="10">10</option>
                  <option value="25">25</option>
                  <option value="50">50</option>
                </select>
              </div>

              <button
                type="button"
                className="page-btn"
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
              >
                <ChevronLeft size={16} /> Prev
              </button>

              <span className="page-current">
                Page {currentPage} of {totalPages}
              </span>

              <button
                type="button"
                className="page-btn"
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
              >
                Next <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Product Create & Edit Modal */}
      <ProductFormModal
        product={editingProduct}
        categories={categories}
        isOpen={isFormModalOpen}
        onClose={() => setIsFormModalOpen(false)}
        onSaved={handleProductSaved}
      />

      {/* Product Images Manager Modal */}
      <ProductImageManagerModal
        product={imageProduct}
        isOpen={isImageModalOpen}
        onClose={() => setIsImageModalOpen(false)}
        onImagesChanged={handleProductUpdated}
      />

      {/* Product Variants Manager Modal */}
      <ProductVariantManagerModal
        product={variantProduct}
        isOpen={isVariantModalOpen}
        onClose={() => setIsVariantModalOpen(false)}
        onVariantsChanged={handleProductUpdated}
      />

      {/* Quick Stock Adjustment Modal */}
      <QuickStockModal
        product={stockProduct}
        isOpen={isStockModalOpen}
        onClose={() => setIsStockModalOpen(false)}
        onStockUpdated={handleProductUpdated}
      />
    </div>
  );
};
