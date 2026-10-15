import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { ShoppingBag, Star, ArrowRight, Loader2 } from 'lucide-react';
import type { ProductListItem } from '../../types/api';
import { PriceDisplay } from '../ui/PriceDisplay';
import { Badge } from '../ui/Badge';
import { useCart } from '../../context/CartContext';
import { getCategoryFallbackImage } from '../../utils/categoryAssets';
import './ProductCard.css';

interface ProductCardProps {
  product: ProductListItem;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  const { addToCart, itemLoadingMap } = useCart();
  const loadingKey = `add_${product.id}_0`;
  const isAdding = !!itemLoadingMap[loadingKey];

  const categoryFallback = getCategoryFallbackImage(product.category?.slug, product.category?.name);
  const [currentImg, setCurrentImg] = useState<string>(product.primary_image || categoryFallback);

  const stockBadge = () => {
    if (!product.is_in_stock) {
      return <Badge variant="error">Out of Stock</Badge>;
    }
    const stockVal = product.total_stock !== undefined && product.total_stock !== null ? product.total_stock : product.stock_quantity;
    if (stockVal > 0 && stockVal <= 5) {
      return <Badge variant="warning">Low Stock ({stockVal})</Badge>;
    }
    return <Badge variant="success">In Stock</Badge>;
  };

  const handleAddToCart = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!product.is_in_stock || isAdding) return;
    await addToCart(product.id, null, 1);
  };

  // Extract or format package size or weight
  const packageSizeMatch = product.name.match(/\b(\d+(?:\.\d+)?\s*(?:kg|g|litres|litre|l|ml|oz|lb|cl|pack|pieces|pcs))\b/i);
  const packageSize = packageSizeMatch ? packageSizeMatch[0] : (product.has_variants ? 'Multiple Sizes' : null);

  return (
    <article className="product-card">
      <div className="product-card__image-wrapper">
        <Link to={`/products/${product.slug}`} className="product-card__image-link" tabIndex={-1}>
          <img
            src={currentImg}
            alt={product.name}
            className="product-card__image"
            loading="lazy"
            onError={() => {
              if (currentImg !== categoryFallback) {
                setCurrentImg(categoryFallback);
              }
            }}
          />
        </Link>

        {product.is_featured && (
          <div className="product-card__badges">
            <Badge variant="secondary" className="product-card__featured-badge">
              <Star size={10} style={{ marginRight: '3px', fill: 'currentColor' }} />
              Featured
            </Badge>
          </div>
        )}
      </div>

      <div className="product-card__body">
        <div className="product-card__meta">
          <div className="product-card__meta-left">
            {stockBadge()}
            {packageSize && (
              <span className="product-card__size-badge">{packageSize}</span>
            )}
          </div>
          {product.category && (
            <span className="product-card__category-text">{product.category.name}</span>
          )}
        </div>

        <h3 className="product-card__title">
          <Link to={`/products/${product.slug}`}>{product.name}</Link>
        </h3>

        <div className="product-card__price-row">
          <PriceDisplay
            price={product.price}
            compareAtPrice={product.compare_at_price}
            size="md"
          />
        </div>

        <div className="product-card__action-row">
          {product.has_variants ? (
            <Link to={`/products/${product.slug}`} className="product-card__btn product-card__btn--secondary">
              <span>View Options</span>
              <ArrowRight size={14} />
            </Link>
          ) : (
            <button
              onClick={handleAddToCart}
              disabled={!product.is_in_stock || isAdding}
              className="product-card__btn product-card__btn--primary"
            >
              {isAdding ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  <span>Adding...</span>
                </>
              ) : (
                <>
                  <ShoppingBag size={14} />
                  <span>{product.is_in_stock ? 'Add to Cart' : 'Out of Stock'}</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </article>
  );
};
