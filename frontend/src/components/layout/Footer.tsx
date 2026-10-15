import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldCheck, Truck, RefreshCw, Mail } from 'lucide-react';
import './Footer.css';

// Clean standard SVG for Instagram
const InstagramIcon: React.FC<{ size?: number; className?: string }> = ({ size = 18, className = '' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-hidden="true"
  >
    <rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>
    <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path>
    <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line>
  </svg>
);

// Clean standard SVG for Facebook
const FacebookIcon: React.FC<{ size?: number; className?: string }> = ({ size = 18, className = '' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-hidden="true"
  >
    <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"></path>
  </svg>
);

// Clean standard SVG for TikTok
const TikTokIcon: React.FC<{ size?: number; className?: string }> = ({ size = 18, className = '' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="currentColor"
    className={className}
    aria-hidden="true"
  >
    <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.88 2.89 2.89 0 0 1-2.89-2.88 2.89 2.89 0 0 1 2.89-2.88c.28 0 .54.04.79.11V9.92a6.34 6.34 0 0 0-.79-.05A6.34 6.34 0 0 0 3 16.21a6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.34-6.34V9.08a8.28 8.28 0 0 0 5.24 1.83V7.47a4.84 4.84 0 0 1-1.33-.78z" />
  </svg>
);

export const Footer: React.FC = () => {
  return (
    <footer className="site-footer">
      {/* 1. Value Proposition & Trust Bar */}
      <div className="site-footer__trust-bar">
        <div className="container site-footer__trust-grid">
          <div className="site-footer__trust-item">
            <div className="trust-icon-box">
              <ShieldCheck className="trust-icon" size={26} />
            </div>
            <div>
              <h5 className="trust-title">100% Authentic Quality</h5>
              <p className="trust-desc">Directly sourced genuine African ingredients & pantry staples</p>
            </div>
          </div>

          <div className="site-footer__trust-item">
            <div className="trust-icon-box">
              <Truck className="trust-icon" size={26} />
            </div>
            <div>
              <h5 className="trust-title">Carefully Packed & Delivered</h5>
              <p className="trust-desc">Prompt, reliable grocery delivery direct to your doorstep</p>
            </div>
          </div>

          <div className="site-footer__trust-item">
            <div className="trust-icon-box">
              <RefreshCw className="trust-icon" size={26} />
            </div>
            <div>
              <h5 className="trust-title">Secure Online Ordering</h5>
              <p className="trust-desc">Encrypted Stripe payments with instant order confirmation</p>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Main Footer Grid */}
      <div className="site-footer__main">
        <div className="container site-footer__grid">
          {/* Brand Info & Socials Column */}
          <div className="site-footer__col site-footer__col--brand">
            <Link to="/" className="site-footer__logo" aria-label="AdesHub Home">
              <span className="logo-accent">Ades<span className="logo-hub">Hub</span></span>
              <span className="logo-badge">AFRICAN MARKET</span>
            </Link>
            <p className="site-footer__about">
              Your premier online African grocery marketplace. Bringing authentic African flavours, fresh yam tubers, premium oils, aromatic spices, and kitchen staples to your home.
            </p>

            {/* Verified Social Media Links */}
            <div className="site-footer__social-group">
              <span className="social-label">Follow & Connect:</span>
              <div className="site-footer__social-links">
                <a
                  href="mailto:Info@adeshub.co.uk"
                  className="social-btn social-btn--email"
                  title="Send us an email at Info@adeshub.co.uk"
                  aria-label="Email AdesHub at Info@adeshub.co.uk"
                >
                  <Mail size={18} />
                </a>

                <a
                  href="https://www.instagram.com/adeshub_africanfoodstore"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="social-btn social-btn--instagram"
                  title="Follow AdesHub on Instagram"
                  aria-label="Instagram @adeshub_africanfoodstore"
                >
                  <InstagramIcon size={18} />
                </a>

                <a
                  href="https://www.facebook.com/share/18cuqV2qX6/?mibextid=wwXIfr"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="social-btn social-btn--facebook"
                  title="Follow AdesHub on Facebook"
                  aria-label="Facebook Page"
                >
                  <FacebookIcon size={18} />
                </a>

                <a
                  href="https://www.tiktok.com/@adeshubafricanstore"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="social-btn social-btn--tiktok"
                  title="Follow AdesHub on TikTok"
                  aria-label="TikTok @adeshubafricanstore"
                >
                  <TikTokIcon size={18} />
                </a>
              </div>
            </div>

            <div className="site-footer__contact-direct">
              <Mail size={15} className="contact-icon" />
              <span>Direct Support: <a href="mailto:Info@adeshub.co.uk">Info@adeshub.co.uk</a></span>
            </div>
          </div>

          {/* Quick Links Column */}
          <div className="site-footer__col">
            <h4 className="site-footer__heading">Quick Links</h4>
            <ul className="site-footer__links">
              <li><Link to="/">Home Marketplace</Link></li>
              <li><Link to="/shop">Shop All Groceries</Link></li>
              <li><Link to="/shop?featured=true">Popular Products</Link></li>
              <li><Link to="/shop?in_stock=true">In-Stock Essentials</Link></li>
              <li><Link to="/cart">View Shopping Cart</Link></li>
            </ul>
          </div>

          {/* Grocery Categories Column */}
          <div className="site-footer__col">
            <h4 className="site-footer__heading">Top Categories</h4>
            <ul className="site-footer__links">
              <li><Link to="/categories/rice-grains">Rice & Grains</Link></li>
              <li><Link to="/categories/garri-cassava-products">Garri & Cassava Products</Link></li>
              <li><Link to="/categories/beans-legumes">Beans & Legumes</Link></li>
              <li><Link to="/categories/palm-oil-cooking-oils">Palm Oil & Cooking Oils</Link></li>
              <li><Link to="/categories/spices-seasonings">Spices & Seasonings</Link></li>
              <li><Link to="/shop">View All 15 Categories</Link></li>
            </ul>
          </div>

          {/* Customer Service Column */}
          <div className="site-footer__col">
            <h4 className="site-footer__heading">Customer Support</h4>
            <ul className="site-footer__links">
              <li><a href="mailto:Info@adeshub.co.uk">Contact Us (Info@adeshub.co.uk)</a></li>
              <li><Link to="/account">Track My Order</Link></li>
              <li><Link to="/account">Manage Addresses</Link></li>
              <li><span className="info-text">Secure Stripe Checkout</span></li>
              <li><span className="info-text">Careful Food Handling & Hygiene</span></li>
            </ul>
          </div>
        </div>
      </div>

      {/* 3. Bottom Copyright Bar */}
      <div className="site-footer__bottom">
        <div className="container site-footer__bottom-inner">
          <p>© 2026 AdesHub African Market. All rights reserved.</p>
          <div className="site-footer__bottom-badges">
            <span className="bottom-note">
              Authentic African Groceries Delivered Across the UK
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
};
