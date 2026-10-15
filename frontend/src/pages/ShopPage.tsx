import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Filter, RotateCcw, PackageCheck } from 'lucide-react';
import type { Category, ProductListItem, PaginatedResponse } from '../types/api';
import { api } from '../services/api';
import { ProductGrid } from '../components/catalog/ProductGrid';
import { SearchBar } from '../components/ui/SearchBar';
import { Pagination } from '../components/ui/Pagination';
import { LoadingState } from '../components/ui/LoadingState';
import { EmptyState } from '../components/ui/EmptyState';
import { ErrorState } from '../components/ui/ErrorState';
import { Button } from '../components/ui/Button';
import './ShopPage.css';

export const ShopPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const selectedCategory = searchParams.get('category') || '';
  const searchQuery = searchParams.get('search') || '';
  const inStockOnly = searchParams.get('in_stock') === 'true';
  const featuredOnly = searchParams.get('featured') === 'true';
  const currentPage = parseInt(searchParams.get('page') || '1', 10);

  const [categories, setCategories] = useState<Category[]>([]);
  const [productData, setProductData] = useState<PaginatedResponse<ProductListItem> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    document.title = 'Shop African Groceries | AdesHub';
    const fetchCats = async () => {
      try {
        const cats = await api.getCategories();
        setCategories(cats);
      } catch (err) {
        console.error('Failed to load categories for shop filter:', err);
      }
    };
    fetchCats();
  }, []);

  const fetchProducts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const res = await api.getProducts({
        category: selectedCategory || undefined,
        search: searchQuery || undefined,
        in_stock: inStockOnly ? true : undefined,
        featured: featuredOnly ? true : undefined,
        page: currentPage,
      });

      setProductData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load products from backend.');
    } finally {
      setLoading(false);
    }
  }, [selectedCategory, searchQuery, inStockOnly, featuredOnly, currentPage]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  const updateParam = (key: string, value: string | null) => {
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set(key, value);
    } else {
      newParams.delete(key);
    }
    if (key !== 'page') {
      newParams.delete('page');
    }
    setSearchParams(newParams);
  };

  const handleClearFilters = () => {
    setSearchParams(new URLSearchParams());
  };

  return (
    <div className="shop-page">
      <section className="shop-header">
        <div className="container shop-header__inner">
          <div className="shop-header__title-group">
            <h1 className="heading-lg shop-header__title">Shop Catalog</h1>
            <p className="shop-header__subtitle">
              Browse our selection of quality African groceries, pantry staples, and spices.
            </p>
          </div>

          <div className="shop-header__search-wrap">
            <SearchBar
              initialValue={searchQuery}
              onSearch={(query) => updateParam('search', query || null)}
              size="md"
              placeholder="Search products"
            />
          </div>
        </div>
      </section>

      <div className="container shop-container">
        <aside className="shop-sidebar">
          <div className="shop-sidebar__card">
            <div className="shop-sidebar__header">
              <div className="shop-sidebar__title">
                <Filter size={16} />
                <span>Filter Products</span>
              </div>
              {(selectedCategory || searchQuery || inStockOnly || featuredOnly) && (
                <button className="shop-sidebar__reset" onClick={handleClearFilters}>
                  <RotateCcw size={12} />
                  <span>Reset</span>
                </button>
              )}
            </div>

            <div className="shop-filter-group">
              <label className="shop-filter-label">Categories</label>
              <div className="shop-category-list">
                <button
                  className={`shop-category-btn ${!selectedCategory ? 'active' : ''}`}
                  onClick={() => updateParam('category', null)}
                >
                  <span>All Categories</span>
                </button>
                {categories.map((cat) => (
                  <button
                    key={cat.id}
                    className={`shop-category-btn ${selectedCategory === cat.slug ? 'active' : ''}`}
                    onClick={() => updateParam('category', cat.slug)}
                  >
                    <span>{cat.name}</span>
                    <span className="count">{cat.product_count}</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="shop-filter-group">
              <label className="shop-filter-label">Availability</label>
              <label className="shop-checkbox-label">
                <input
                  type="checkbox"
                  checked={inStockOnly}
                  onChange={(e) => updateParam('in_stock', e.target.checked ? 'true' : null)}
                />
                <PackageCheck size={16} />
                <span>In Stock Items Only</span>
              </label>
            </div>

            <div className="shop-filter-group">
              <label className="shop-filter-label">Collections</label>
              <label className="shop-checkbox-label">
                <input
                  type="checkbox"
                  checked={featuredOnly}
                  onChange={(e) => updateParam('featured', e.target.checked ? 'true' : null)}
                />
                <span>Featured Items Only</span>
              </label>
            </div>
          </div>
        </aside>

        <main className="shop-content">
          {(selectedCategory || searchQuery || inStockOnly || featuredOnly) && (
            <div className="shop-active-chips">
              <span className="shop-chips-label">Active Filters:</span>
              {selectedCategory && (
                <span className="shop-chip">
                  Category: {categories.find((c) => c.slug === selectedCategory)?.name || selectedCategory}
                  <button onClick={() => updateParam('category', null)}>×</button>
                </span>
              )}
              {searchQuery && (
                <span className="shop-chip">
                  Search: "{searchQuery}"
                  <button onClick={() => updateParam('search', null)}>×</button>
                </span>
              )}
              {inStockOnly && (
                <span className="shop-chip">
                  In Stock Only
                  <button onClick={() => updateParam('in_stock', null)}>×</button>
                </span>
              )}
              {featuredOnly && (
                <span className="shop-chip">
                  Featured Only
                  <button onClick={() => updateParam('featured', null)}>×</button>
                </span>
              )}
              <Button variant="ghost" size="sm" onClick={handleClearFilters}>
                Clear All
              </Button>
            </div>
          )}

          {loading ? (
            <LoadingState type="product-grid" count={8} />
          ) : error ? (
            <ErrorState title="Error Loading Shop" message={error} onRetry={fetchProducts} />
          ) : !productData || productData.results.length === 0 ? (
            <EmptyState
              type={searchQuery ? 'search' : 'products'}
              title={searchQuery ? `No results for "${searchQuery}"` : 'No products found'}
              message={
                searchQuery
                  ? 'Try checking for spelling errors, clearing filters, or searching for a broader term.'
                  : 'There are no products matching your selected category and filters in the catalog.'
              }
              actionLabel="Clear Filters"
              onAction={handleClearFilters}
            />
          ) : (
            <>
              <div className="shop-results-header">
                <span className="shop-results-count">
                  Showing {productData.results.length} of {productData.count} items
                </span>
              </div>

              <ProductGrid products={productData.results} />

              <Pagination
                currentPage={currentPage}
                totalItems={productData.count}
                pageSize={10}
                hasNext={!!productData.next}
                hasPrevious={!!productData.previous}
                onPageChange={(page) => updateParam('page', page.toString())}
              />
            </>
          )}
        </main>
      </div>
    </div>
  );
};
