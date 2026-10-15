import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import type { Category } from '../../types/api';
import { getCategoryFallbackImage } from '../../utils/categoryAssets';
import './CategoryCard.css';

interface CategoryCardProps {
  category: Category;
}

export const CategoryCard: React.FC<CategoryCardProps> = ({ category }) => {
  const fallback = getCategoryFallbackImage(category.slug, category.name);
  const [imgSrc, setImgSrc] = useState(category.image || fallback);

  return (
    <Link to={`/categories/${category.slug}`} className="category-card" aria-label={`Browse ${category.name}`}>
      <div className="category-card__image-container">
        <img
          src={imgSrc}
          alt={category.name}
          className="category-card__image"
          loading="lazy"
          onError={() => {
            if (imgSrc !== fallback) {
              setImgSrc(fallback);
            }
          }}
        />
        <div className="category-card__overlay" />
        <span className="category-card__badge">
          {category.product_count} {category.product_count === 1 ? 'item' : 'items'}
        </span>
      </div>

      <div className="category-card__body">
        <div className="category-card__content">
          <h3 className="category-card__title">{category.name}</h3>
          {category.description && (
            <p className="category-card__description">{category.description}</p>
          )}
        </div>
        <div className="category-card__action">
          <span className="category-card__link-text">Shop Now</span>
          <ArrowRight size={15} className="category-card__arrow" />
        </div>
      </div>
    </Link>
  );
};
