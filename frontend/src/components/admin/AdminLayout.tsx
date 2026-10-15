import React, { useState } from 'react';
import { NavLink, Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { getUserDisplayName, getUserAvatarInitial } from '../../utils/userDisplay';
import {
  LayoutDashboard,
  ShoppingBag,
  Package,
  Layers,
  LogOut,
  Menu,
  X,
  ShieldCheck,
  ShieldAlert,
  Store,
  ChevronRight,
  ExternalLink
} from 'lucide-react';
import './AdminLayout.css';

export const AdminLayout: React.FC = () => {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  // 1. Loading state
  if (isLoading) {
    return (
      <div className="admin-loading-screen">
        <div className="admin-spinner" />
        <p className="admin-loading-text">Verifying administrative access...</p>
      </div>
    );
  }

  // 2. Unauthenticated check
  if (!isAuthenticated) {
    navigate(`/login?redirect=${encodeURIComponent(location.pathname)}`, { replace: true });
    return null;
  }

  // 3. Staff / Administrator authorization gate (enforced on both React & Django backend)
  const isAuthorized = Boolean(user?.is_staff || user?.is_superuser);
  if (!isAuthorized) {
    return (
      <div className="admin-access-denied-container">
        <div className="access-denied-card">
          <div className="access-denied-icon">
            <ShieldAlert size={48} className="text-error" />
          </div>
          <h2 className="access-denied-title">Administrator Access Required</h2>
          <p className="access-denied-message">
            Your account (<strong>{user?.email}</strong>) does not have staff permissions to access the AdesHub business management dashboard.
          </p>
          <div className="access-denied-actions">
            <Link to="/" className="btn-return-shop">
              <Store size={16} /> Return to Storefront
            </Link>
            <Link to="/account" className="btn-my-account">
              My Customer Account
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="admin-layout-shell">
      {/* Mobile Sidebar Backdrop */}
      {mobileSidebarOpen && (
        <div
          className="admin-sidebar-backdrop"
          onClick={() => setMobileSidebarOpen(false)}
        />
      )}

      {/* Sidebar Navigation */}
      <aside className={`admin-sidebar ${mobileSidebarOpen ? 'open' : ''}`}>
        <div className="admin-sidebar-header">
          <Link to="/admin" className="admin-brand-link" onClick={() => setMobileSidebarOpen(false)}>
            <div className="admin-brand-badge">
              <ShieldCheck size={18} />
            </div>
            <div className="admin-brand-text">
              <span className="brand-title">AdesHub</span>
              <span className="brand-subtitle">Business Management</span>
            </div>
          </Link>
          <button
            type="button"
            className="mobile-close-sidebar-btn"
            onClick={() => setMobileSidebarOpen(false)}
            aria-label="Close menu"
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="admin-nav-menu" aria-label="Admin Navigation">
          <div className="nav-section-label">Operations</div>
          <NavLink
            to="/admin"
            end
            className={({ isActive }) => `admin-nav-item ${isActive ? 'active' : ''}`}
            onClick={() => setMobileSidebarOpen(false)}
          >
            <LayoutDashboard size={18} className="nav-icon" />
            <span>Dashboard Overview</span>
          </NavLink>

          <NavLink
            to="/admin/orders"
            className={({ isActive }) => `admin-nav-item ${isActive ? 'active' : ''}`}
            onClick={() => setMobileSidebarOpen(false)}
          >
            <ShoppingBag size={18} className="nav-icon" />
            <span>Orders & Fulfilment</span>
          </NavLink>

          <div className="nav-section-label">Catalog & Stock</div>
          <NavLink
            to="/admin/products"
            className={({ isActive }) => `admin-nav-item ${isActive ? 'active' : ''}`}
            onClick={() => setMobileSidebarOpen(false)}
          >
            <Package size={18} className="nav-icon" />
            <span>Products & Inventory</span>
          </NavLink>

          <NavLink
            to="/admin/categories"
            className={({ isActive }) => `admin-nav-item ${isActive ? 'active' : ''}`}
            onClick={() => setMobileSidebarOpen(false)}
          >
            <Layers size={18} className="nav-icon" />
            <span>Categories</span>
          </NavLink>
        </nav>

        {/* Sidebar Footer */}
        <div className="admin-sidebar-footer">
          <Link to="/" className="storefront-link" target="_blank" rel="noopener noreferrer">
            <Store size={15} />
            <span>View Live Storefront</span>
            <ExternalLink size={12} className="ml-auto" />
          </Link>

          <div className="admin-user-profile-badge">
            <div className="admin-avatar">
              {getUserAvatarInitial(user)}
            </div>
            <div className="admin-user-info">
              <span className="admin-user-name">{getUserDisplayName(user)}</span>
              <span className="admin-user-role">
                {user?.is_superuser ? 'Super Administrator' : 'Staff Member'}
              </span>
            </div>
            <button
              type="button"
              className="admin-logout-btn"
              onClick={handleLogout}
              title="Log out"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="admin-main-wrapper">
        {/* Top Navbar */}
        <header className="admin-topbar">
          <div className="topbar-left">
            <button
              type="button"
              className="mobile-hamburger-btn"
              onClick={() => setMobileSidebarOpen(true)}
              aria-label="Open sidebar navigation"
            >
              <Menu size={20} />
            </button>
            <div className="breadcrumbs">
              <span className="breadcrumb-root">Admin</span>
              <ChevronRight size={14} className="text-muted" />
              <span className="breadcrumb-current">
                {location.pathname === '/admin' && 'Dashboard Overview'}
                {location.pathname.startsWith('/admin/orders') && 'Order Management'}
                {location.pathname.startsWith('/admin/products') && 'Product & Stock Management'}
                {location.pathname.startsWith('/admin/categories') && 'Category Management'}
              </span>
            </div>
          </div>

          <div className="topbar-right">
            <div className="system-status-indicator">
              <span className="live-pulse-dot" />
              <span className="live-pulse-text">System Live</span>
            </div>
            <Link to="/" className="btn-storefront-compact" title="Open storefront">
              <Store size={15} />
              <span className="hide-mobile">Storefront</span>
            </Link>
          </div>
        </header>

        {/* Routed Page Container */}
        <main className="admin-page-container">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
