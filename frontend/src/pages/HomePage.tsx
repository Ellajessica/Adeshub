import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  ShoppingBag,
  CheckCircle2,
  ShieldCheck,
  Truck,
  Sparkles,
  Flame,
  Leaf
} from 'lucide-react';
import type { Category, ProductListItem } from '../types/api';
import { api } from '../services/api';
import { CategoryCard } from '../components/catalog/CategoryCard';
import { ProductGrid } from '../components/catalog/ProductGrid';
import { LoadingState } from '../components/ui/LoadingState';
import { EmptyState } from '../components/ui/EmptyState';
import { ErrorState } from '../components/ui/ErrorState';
import { Button } from '../components/ui/Button';
import heroGroceryImage from '../assets/african_groceries_hero.jpg';
import './HomePage.css';

export const HomePage: React.FC = () => {
  const [categories, setCategories] = useState<Category[]>([]);
  const [popularProducts, setPopularProducts] = useState<ProductListItem[]>([]);
  const [featuredProducts, setFeaturedProducts] = useState<ProductListItem[]>([]);

  const [loadingCats, setLoadingCats] = useState(true);
  const [loadingPopular, setLoadingPopular] = useState(true);

  const [errorCats, setErrorCats] = useState<string | null>(null);
  const [errorPopular, setErrorPopular] = useState<string | null>(null);

  const navigate = useNavigate();

  useEffect(() => {
    document.title = 'AdesHub | Authentic African Groceries & Food Marketplace';

    let isMounted = true;

    const loadData = async () => {
      // 1. Fetch Categories
      try {
        setLoadingCats(true);
        setErrorCats(null);
        const catsData = await api.getCategories();
        if (isMounted) {
          setCategories(catsData);
        }
      } catch (err) {
        if (isMounted) {
          setErrorCats(err instanceof Error ? err.message : 'Failed to load grocery categories.');
        }
      } finally {
        if (isMounted) setLoadingCats(false);
      }

      // 2. Fetch Featured & Popular Products
      try {
        setLoadingPopular(true);
        setErrorPopular(null);

        const [featuredRes, allRes] = await Promise.allSettled([
          api.getProducts({ featured: true }),
          api.getProducts({ page: 1 })
        ]);

        if (isMounted) {
          if (featuredRes.status === 'fulfilled') {
            setFeaturedProducts(featuredRes.value.results || []);
          }
          if (allRes.status === 'fulfilled') {
            setPopularProducts(allRes.value.results || []);
          } else {
            setErrorPopular('Failed to load store products from backend.');
          }
        }
      } catch (err) {
        if (isMounted) {
          setErrorPopular(err instanceof Error ? err.message : 'Unable to connect to product catalog.');
        }
      } finally {
        if (isMounted) setLoadingPopular(false);
      }
    };

    loadData();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleExploreCategories = () => {
    const section = document.getElementById('shop-categories');
    if (section) {
      section.scrollIntoView({ behavior: 'smooth' });
    } else {
      navigate('/shop');
    }
  };

  // Determine display products for Popular in African Kitchens (combines all available items)
  const displayProducts = React.useMemo(() => {
    const combined = [...featuredProducts];
    for (const p of popularProducts) {
      if (!combined.some((item) => item.id === p.id)) {
        combined.push(p);
      }
    }
    return combined;
  }, [featuredProducts, popularProducts]);

  return (
    <div className="home-page">
      {/* 1. HERO SECTION */}
      <section className="hero-section" aria-label="Welcome hero banner">
        <div className="container hero-section__inner">
          {/* Left Column: Eyebrow, Headline, Description, CTAs, Trust indicators */}
          <div className="hero-section__content">
            <div className="hero-eyebrow">
              <Leaf size={14} className="hero-eyebrow-icon" />
              <span>YOUR FAVOURITE AFRICAN GROCERIES</span>
            </div>

            <h1 className="hero-title">
              Authentic African Groceries,{' '}
              <span className="hero-highlight">Delivered to Your Door.</span>
            </h1>

            <p className="hero-lead">
              Discover the ingredients that bring African cooking to life. From traditional staples, grains and flours to rich oils, spices, fresh produce and everyday essentials, find quality ingredients for the dishes you love, delivered to your door across the UK.
            </p>

            <div className="hero-actions">
              <Button
                variant="primary"
                size="lg"
                onClick={() => navigate('/shop')}
                icon={<ShoppingBag size={18} />}
                className="hero-btn-primary"
              >
                Shop Now
              </Button>

              <Button
                variant="outline"
                size="lg"
                onClick={handleExploreCategories}
                className="hero-btn-secondary"
              >
                Explore Categories
              </Button>
            </div>

            {/* Short Real Business Trust Indicators */}
            <div className="hero-trust-row">
              <div className="hero-trust-point">
                <CheckCircle2 size={16} className="hero-trust-check" />
                <span>100% Authentic Quality</span>
              </div>
              <div className="hero-trust-point">
                <Truck size={16} className="hero-trust-check" />
                <span>UK Doorstep Delivery</span>
              </div>
              <div className="hero-trust-point">
                <ShieldCheck size={16} className="hero-trust-check" />
                <span>Secure Stripe Checkout</span>
              </div>
            </div>
          </div>

          {/* Right Column: Visually Rich African Groceries Photography */}
          <div className="hero-section__media">
            <div className="hero-image-frame">
              <img
                src={heroGroceryImage}
                alt="Abundant authentic African groceries including red palm oil, yams, garri, and spices"
                className="hero-image"
                loading="eager"
              />
              <div className="hero-image-badge">
                <div className="badge-dot" />
                <span>Fresh Harvest & Authentic Pantry Staples</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. VALUE BENEFIT STRIP */}
      <section className="benefit-bar">
        <div className="container benefit-bar__inner">
          <div className="benefit-item">
            <div className="benefit-icon-wrap">
              <Leaf size={20} />
            </div>
            <div className="benefit-text">
              <span className="benefit-title">Authentic Sourcing</span>
              <span className="benefit-sub">Directly from verified African suppliers</span>
            </div>
          </div>

          <div className="benefit-item">
            <div className="benefit-icon-wrap">
              <Truck size={20} />
            </div>
            <div className="benefit-text">
              <span className="benefit-title">Careful Packing</span>
              <span className="benefit-sub">Safely packaged for fresh arrival</span>
            </div>
          </div>

          <div className="benefit-item">
            <div className="benefit-icon-wrap">
              <ShieldCheck size={20} />
            </div>
            <div className="benefit-text">
              <span className="benefit-title">Secure Payments</span>
              <span className="benefit-sub">Card & Mobile Pay via Stripe</span>
            </div>
          </div>

          <div className="benefit-item">
            <div className="benefit-icon-wrap">
              <Sparkles size={20} />
            </div>
            <div className="benefit-text">
              <span className="benefit-title">Guaranteed Freshness</span>
              <span className="benefit-sub">Quality checked pantry staples</span>
            </div>
          </div>
        </div>
      </section>

      {/* 3. SHOP BY CATEGORY SECTION */}
      <section id="shop-categories" className="categories-section">
        <div className="container">
          <div className="section-header">
            <div>
              <div className="section-kicker">EXPLORE AISLES</div>
              <h2 className="heading-lg">Shop by Category</h2>
              <p className="section-subtitle">Find the ingredients you need for your favourite meals.</p>
            </div>
            <Link to="/shop" className="section-view-all">
              <span>View All Categories</span>
              <ArrowRight size={16} />
            </Link>
          </div>

          {loadingCats ? (
            <LoadingState type="category-grid" count={4} />
          ) : errorCats ? (
            <ErrorState title="Categories unavailable" message={errorCats} />
          ) : categories.length === 0 ? (
            <EmptyState
              type="categories"
              title="No categories available yet"
              message="Categories will appear here as soon as they are added to the store."
            />
          ) : (
            <div className="categories-grid">
              {categories.map((cat) => (
                <CategoryCard key={cat.id} category={cat} />
              ))}
            </div>
          )}
        </div>
      </section>

      {/* 4. PRODUCT DISCOVERY: POPULAR IN AFRICAN KITCHENS */}
      <section className="products-section">
        <div className="container">
          <div className="section-header">
            <div>
              <div className="section-kicker">
                <Flame size={13} className="kicker-icon" />
                CUSTOMER FAVOURITES
              </div>
              <h2 className="heading-lg">Popular in African Kitchens</h2>
              <p className="section-subtitle">Handpicked pantry staples, grains, and kitchen essentials.</p>
            </div>
            <Link to="/shop" className="section-view-all">
              <span>Browse Full Shop</span>
              <ArrowRight size={16} />
            </Link>
          </div>

          {loadingPopular ? (
            <LoadingState type="product-grid" count={4} />
          ) : errorPopular ? (
            <ErrorState title="Unable to load products" message={errorPopular} />
          ) : displayProducts.length === 0 ? (
            <EmptyState
              type="products"
              title="No products available in the store yet"
              message="New African food products are being catalogued and will appear here shortly."
            />
          ) : (
            <ProductGrid products={displayProducts} />
          )}
        </div>
      </section>

      {/* 5. WHY SHOP WITH ADESHUB PROMO SECTION */}
      <section className="trust-story-section">
        <div className="container">
          <div className="trust-story__header">
            <span className="section-kicker">THE ADESHUB PROMISE</span>
            <h2 className="heading-lg">Why Customers Trust AdesHub</h2>
            <p className="section-subtitle">
              We make shopping for African groceries in the UK simple, trustworthy, and convenient.
            </p>
          </div>

          <div className="trust-story__grid">
            <div className="trust-card">
              <div className="trust-card__num">01</div>
              <h3 className="trust-card__title">Authentic African Selection</h3>
              <p className="trust-card__desc">
                From Nigerian parboiled rice and Ijebu garri to pure red palm oil and suya seasoning, we bring the true taste of home to your kitchen.
              </p>
            </div>

            <div className="trust-card">
              <div className="trust-card__num">02</div>
              <h3 className="trust-card__title">Reliable Doorstep Delivery</h3>
              <p className="trust-card__desc">
                No need to travel far or carry heavy sacks of rice and yam tubers. We pack your items securely and deliver straight to your door.
              </p>
            </div>

            <div className="trust-card">
              <div className="trust-card__num">03</div>
              <h3 className="trust-card__title">Clear Pricing & No Hidden Fees</h3>
              <p className="trust-card__desc">
                Shop with complete transparency. Honest prices in British Pounds (£) with immediate digital order confirmation.
              </p>
            </div>

            <div className="trust-card">
              <div className="trust-card__num">04</div>
              <h3 className="trust-card__title">Responsive Customer Care</h3>
              <p className="trust-card__desc">
                Have questions about an order or a specific ingredient? Our dedicated team is reachable via email and social channels.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
