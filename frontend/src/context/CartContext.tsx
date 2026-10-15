import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { Cart } from '../types/api';
import { api } from '../services/api';

export interface ToastNotice {
  id: string;
  type: 'success' | 'error' | 'info';
  text: string;
}

interface CartContextType {
  cart: Cart | null;
  loading: boolean;
  actionLoading: boolean;
  itemLoadingMap: Record<string, boolean>;
  toast: ToastNotice | null;
  clearToast: () => void;
  showToast: (text: string, type?: 'success' | 'error' | 'info') => void;
  addToCart: (productId: number, variantId?: number | null, quantity?: number) => Promise<boolean>;
  updateQuantity: (itemId: number, quantity: number) => Promise<boolean>;
  removeItem: (itemId: number) => Promise<boolean>;
  clearCart: () => Promise<boolean>;
  refreshCart: () => Promise<void>;
}

const CartContext = createContext<CartContextType | undefined>(undefined);

export const CartProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [cart, setCart] = useState<Cart | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [itemLoadingMap, setItemLoadingMap] = useState<Record<string, boolean>>({});
  const [toast, setToast] = useState<ToastNotice | null>(null);

  const clearToast = useCallback(() => {
    setToast(null);
  }, []);

  const showToast = useCallback((text: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = Date.now().toString();
    setToast({ id, type, text });
    setTimeout(() => {
      setToast((prev) => (prev?.id === id ? null : prev));
    }, 4000);
  }, []);

  const refreshCart = useCallback(async () => {
    try {
      const data = await api.getCart();
      setCart(data);
    } catch (err) {
      console.error('Failed to fetch shopping cart:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshCart();
  }, [refreshCart]);

  const setItemLoading = (key: string, isLoading: boolean) => {
    setItemLoadingMap((prev) => ({ ...prev, [key]: isLoading }));
  };

  const addToCart = async (
    productId: number,
    variantId?: number | null,
    quantity: number = 1
  ): Promise<boolean> => {
    const key = `add_${productId}_${variantId || 0}`;
    setItemLoading(key, true);
    setActionLoading(true);
    try {
      const updatedCart = await api.addToCart(productId, variantId, quantity);
      setCart(updatedCart);
      showToast('Item successfully added to cart!', 'success');
      return true;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Could not add product to cart.';
      showToast(msg, 'error');
      return false;
    } finally {
      setItemLoading(key, false);
      setActionLoading(false);
    }
  };

  const updateQuantity = async (itemId: number, quantity: number): Promise<boolean> => {
    const key = `update_${itemId}`;
    setItemLoading(key, true);
    setActionLoading(true);
    try {
      const updatedCart = await api.updateCartItem(itemId, quantity);
      setCart(updatedCart);
      showToast('Cart quantity updated', 'info');
      return true;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to update quantity.';
      showToast(msg, 'error');
      return false;
    } finally {
      setItemLoading(key, false);
      setActionLoading(false);
    }
  };

  const removeItem = async (itemId: number): Promise<boolean> => {
    const key = `remove_${itemId}`;
    setItemLoading(key, true);
    setActionLoading(true);
    try {
      const updatedCart = await api.removeCartItem(itemId);
      setCart(updatedCart);
      showToast('Item removed from cart', 'info');
      return true;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to remove item.';
      showToast(msg, 'error');
      return false;
    } finally {
      setItemLoading(key, false);
      setActionLoading(false);
    }
  };

  const clearCart = async (): Promise<boolean> => {
    setActionLoading(true);
    try {
      const clearedCart = await api.clearCart();
      setCart(clearedCart);
      showToast('Cart cleared', 'info');
      return true;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to clear cart.';
      showToast(msg, 'error');
      return false;
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <CartContext.Provider
      value={{
        cart,
        loading,
        actionLoading,
        itemLoadingMap,
        toast,
        clearToast,
        showToast,
        addToCart,
        updateQuantity,
        removeItem,
        clearCart,
        refreshCart,
      }}
    >
      {children}
    </CartContext.Provider>
  );
};

export const useCart = (): CartContextType => {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
};
