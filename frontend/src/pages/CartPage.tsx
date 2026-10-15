import React from 'react';
import { Link } from 'react-router-dom';
import { ShoppingBag, Trash2, ArrowLeft, Plus, Minus, Loader2, ArrowRight, ShieldCheck, RefreshCw } from 'lucide-react';
import { useCart } from '../context/CartContext';
import { formatCurrency } from '../components/ui/PriceDisplay';
import { Badge } from '../components/ui/Badge';
import { LoadingState } from '../components/ui/LoadingState';
import './CartPage.css';

export const CartPage: React.FC = () => {
  const { cart, loading, actionLoading, itemLoadingMap, updateQuantity, removeItem, clearCart } = useCart();

  React.useEffect(() => {
    document.title = 'Shopping Cart | AdesHub Market';
  }, []);

  if (loading && !cart) {
    return (
      <div className="cart-page">
        <div className="container">
          <LoadingState type="inline" message="Loading your shopping cart..." />
        </div>
      </div>
    );
  }

  const items = cart?.items || [];
  const isEmpty = items.length === 0;

  return (
    <div className="cart-page">
      <div className="container">
        <nav className="cart-page__breadcrumb" aria-label="Breadcrumb">
          <Link to="/">Home</Link>
          <span>/</span>
          <span className="current">Shopping Cart</span>
        </nav>

        <div className="cart-page__header">
          <h1 className="heading-lg cart-page__title">Shopping Cart</h1>
          {!isEmpty && (
            <div className="cart-page__header-actions">
              <span className="cart-page__count-badge">
                {cart?.total_quantity} {cart?.total_quantity === 1 ? 'item' : 'items'}
              </span>
              <Link to="/shop" className="cart-page__header-continue-btn">
                <ArrowLeft size={16} />
                <span>Continue Shopping</span>
              </Link>
            </div>
          )}
        </div>

        {isEmpty ? (
          <div className="cart-page__empty-state">
            <div className="cart-page__empty-icon-wrapper">
              <ShoppingBag size={64} className="cart-page__empty-icon" />
            </div>
            <h2 className="heading-md cart-page__empty-title">Your cart is empty</h2>
            <p className="cart-page__empty-text">
              Browse our selection of premium African foods and groceries and add something you love.
            </p>
            <Link to="/shop" className="cart-page__continue-btn">
              <ArrowLeft size={18} />
              <span>Continue Shopping</span>
            </Link>
          </div>
        ) : (
          <div className="cart-page__grid">
            {/* Left Column: Cart Items List */}
            <div className="cart-page__items-column">
              <div className="cart-page__table-header">
                <span className="th-product">Product</span>
                <span className="th-price">Price</span>
                <span className="th-quantity">Quantity</span>
                <span className="th-total">Total</span>
                <span className="th-action"></span>
              </div>

              <div className="cart-page__items-list">
                {items.map((item) => {
                  const updateKey = `update_${item.id}`;
                  const removeKey = `remove_${item.id}`;
                  const isUpdating = !!itemLoadingMap[updateKey];
                  const isRemoving = !!itemLoadingMap[removeKey];
                  const stock = item.variant ? item.variant.stock_quantity : item.product.stock_quantity;
                  const isLowStock = stock > 0 && stock <= 5;
                  const isOutOfStock = stock <= 0 || !item.product.is_active || (item.variant && !item.variant.is_active);

                  return (
                    <div key={item.id} className={`cart-item ${isOutOfStock ? 'cart-item--unavailable' : ''}`}>
                      <div className="cart-item__product-col">
                        <Link to={`/products/${item.product.slug}`} className="cart-item__image-link">
                          {item.product.primary_image ? (
                            <img
                              src={item.product.primary_image}
                              alt={item.product.name}
                              className="cart-item__image"
                            />
                          ) : (
                            <div className="cart-item__fallback-img">
                              <ShoppingBag size={24} />
                            </div>
                          )}
                        </Link>

                        <div className="cart-item__details">
                          <Link to={`/products/${item.product.slug}`} className="cart-item__name">
                            {item.product.name}
                          </Link>

                          {item.variant && (
                            <div className="cart-item__variant-tag">
                              Option: <strong>{item.variant.name}</strong>
                            </div>
                          )}

                          <div className="cart-item__stock-status">
                            {isOutOfStock ? (
                              <Badge variant="error">Item Unavailable / Out of Stock</Badge>
                            ) : isLowStock ? (
                              <Badge variant="warning">Only {stock} left in stock</Badge>
                            ) : null}
                          </div>
                        </div>
                      </div>

                      <div className="cart-item__price-col">
                        <span className="cart-item__label">Price:</span>
                        <span className="cart-item__price-val">{formatCurrency(item.unit_price)}</span>
                      </div>

                      <div className="cart-item__quantity-col">
                        <span className="cart-item__label">Qty:</span>
                        <div className="cart-item__stepper">
                          <button
                            type="button"
                            className="cart-item__stepper-btn"
                            disabled={item.quantity <= 1 || isUpdating || isRemoving}
                            onClick={() => updateQuantity(item.id, item.quantity - 1)}
                            aria-label="Decrease quantity"
                          >
                            <Minus size={14} />
                          </button>
                          <span className="cart-item__stepper-val">
                            {isUpdating ? <Loader2 size={14} className="animate-spin" /> : item.quantity}
                          </span>
                          <button
                            type="button"
                            className="cart-item__stepper-btn"
                            disabled={item.quantity >= stock || isUpdating || isRemoving}
                            onClick={() => updateQuantity(item.id, item.quantity + 1)}
                            aria-label="Increase quantity"
                          >
                            <Plus size={14} />
                          </button>
                        </div>
                      </div>

                      <div className="cart-item__total-col">
                        <span className="cart-item__label">Line Total:</span>
                        <span className="cart-item__total-val">{formatCurrency(item.line_total)}</span>
                      </div>

                      <div className="cart-item__action-col">
                        <button
                          type="button"
                          className="cart-item__remove-btn"
                          disabled={isRemoving || actionLoading}
                          onClick={() => removeItem(item.id)}
                          title="Remove item"
                          aria-label="Remove item"
                        >
                          {isRemoving ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={18} />}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="cart-page__actions-row">
                <Link to="/shop" className="cart-page__continue-link">
                  <ArrowLeft size={16} />
                  <span>Continue Shopping</span>
                </Link>

                <button
                  type="button"
                  className="cart-page__clear-btn"
                  onClick={() => clearCart()}
                  disabled={actionLoading}
                >
                  <RefreshCw size={14} />
                  <span>Clear Cart</span>
                </button>
              </div>
            </div>

            {/* Right Column: Order Summary */}
            <div className="cart-page__summary-column">
              <div className="cart-summary-box">
                <h2 className="cart-summary-box__title">Order Summary</h2>

                <div className="cart-summary-box__row">
                  <span>Subtotal ({cart?.total_quantity} items)</span>
                  <span className="cart-summary-box__val">{formatCurrency(cart?.subtotal || '0.00')}</span>
                </div>

                <div className="cart-summary-box__row">
                  <span>Standard Shipping</span>
                  <span className="cart-summary-box__subtext">Calculated at checkout</span>
                </div>

                <div className="cart-summary-box__divider"></div>

                <div className="cart-summary-box__row cart-summary-box__row--total">
                  <span>Subtotal</span>
                  <span className="cart-summary-box__total-val">{formatCurrency(cart?.subtotal || '0.00')}</span>
                </div>

                <div className="cart-summary-box__notice">
                  <ShieldCheck size={16} className="cart-summary-box__notice-icon" />
                  <span>Secure session cart. Prices locked at current catalog rates.</span>
                </div>

                <Link
                  to="/checkout"
                  className="cart-summary-box__checkout-btn"
                >
                  <span>Proceed to Checkout</span>
                  <ArrowRight size={18} />
                </Link>

                <p className="cart-summary-box__checkout-note">
                  Fast & secure UK delivery checkout.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
