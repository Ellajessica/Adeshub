import React, { useState, useEffect, useRef } from 'react';
import { Link, NavLink, useNavigate, useLocation } from 'react-router-dom';
import {
  ShoppingBag,
  User,
  Menu,
  X,
  ChevronDown,
  LogOut,
  Package,
  MapPin,
  UserCheck,
  Search,
  Flame,
  CheckCircle,
  ArrowRight,
  Layers,
  ShieldCheck
} from 'lucide-react';
import type { Category } from '../../types/api';
import { api } from '../../services/api';
import { useCart } from '../../context/CartContext';
import { useAuth } from '../../context/AuthContext';
import { getCategoryFallbackImage } from '../../utils/categoryAssets';
import { getUserDisplayName } from '../../utils/userDisplay';
import './Header.css';

export const Header: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [categoriesDropdownOpen, setCategoriesDropdownOpen] = useState(false);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);
  const [searchQuery, setSearchQuery] = useState('');

  const dropdownRef = useRef<HTMLDivElement>(null);
  const userDropdownRef = useRef<HTMLDivElement>(null);

  const { cart } = useCart();
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const totalQuantity = cart?.total_quantity || 0;
  const customerDisplayName = getUserDisplayName(user);

  // Load categories on initial render for seamless instant dropdown
  useEffect(() => {
    let isMounted = true;
    const fetchCategories = async () => {
      try {
        const cats = await api.getCategories();
        if (isMounted) {
          setCategories(cats);
        }
      } catch (err) {
        console.error('Failed to load categories for nav:', err);
      }
    };
    fetchCategories();
    return () => {
      isMounted = false;
    };
  }, []);

  // Sync search input if URL has ?search=
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const searchParam = params.get('search');
    if (searchParam) {
      setSearchQuery(searchParam);
    }
  }, [location.search]);

  // Close menus on route change
  useEffect(() => {
    setMobileMenuOpen(false);
    setCategoriesDropdownOpen(false);
    setUserDropdownOpen(false);
  }, [location.pathname]);

  // Click outside to close dropdowns
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setCategoriesDropdownOpen(false);
      }
      if (userDropdownRef.current && !userDropdownRef.current.contains(event.target as Node)) {
        setUserDropdownOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setCategoriesDropdownOpen(false);
        setUserDropdownOpen(false);
        setMobileMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const query = searchQuery.trim();
    if (query) {
      navigate(`/shop?search=${encodeURIComponent(query)}`);
    } else {
      navigate('/shop');
    }
  };

  const handleLogout = async () => {
    setUserDropdownOpen(false);
    await logout();
    navigate('/');
  };

  const isCheckoutPage = location.pathname === '/checkout';

  if (isCheckoutPage) {
    return (
      <header className="site-header site-header--checkout">
        <div className="container site-header__checkout-inner">
          <Link to="/" className="site-header__logo" aria-label="AdesHub Home">
            <span className="logo-accent">Ades<span className="logo-hub">Hub</span></span>
            <span className="logo-badge">AFRICAN MARKET</span>
          </Link>
          <div className="checkout-trust-badge">
            <ShieldCheck size={18} className="trust-badge-icon" />
            <span className="trust-badge-text">Secure Checkout</span>
          </div>
        </div>
      </header>
    );
  }

  return (
    <header className="site-header">
      {/* 1. PRIMARY TOP ROW: LOGO | HORIZONTALLY PROMINENT SEARCH | ACCOUNT & CART */}
      <div className="site-header__main">
        <div className="container site-header__main-inner">
          {/* Mobile Menu Toggle Button */}
          <button
            className="site-header__mobile-toggle"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>

          {/* AdesHub Logo */}
          <Link to="/" className="site-header__logo" aria-label="AdesHub Home">
            <span className="logo-accent">Ades<span className="logo-hub">Hub</span></span>
            <span className="logo-badge">AFRICAN MARKET</span>
          </Link>

          {/* Desktop Search Bar */}
          <form className="site-header__search" onSubmit={handleSearchSubmit} role="search">
            <div className="search-input-wrap">
              <Search className="search-icon" size={19} aria-hidden="true" />
              <input
                type="text"
                className="search-input"
                placeholder="Search African groceries, spices, grains..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                aria-label="Search African groceries, spices, grains"
              />
              {searchQuery && (
                <button
                  type="button"
                  className="search-clear-btn"
                  onClick={() => setSearchQuery('')}
                  aria-label="Clear search input"
                >
                  <X size={15} />
                </button>
              )}
            </div>
            <button type="submit" className="search-submit-btn" aria-label="Search products">
              Search
            </button>
          </form>

          {/* Account and Cart Action Controls */}
          <div className="site-header__actions">
            {/* User Account Menu */}
            <div className="header-action-wrapper" ref={userDropdownRef}>
              <button
                className={`header-action-btn ${isAuthenticated ? 'header-action-btn--auth' : ''}`}
                onClick={() => setUserDropdownOpen(!userDropdownOpen)}
                aria-expanded={userDropdownOpen}
                aria-haspopup="true"
                aria-label="You menu"
              >
                {isAuthenticated ? <UserCheck size={20} className="icon-auth" /> : <User size={20} />}
                <div className="action-btn-text you-control-text">
                  <span className="you-label">You</span>
                  {isAuthenticated && customerDisplayName !== 'My Account' ? (
                    <span className="you-username" title={customerDisplayName}>{customerDisplayName}</span>
                  ) : null}
                </div>
                <ChevronDown size={14} className="dropdown-arrow" />
              </button>

              {userDropdownOpen && (
                <div className="header-dropdown-card header-account-dropdown" role="menu">
                  {isAuthenticated ? (
                    <>
                      <div className="account-card-header">
                        <span className="user-name">{customerDisplayName}</span>
                        <span className="user-email">{user?.email}</span>
                      </div>
                      {(user?.is_staff || user?.is_superuser) && (
                        <Link
                          to="/admin"
                          className="header-dropdown-item admin-portal-item"
                          role="menuitem"
                          onClick={() => setUserDropdownOpen(false)}
                        >
                          <ShieldCheck size={16} className="text-primary" />
                          <span className="font-bold">Admin Dashboard</span>
                          <span className="admin-chip">Staff</span>
                        </Link>
                      )}
                      <Link
                        to="/account"
                        className="header-dropdown-item"
                        role="menuitem"
                        onClick={() => setUserDropdownOpen(false)}
                      >
                        <User size={16} /> My Account
                      </Link>
                      <Link
                        to="/account"
                        className="header-dropdown-item"
                        role="menuitem"
                        onClick={() => setUserDropdownOpen(false)}
                      >
                        <Package size={16} /> Order History
                      </Link>
                      <Link
                        to="/account"
                        className="header-dropdown-item"
                        role="menuitem"
                        onClick={() => setUserDropdownOpen(false)}
                      >
                        <MapPin size={16} /> Delivery Addresses
                      </Link>
                      <button
                        className="header-dropdown-item logout-action"
                        role="menuitem"
                        onClick={handleLogout}
                      >
                        <LogOut size={16} /> Log Out
                      </button>
                    </>
                  ) : (
                    <>
                      <div className="account-card-guest">
                        <p className="guest-title">Welcome to AdesHub</p>
                        <p className="guest-desc">Sign in to track orders and save your delivery details.</p>
                      </div>
                      <Link
                        to="/login"
                        className="header-dropdown-item highlight-action"
                        role="menuitem"
                        onClick={() => setUserDropdownOpen(false)}
                      >
                        Sign In
                      </Link>
                      <Link
                        to="/register"
                        className="header-dropdown-item"
                        role="menuitem"
                        onClick={() => setUserDropdownOpen(false)}
                      >
                        Create Free Account
                      </Link>
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Shopping Cart Button */}
            <Link
              to="/cart"
              className="header-cart-btn"
              aria-label={`Shopping cart containing ${totalQuantity} items`}
            >
              <div className="cart-icon-wrap">
                <ShoppingBag size={21} />
                <span className="cart-count-badge">{totalQuantity}</span>
              </div>
              <div className="cart-text-wrap">
                <span className="cart-label">Cart</span>
              </div>
            </Link>
          </div>
        </div>

        {/* Mobile Search Bar - Displayed right below logo/actions on mobile */}
        <div className="site-header__mobile-search-bar">
          <div className="container">
            <form onSubmit={handleSearchSubmit} className="mobile-search-form" role="search">
              <Search className="mobile-search-icon" size={18} />
              <input
                type="text"
                className="mobile-search-input"
                placeholder="Search African groceries, spices, grains..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                aria-label="Search African groceries"
              />
              {searchQuery && (
                <button
                  type="button"
                  className="mobile-clear-btn"
                  onClick={() => setSearchQuery('')}
                  aria-label="Clear search"
                >
                  <X size={16} />
                </button>
              )}
              <button type="submit" className="mobile-search-submit">
                Search
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* 3. SECONDARY NAVIGATION ROW */}
      <nav className="site-header__secondary-nav" aria-label="Secondary navigation">
        <div className="container site-header__secondary-inner">
          <div className="nav-links-cluster">
            {/* Home */}
            <NavLink to="/" end className={({ isActive }) => `sec-nav-link ${isActive ? 'active' : ''}`}>
              Home
            </NavLink>

            {/* Shop All */}
            <NavLink to="/shop" end className={({ isActive }) => `sec-nav-link ${isActive ? 'active' : ''}`}>
              Shop All
            </NavLink>

            {/* Categories Mega Dropdown */}
            <div
              className="categories-dropdown-container"
              ref={dropdownRef}
              onMouseEnter={() => setCategoriesDropdownOpen(true)}
              onMouseLeave={() => setCategoriesDropdownOpen(false)}
            >
              <button
                className={`sec-nav-link categories-trigger-btn ${categoriesDropdownOpen ? 'active' : ''}`}
                onClick={() => setCategoriesDropdownOpen(!categoriesDropdownOpen)}
                aria-expanded={categoriesDropdownOpen}
                aria-haspopup="true"
              >
                <Layers size={16} className="nav-icon" />
                <span>Categories</span>
                <ChevronDown size={14} className={`chevron-indicator ${categoriesDropdownOpen ? 'rotate' : ''}`} />
              </button>

              {categoriesDropdownOpen && (
                <div className="categories-mega-menu" role="menu">
                  <div className="mega-menu-header">
                    <div>
                      <h4 className="mega-menu-title">Browse African Grocery Categories</h4>
                      <p className="mega-menu-subtitle">Selected authentic staples from trusted suppliers</p>
                    </div>
                    <Link
                      to="/shop"
                      className="mega-menu-view-all"
                      onClick={() => setCategoriesDropdownOpen(false)}
                    >
                      <span>Explore Entire Store</span>
                      <ArrowRight size={14} />
                    </Link>
                  </div>

                  <div className="mega-menu-grid">
                    {categories.length > 0 ? (
                      categories.map((cat) => {
                        const fallbackImg = getCategoryFallbackImage(cat.slug, cat.name);
                        const displayImage = cat.image || fallbackImg;
                        return (
                          <Link
                            key={cat.id}
                            to={`/categories/${cat.slug}`}
                            className="mega-menu-category-card"
                            role="menuitem"
                            onClick={() => setCategoriesDropdownOpen(false)}
                          >
                            <div className="category-card-thumb">
                              <img src={displayImage} alt={cat.name} loading="lazy" />
                            </div>
                            <div className="category-card-info">
                              <span className="category-title">{cat.name}</span>
                              <span className="category-qty">
                                {cat.product_count} {cat.product_count === 1 ? 'product' : 'products'}
                              </span>
                            </div>
                          </Link>
                        );
                      })
                    ) : (
                      <div className="mega-menu-empty">
                        <p>Loading categories...</p>
                        <Link to="/shop" onClick={() => setCategoriesDropdownOpen(false)}>
                          View All Catalog Products
                        </Link>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Popular Products */}
            <NavLink
              to="/shop?featured=true"
              className={({ isActive }) => `sec-nav-link ${isActive ? 'active' : ''}`}
            >
              <Flame size={15} className="nav-icon popular-icon" />
              <span>Popular Products</span>
            </NavLink>

            {/* In-Stock Items */}
            <NavLink
              to="/shop?in_stock=true"
              className={({ isActive }) => `sec-nav-link ${isActive ? 'active' : ''}`}
            >
              <CheckCircle size={15} className="nav-icon stock-icon" />
              <span>In-Stock Essentials</span>
            </NavLink>
          </div>

          {/* Quick value message on desktop */}
          <div className="sec-nav-promo">
            <span className="promo-text">100% Authentic Quality Guaranteed</span>
          </div>
        </div>
      </nav>

      {/* 4. MOBILE SLIDE-OUT MENU */}
      {mobileMenuOpen && (
        <div className="site-header__mobile-drawer" role="dialog" aria-modal="true">
          <div className="mobile-drawer-overlay" onClick={() => setMobileMenuOpen(false)} />
          <div className="mobile-drawer-content">
            <div className="mobile-drawer-header">
              <span className="mobile-drawer-brand">AdesHub African Market</span>
              <button
                className="mobile-drawer-close"
                onClick={() => setMobileMenuOpen(false)}
                aria-label="Close menu"
              >
                <X size={22} />
              </button>
            </div>

            <div className="mobile-drawer-body">
              <nav className="mobile-nav-links">
                <NavLink
                  to="/"
                  end
                  className="mobile-nav-item"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Home
                </NavLink>
                <NavLink
                  to="/shop"
                  end
                  className="mobile-nav-item"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Shop All Products
                </NavLink>
                <NavLink
                  to="/shop?featured=true"
                  className="mobile-nav-item"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <Flame size={16} className="popular-icon" />
                  Popular Products
                </NavLink>
                <NavLink
                  to="/shop?in_stock=true"
                  className="mobile-nav-item"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <CheckCircle size={16} className="stock-icon" />
                  In-Stock Essentials
                </NavLink>

                <div className="mobile-nav-divider" />
                <div className="mobile-section-heading">Browse Categories</div>

                <div className="mobile-categories-list">
                  {categories.map((cat) => (
                    <NavLink
                      key={cat.id}
                      to={`/categories/${cat.slug}`}
                      className="mobile-category-link"
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      <span>{cat.name}</span>
                      <span className="mobile-cat-count">{cat.product_count}</span>
                    </NavLink>
                  ))}
                </div>

                <div className="mobile-nav-divider" />
                <div className="mobile-section-heading">My Account</div>

                {isAuthenticated ? (
                  <>
                    {(user?.is_staff || user?.is_superuser) && (
                      <NavLink
                        to="/admin"
                        className="mobile-nav-item admin-portal-mobile"
                        onClick={() => setMobileMenuOpen(false)}
                      >
                        <ShieldCheck size={16} className="text-primary" /> Admin Dashboard
                      </NavLink>
                    )}
                    <NavLink
                      to="/account"
                      className="mobile-nav-item"
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      <User size={16} /> My Account {customerDisplayName !== 'My Account' ? `(${customerDisplayName})` : ''}
                    </NavLink>
                    <button
                      className="mobile-nav-item mobile-logout-btn"
                      onClick={() => {
                        setMobileMenuOpen(false);
                        handleLogout();
                      }}
                    >
                      <LogOut size={16} /> Log Out
                    </button>
                  </>
                ) : (
                  <>
                    <NavLink
                      to="/login"
                      className="mobile-nav-item mobile-login-highlight"
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      Sign In
                    </NavLink>
                    <NavLink
                      to="/register"
                      className="mobile-nav-item"
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      Register Free Account
                    </NavLink>
                  </>
                )}
              </nav>
            </div>
          </div>
        </div>
      )}
    </header>
  );
};
