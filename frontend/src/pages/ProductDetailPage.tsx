import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ShoppingBag, ArrowLeft, ShieldCheck, Truck, Check, Minus, Plus, Loader2 } from 'lucide-react';
import type { ProductDetail, ProductVariant } from '../types/api';
import { api } from '../services/api';
import { PriceDisplay, formatCurrency } from '../components/ui/PriceDisplay';
import { Badge } from '../components/ui/Badge';
import { LoadingState } from '../components/ui/LoadingState';
import { ErrorState } from '../components/ui/ErrorState';
import { Button } from '../components/ui/Button';
import { useCart } from '../context/CartContext';
import { getCategoryFallbackImage } from '../utils/categoryAssets';
import './ProductDetailPage.css';

export const ProductDetailPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();

  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [selectedVariant, setSelectedVariant] = useState<ProductVariant | null>(null);
  const [quantity, setQuantity] = useState<number>(1);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { addToCart, itemLoadingMap, showToast } = useCart();

  useEffect(() => {
    if (!slug) return;

    const fetchProduct = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await api.getProductDetail(slug);
        setProduct(data);
        document.title = `${data.name} | AdesHub Market`;

        if (data.images && data.images.length > 0) {
          const primary = data.images.find((img) => img.is_primary) || data.images[0];
          setSelectedImage(primary.image);
        } else if (data.primary_image) {
          setSelectedImage(data.primary_image);
        } else {
          setSelectedImage(getCategoryFallbackImage(data.category?.slug, data.category?.name));
        }

        if (data.has_variants && data.variants && data.variants.length > 0) {
          const activeVariants = data.variants.filter((v) => v.is_active);
          if (activeVariants.length > 0) {
            setSelectedVariant(activeVariants[0]);
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load product details.');
      } finally {
        setLoading(false);
      }
    };

    fetchProduct();
  }, [slug]);

  if (loading) {
    return (
      <div className="container product-detail-page">
        <LoadingState type="detail" />
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="container product-detail-page">
        <Link to="/shop" className="product-detail__back">
          <ArrowLeft size={16} />
          <span>Back to Shop Catalog</span>
        </Link>
        <ErrorState
          title="Product Not Found"
          message={error || 'We could not find the product you requested.'}
        />
      </div>
    );
  }

  const categoryFallback = getCategoryFallbackImage(product.category?.slug, product.category?.name);
  const currentPrice = selectedVariant ? selectedVariant.price : product.price;
  const compareAtPrice = selectedVariant ? selectedVariant.compare_at_price : product.compare_at_price;
  const currentStock = selectedVariant ? selectedVariant.stock_quantity : product.total_stock;
  const isInStock = selectedVariant ? selectedVariant.is_in_stock : product.is_in_stock;

  const loadingKey = `add_${product.id}_${selectedVariant?.id || 0}`;
  const isAdding = !!itemLoadingMap[loadingKey];

  const handleQuantityDecrease = () => {
    setQuantity((prev) => Math.max(1, prev - 1));
  };

  const handleQuantityIncrease = () => {
    if (currentStock > 0 && quantity >= currentStock) {
      showToast(`Only ${currentStock} available in stock.`, 'info');
      return;
    }
    setQuantity((prev) => prev + 1);
  };

  const handleAddToCart = async () => {
    if (product.has_variants && !selectedVariant) {
      showToast('Please select a package option.', 'error');
      return;
    }
    if (!isInStock || isAdding) return;
    await addToCart(product.id, selectedVariant?.id, quantity);
  };

  const hasDescription = product.description && product.description.trim().length > 0;

  return (
    <div className="product-detail-page">
      <div className="container">
        <div className="product-detail__top-nav">
          <Link to="/shop" className="product-detail__back-btn">
            <ArrowLeft size={16} />
            <span>Back to Shop</span>
          </Link>

          <nav className="product-detail__breadcrumb" aria-label="Breadcrumb">
            <Link to="/">Home</Link>
            <span>/</span>
            <Link to="/shop">Shop</Link>
            {product.category && (
              <>
                <span>/</span>
                <Link to={`/categories/${product.category.slug}`}>{product.category.name}</Link>
              </>
            )}
            <span>/</span>
            <span className="current">{product.name}</span>
          </nav>
        </div>

        <div className="product-detail__grid">
          <div className="product-detail__media">
            <div className="product-detail__main-img-wrapper">
              <img
                src={selectedImage || categoryFallback}
                alt={product.name}
                className="product-detail__main-img"
                onError={() => {
                  if (selectedImage !== categoryFallback) {
                    setSelectedImage(categoryFallback);
                  }
                }}
              />
              {product.is_featured && (
                <Badge variant="secondary" className="product-detail__featured-badge">
                  Featured Item
                </Badge>
              )}
            </div>

            {product.images && product.images.length > 1 && (
              <div className="product-detail__thumbnails">
                {product.images.map((img) => (
                  <button
                    key={img.id}
                    className={`product-detail__thumb-btn ${selectedImage === img.image ? 'active' : ''}`}
                    onClick={() => setSelectedImage(img.image)}
                  >
                    <img src={img.image} alt={img.alt_text || product.name} />
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="product-detail__info">
            <div className="product-detail__badges">
              {product.category && (
                <Link to={`/categories/${product.category.slug}`}>
                  <Badge variant="neutral">{product.category.name}</Badge>
                </Link>
              )}

              {isInStock ? (
                product.is_low_stock ? (
                  <Badge variant="warning">Low Stock ({currentStock} left)</Badge>
                ) : (
                  <Badge variant="success">In Stock</Badge>
                )
              ) : (
                <Badge variant="error">Out of Stock</Badge>
              )}
            </div>

            <h1 className="heading-lg product-detail__title">{product.name}</h1>

            <div className="product-detail__meta">
              <span className="sku">SKU: {selectedVariant ? selectedVariant.sku : product.sku}</span>
              {currentStock > 0 && (
                <span className="stock-count">{currentStock} units available</span>
              )}
            </div>

            <div className="product-detail__price-box">
              <PriceDisplay
                price={currentPrice}
                compareAtPrice={compareAtPrice}
                size="xl"
              />
            </div>

            {product.has_variants && product.variants && product.variants.length > 0 && (
              <div className="product-detail__variants">
                <label className="product-detail__variant-label">
                  Package:
                </label>
                <div className="product-detail__variant-options">
                  {product.variants.map((v) => (
                    <button
                      key={v.id}
                      className={`product-detail__variant-btn ${selectedVariant?.id === v.id ? 'active' : ''}`}
                      onClick={() => {
                        setSelectedVariant(v);
                        setQuantity(1);
                      }}
                      disabled={!v.is_active}
                    >
                      <span className="variant-name">{v.name}</span>
                      <span className="variant-price">{formatCurrency(v.price)}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {isInStock && (
              <div className="product-detail__quantity-selector">
                <label className="quantity-label">Quantity:</label>
                <div className="quantity-stepper">
                  <button
                    type="button"
                    className="stepper-btn"
                    onClick={handleQuantityDecrease}
                    disabled={quantity <= 1 || isAdding}
                    aria-label="Decrease quantity"
                  >
                    <Minus size={16} />
                  </button>
                  <span className="stepper-val">{quantity}</span>
                  <button
                    type="button"
                    className="stepper-btn"
                    onClick={handleQuantityIncrease}
                    disabled={quantity >= currentStock || isAdding}
                    aria-label="Increase quantity"
                  >
                    <Plus size={16} />
                  </button>
                </div>
              </div>
            )}

            <div className="product-detail__cta-section">
              <Button
                variant="primary"
                size="lg"
                fullWidth
                disabled={!isInStock || isAdding}
                onClick={handleAddToCart}
                icon={isAdding ? <Loader2 size={20} className="animate-spin" /> : <ShoppingBag size={20} />}
                className="product-detail__add-btn"
              >
                {isAdding ? 'Adding to Cart...' : isInStock ? 'Add to Cart' : 'Currently Out of Stock'}
              </Button>
            </div>

            <div className="product-detail__description">
              <h3>Product Description</h3>
              <p className={hasDescription ? "product-detail__desc-text" : "product-detail__no-desc"}>
                {hasDescription ? product.description : 'No detailed description is currently available for this product.'}
              </p>
            </div>

            <div className="product-detail__guarantees">
              <div className="guarantee-item">
                <ShieldCheck size={20} className="icon" />
                <span>Quality Product Guarantee</span>
              </div>
              <div className="guarantee-item">
                <Truck size={20} className="icon" />
                <span>Standard Dispatch</span>
              </div>
              <div className="guarantee-item">
                <Check size={20} className="icon" />
                <span>Direct Supplier Sourcing</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
