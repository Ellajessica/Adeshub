import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import type { Category, ProductListItem, PaginatedResponse } from '../types/api';
import { api } from '../services/api';
import { ProductGrid } from '../components/catalog/ProductGrid';
import { SearchBar } from '../components/ui/SearchBar';
import { Pagination } from '../components/ui/Pagination';
import { LoadingState } from '../components/ui/LoadingState';
import { EmptyState } from '../components/ui/EmptyState';
import { ErrorState } from '../components/ui/ErrorState';
import { getCategoryFallbackImage } from '../utils/categoryAssets';
import './CategoryPage.css';

export const CategoryPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const [searchParams, setSearchParams] = useSearchParams();

  const searchQuery = searchParams.get('search') || '';
  const currentPage = parseInt(searchParams.get('page') || '1', 10);

  const [category, setCategory] = useState<Category | null>(null);
  const [productData, setProductData] = useState<PaginatedResponse<ProductListItem> | null>(null);

  const [loadingCategory, setLoadingCategory] = useState(true);
  const [loadingProducts, setLoadingProducts] = useState(true);
  const [errorCategory, setErrorCategory] = useState<string | null>(null);
  const [errorProducts, setErrorProducts] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) return;

    const fetchCategory = async () => {
      try {
        setLoadingCategory(true);
        setErrorCategory(null);
        const data = await api.getCategoryDetail(slug);
        setCategory(data);
        document.title = `${data.name} Groceries | AdesHub Market`;
      } catch (err) {
        setErrorCategory(err instanceof Error ? err.message : 'Category not found.');
      } finally {
        setLoadingCategory(false);
      }
    };

    fetchCategory();
  }, [slug]);

  const fetchProducts = useCallback(async () => {
    if (!slug) return;
    try {
      setLoadingProducts(true);
      setErrorProducts(null);

      const res = await api.getProducts({
        category: slug,
        search: searchQuery || undefined,
        page: currentPage,
      });

      setProductData(res);
    } catch (err) {
      setErrorProducts(err instanceof Error ? err.message : 'Failed to load category items.');
    } finally {
      setLoadingProducts(false);
    }
  }, [slug, searchQuery, currentPage]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  const updateSearch = (query: string) => {
    const newParams = new URLSearchParams(searchParams);
    if (query) {
      newParams.set('search', query);
    } else {
      newParams.delete('search');
    }
    newParams.delete('page');
    setSearchParams(newParams);
  };

  const updatePage = (page: number) => {
    const newParams = new URLSearchParams(searchParams);
    newParams.set('page', page.toString());
    setSearchParams(newParams);
  };

  if (loadingCategory) {
    return (
      <div className="container category-page">
        <LoadingState type="spinner" message="Loading category..." />
      </div>
    );
  }

  if (errorCategory || !category) {
    return (
      <div className="container category-page">
        <Link to="/shop" className="category-page__back">
          <ArrowLeft size={16} />
          <span>Back to All Categories</span>
        </Link>
        <ErrorState
          title="Category Not Found"
          message={errorCategory || 'The category you requested could not be found.'}
        />
      </div>
    );
  }

  return (
    <div className="category-page">
      <section className="category-header">
        <div className="container">
          <Link to="/shop" className="category-page__back">
            <ArrowLeft size={16} />
            <span>All Categories</span>
          </Link>

          <div className="category-header__content">
            <div className="category-header__icon-box">
              <img
                src={category.image || getCategoryFallbackImage(category.slug, category.name)}
                alt={category.name}
                className="category-header__img"
              />
            </div>

            <div className="category-header__text">
              <h1 className="heading-lg category-header__title">{category.name}</h1>
              {category.description && (
                <p className="category-header__desc">{category.description}</p>
              )}
              <span className="category-header__badge">
                {category.product_count} {category.product_count === 1 ? 'Product' : 'Products'} Available
              </span>
            </div>
          </div>
        </div>
      </section>

      <div className="container category-products-section">
        <div className="category-search-bar">
          <SearchBar
            initialValue={searchQuery}
            onSearch={updateSearch}
            placeholder={`Search within ${category.name}...`}
            size="md"
          />
        </div>

        {loadingProducts ? (
          <LoadingState type="product-grid" count={6} />
        ) : errorProducts ? (
          <ErrorState
            title="Failed to load category products"
            message={errorProducts}
            onRetry={fetchProducts}
          />
        ) : !productData || productData.results.length === 0 ? (
          <EmptyState
            type={searchQuery ? 'search' : 'products'}
            title={searchQuery ? `No results for "${searchQuery}" in ${category.name}` : `No products in ${category.name} yet`}
            message={
              searchQuery
                ? 'Try searching with different keywords or clearing your search input.'
                : 'Products added under this category will automatically display here.'
            }
          />
        ) : (
          <>
            <ProductGrid products={productData.results} />

            <Pagination
              currentPage={currentPage}
              totalItems={productData.count}
              pageSize={10}
              hasNext={!!productData.next}
              hasPrevious={!!productData.previous}
              onPageChange={updatePage}
            />
          </>
        )}
      </div>
    </div>
  );
};
