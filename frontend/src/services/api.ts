import type {
  Category,
  ProductDetail,
  ProductListItem,
  PaginatedResponse,
  ProductFilterParams,
  Cart,
  User,
  Address,
  AddressInput,
  Order,
  CreateOrderPayload,
  RegisterPayload,
  StripeCheckoutResponse,
  OrderPaymentStatusResponse,
  StripeConfigResponse,
  ProductImage,
  ProductVariant,
  DeliveryMethod,
  DeliveryQuoteResponse,
} from '../types/api';
import type {
  DashboardResponse,
  AdminOrderFilterParams,
  AdminProductFilterParams,
  ProductFormData,
} from '../types/admin';

export class ApiError extends Error {
  status: number;
  fieldErrors?: Record<string, string>;

  constructor(message: string, status: number, fieldErrors?: Record<string, string>) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api';

const CART_SESSION_KEY_STORAGE = 'adeshub_cart_session';
const AUTH_TOKEN_KEY_STORAGE = 'adeshub_auth_token';

export function getStoredAuthToken(): string | null {
  try {
    const token = localStorage.getItem(AUTH_TOKEN_KEY_STORAGE);
    return token && token.trim() !== '' ? token.trim() : null;
  } catch {
    return null;
  }
}

export function setStoredAuthToken(token: string | null): void {
  try {
    if (token && token.trim() !== '') {
      localStorage.setItem(AUTH_TOKEN_KEY_STORAGE, token.trim());
    } else {
      localStorage.removeItem(AUTH_TOKEN_KEY_STORAGE);
    }
  } catch {
    // ignore
  }
}

function getStoredCartSession(): string | null {
  try {
    const session = localStorage.getItem(CART_SESSION_KEY_STORAGE);
    return session && session.trim() !== '' ? session.trim() : null;
  } catch {
    return null;
  }
}

function storeCartSession(sessionKey: string) {
  try {
    if (sessionKey && sessionKey.trim() !== '') {
      localStorage.setItem(CART_SESSION_KEY_STORAGE, sessionKey.trim());
    }
  } catch {
    // ignore
  }
}

function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    'Accept': 'application/json',
  };
  const cartSession = getStoredCartSession();
  if (cartSession) {
    headers['X-Cart-Session'] = cartSession;
  }
  const token = getStoredAuthToken();
  if (token) {
    headers['Authorization'] = `Token ${token}`;
  }
  return headers;
}

function buildUrl(endpoint: string, params?: Record<string, string | number | boolean | undefined>): string {
  const baseUrl = API_BASE_URL.replace(/\/+$/, '');
  const cleanEndpoint = endpoint.replace(/^\/+/, '');
  const url = new URL(`${baseUrl}/${cleanEndpoint}`);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.append(key, String(value));
      }
    });
  }

  return url.toString();
}

async function handleResponse<T>(response: Response): Promise<T> {
  const sessionHeader = response.headers.get('X-Cart-Session') || response.headers.get('x-cart-session');
  if (sessionHeader) {
    storeCartSession(sessionHeader);
  }

  if (!response.ok) {
    let errorMessage = `Server returned status code ${response.status}.`;
    let fieldErrors: Record<string, string> | undefined = undefined;

    try {
      const data = await response.json();
      if (typeof data === 'string') {
        errorMessage = data;
      } else if (data.detail) {
        errorMessage = data.detail;
      } else if (data.error) {
        errorMessage = data.error;
      } else if (data.non_field_errors) {
        errorMessage = Array.isArray(data.non_field_errors) ? data.non_field_errors[0] : String(data.non_field_errors);
      }

      if (typeof data === 'object' && data !== null && !Array.isArray(data)) {
        const parsedFields: Record<string, string> = {};
        for (const [key, val] of Object.entries(data)) {
          if (key === 'detail' || key === 'error') continue;
          const msg = Array.isArray(val) ? val[0] : String(val);
          parsedFields[key] = msg;
        }
        if (Object.keys(parsedFields).length > 0) {
          fieldErrors = parsedFields;
          if (!data.detail && !data.error && !data.non_field_errors) {
            const firstKey = Object.keys(parsedFields)[0];
            errorMessage = `${firstKey}: ${parsedFields[firstKey]}`;
          }
        }
      }
    } catch {
      // json parse error, keep generic error message
    }
    throw new ApiError(errorMessage, response.status, fieldErrors);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return await response.json();
}


async function apiFetch<T>(url: string, options?: RequestInit & { timeoutMs?: number }): Promise<T> {
  const timeoutMs = options?.timeoutMs ?? 25000;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: options?.signal || controller.signal,
      headers: {
        ...getAuthHeaders(),
        ...options?.headers,
      },
      credentials: 'include',
    });

    return await handleResponse<T>(response);
  } catch (error: unknown) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Network request timed out. Please check your internet connection and try again.');
    }
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected network error occurred while connecting to AdesHub backend.');
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  // Catalog APIs
  async getCategories(): Promise<Category[]> {
    const url = buildUrl('categories/');
    const data = await apiFetch<Category[] | PaginatedResponse<Category>>(url);
    if (Array.isArray(data)) {
      return data;
    }
    return data.results || [];
  },

  async getCategoryDetail(slug: string): Promise<Category> {
    const url = buildUrl(`categories/${slug}/`);
    return await apiFetch<Category>(url);
  },

  async getProducts(params?: ProductFilterParams): Promise<PaginatedResponse<ProductListItem>> {
    const queryParams: Record<string, string | number | boolean | undefined> = {};
    if (params?.category) queryParams.category = params.category;
    if (params?.featured !== undefined) queryParams.featured = params.featured;
    if (params?.in_stock !== undefined) queryParams.in_stock = params.in_stock;
    if (params?.search) queryParams.search = params.search;
    if (params?.page) queryParams.page = params.page;

    const url = buildUrl('products/', queryParams);
    const data = await apiFetch<PaginatedResponse<ProductListItem> | ProductListItem[]>(url);

    if (Array.isArray(data)) {
      return {
        count: data.length,
        next: null,
        previous: null,
        results: data,
      };
    }
    return data;
  },

  async getProductDetail(slug: string): Promise<ProductDetail> {
    const url = buildUrl(`products/${slug}/`);
    return await apiFetch<ProductDetail>(url);
  },

  // Shopping Cart APIs
  async getCart(): Promise<Cart> {
    const url = buildUrl('cart/');
    return await apiFetch<Cart>(url);
  },

  async addToCart(productId: number, variantId?: number | null, quantity: number = 1): Promise<Cart> {
    const url = buildUrl('cart/items/');
    const body: { product: number; variant?: number; quantity: number } = {
      product: productId,
      quantity,
    };
    if (variantId) {
      body.variant = variantId;
    }
    return await apiFetch<Cart>(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
  },

  async updateCartItem(itemId: number, quantity: number): Promise<Cart> {
    const url = buildUrl(`cart/items/${itemId}/`);
    return await apiFetch<Cart>(url, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ quantity }),
    });
  },

  async removeCartItem(itemId: number): Promise<Cart> {
    const url = buildUrl(`cart/items/${itemId}/`);
    return await apiFetch<Cart>(url, {
      method: 'DELETE',
    });
  },

  async clearCart(): Promise<Cart> {
    const url = buildUrl('cart/');
    return await apiFetch<Cart>(url, {
      method: 'DELETE',
    });
  },

  // Auth APIs
  async login(email: string, password: string): Promise<{ token: string; user: User }> {
    const url = buildUrl('auth/login/');
    const res = await apiFetch<{ token: string; user: User }>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (res.token) {
      setStoredAuthToken(res.token);
    }
    return res;
  },

  async register(data: RegisterPayload): Promise<{ token: string; user: User }> {
    const url = buildUrl('auth/register/');
    const res = await apiFetch<{ token: string; user: User }>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (res.token) {
      setStoredAuthToken(res.token);
    }
    return res;
  },

  async logout(): Promise<void> {
    const url = buildUrl('auth/logout/');
    try {
      await apiFetch<void>(url, { method: 'POST' });
    } finally {
      setStoredAuthToken(null);
    }
  },

  async getProfile(): Promise<User> {
    const url = buildUrl('auth/me/');
    return await apiFetch<User>(url);
  },

  async updateProfile(data: Partial<{ first_name: string; last_name: string; phone_number: string; email: string }>): Promise<User> {
    const url = buildUrl('auth/me/');
    const res = await apiFetch<{ message: string; user: User } | User>(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (res && 'user' in res && res.user) {
      return res.user;
    }
    return res as User;
  },

  async changePassword(currentPassword: string, newPassword: string, newPasswordConfirm: string): Promise<{ message: string }> {
    const url = buildUrl('auth/change-password/');
    return await apiFetch<{ message: string }>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
        new_password_confirm: newPasswordConfirm,
      }),
    });
  },

  async requestPasswordReset(email: string): Promise<{ message: string }> {
    const url = buildUrl('auth/password-reset/');
    return await apiFetch<{ message: string }>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
  },

  async validatePasswordResetToken(uid: string, token: string): Promise<{ valid: boolean; message?: string }> {
    const url = buildUrl('auth/password-reset/validate/');
    return await apiFetch<{ valid: boolean; message?: string }>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ uid, token }),
    });
  },

  async confirmPasswordReset(data: {
    uid: string;
    token: string;
    new_password: string;
    new_password_confirm: string;
  }): Promise<{ message: string }> {
    const url = buildUrl('auth/password-reset/confirm/');
    return await apiFetch<{ message: string }>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },

  // Address APIs
  async getAddresses(): Promise<Address[]> {
    const url = buildUrl('auth/addresses/');
    return await apiFetch<Address[]>(url);
  },

  async createAddress(addressData: AddressInput): Promise<Address> {
    const url = buildUrl('auth/addresses/');
    return await apiFetch<Address>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(addressData),
    });
  },

  async updateAddress(id: number, addressData: Partial<AddressInput>): Promise<Address> {
    const url = buildUrl(`auth/addresses/${id}/`);
    return await apiFetch<Address>(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(addressData),
    });
  },

  async deleteAddress(id: number): Promise<void> {
    const url = buildUrl(`auth/addresses/${id}/`);
    await apiFetch<void>(url, { method: 'DELETE' });
  },

  // Order APIs
  async createOrder(payload: CreateOrderPayload): Promise<Order> {
    const url = buildUrl('orders/');
    return await apiFetch<Order>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  },

  async getMyOrders(): Promise<PaginatedResponse<Order> | Order[]> {
    const url = buildUrl('orders/my-orders/');
    return await apiFetch<PaginatedResponse<Order> | Order[]>(url);
  },

  async getOrderDetail(orderReference: string, email?: string, sessionId?: string): Promise<Order> {
    const params: Record<string, string> = {};
    if (email) params.email = email;
    if (sessionId) params.session_id = sessionId;
    const url = buildUrl(`orders/${orderReference}/`, Object.keys(params).length ? params : undefined);
    return await apiFetch<Order>(url);
  },

  async getDeliveryQuote(subtotal?: number | string, method?: string): Promise<DeliveryQuoteResponse> {
    const params: Record<string, string> = {};
    if (subtotal !== undefined) params.subtotal = String(subtotal);
    if (method) params.method = method;
    const url = buildUrl('orders/delivery-quote/', Object.keys(params).length ? params : undefined);
    return await apiFetch<DeliveryQuoteResponse>(url);
  },

  async getDeliveryMethods(): Promise<DeliveryMethod[]> {
    const url = buildUrl('orders/delivery-methods/');
    return await apiFetch<DeliveryMethod[]>(url);
  },

  // Stripe Payment Gateway APIs
  async createCheckoutSession(orderReference: string): Promise<StripeCheckoutResponse> {
    const url = buildUrl(`orders/${orderReference}/create-checkout-session/`);
    const data = await apiFetch<StripeCheckoutResponse>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!data.checkout_url || !data.checkout_url.startsWith('https://checkout.stripe.com/')) {
      throw new Error('Received an invalid or untrusted Stripe Checkout redirect URL.');
    }
    return data;
  },

  async getOrderPaymentStatus(orderReference: string, sessionId?: string, email?: string): Promise<OrderPaymentStatusResponse> {
    const params: Record<string, string> = {};
    if (sessionId) params.session_id = sessionId;
    if (email) params.email = email;
    const url = buildUrl(`orders/${orderReference}/payment-status/`, Object.keys(params).length ? params : undefined);
    return await apiFetch<OrderPaymentStatusResponse>(url);
  },

  async getStripeConfig(): Promise<StripeConfigResponse> {
    const url = buildUrl('orders/stripe/config/');
    return await apiFetch<StripeConfigResponse>(url);
  },

  // ==========================================
  // Custom Business Administration APIs
  // ==========================================

  async getAdminDashboard(): Promise<DashboardResponse> {
    const url = buildUrl('admin/dashboard/');
    return await apiFetch<DashboardResponse>(url);
  },

  async getAdminOrders(params?: AdminOrderFilterParams): Promise<PaginatedResponse<Order>> {
    const url = buildUrl('admin/orders/', params as Record<string, string | number | boolean | undefined>);
    return await apiFetch<PaginatedResponse<Order>>(url);
  },

  async getAdminOrderDetail(reference: string): Promise<Order> {
    const url = buildUrl(`admin/orders/${reference}/`);
    return await apiFetch<Order>(url);
  },

  async updateAdminOrderStatus(
    reference: string,
    payload:
      | string
      | {
          order_status?: string;
          courier_name?: string;
          shipment_reference?: string;
          tracking_number?: string;
          tracking_url?: string;
        }
  ): Promise<Order> {
    const body = typeof payload === 'string' ? { order_status: payload } : payload;
    const url = buildUrl(`admin/orders/${reference}/status/`);
    return await apiFetch<Order>(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  },

  async getAdminProducts(params?: AdminProductFilterParams): Promise<PaginatedResponse<ProductDetail>> {
    const url = buildUrl('admin/products/', params as Record<string, string | number | boolean | undefined>);
    return await apiFetch<PaginatedResponse<ProductDetail>>(url);
  },

  async updateProductStock(slug: string, stockQuantity: number, variantId?: number): Promise<ProductDetail> {
    const url = buildUrl(`admin/products/${slug}/stock/`);
    return await apiFetch<ProductDetail>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        stock_quantity: stockQuantity,
        ...(variantId ? { variant_id: variantId } : {}),
      }),
    });
  },

  async createProduct(productData: Partial<ProductFormData>): Promise<ProductDetail> {
    const url = buildUrl('products/');
    return await apiFetch<ProductDetail>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(productData),
    });
  },

  async updateProduct(slug: string, productData: Partial<ProductFormData>): Promise<ProductDetail> {
    const url = buildUrl(`products/${slug}/`);
    return await apiFetch<ProductDetail>(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(productData),
    });
  },

  async deleteProduct(slug: string): Promise<void> {
    const url = buildUrl(`products/${slug}/`);
    await apiFetch<void>(url, { method: 'DELETE' });
  },

  async createProductImage(slug: string, formData: FormData): Promise<ProductImage> {
    const url = buildUrl(`products/${slug}/images/`);
    return await apiFetch<ProductImage>(url, {
      method: 'POST',
      body: formData,
    });
  },

  async deleteProductImage(slug: string, imageId: number): Promise<void> {
    const url = buildUrl(`products/${slug}/images/${imageId}/`);
    await apiFetch<void>(url, { method: 'DELETE' });
  },

  async createProductVariant(slug: string, variantData: Partial<ProductVariant>): Promise<ProductVariant> {
    const url = buildUrl(`products/${slug}/variants/`);
    return await apiFetch<ProductVariant>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(variantData),
    });
  },

  async updateProductVariant(slug: string, variantId: number, variantData: Partial<ProductVariant>): Promise<ProductVariant> {
    const url = buildUrl(`products/${slug}/variants/${variantId}/`);
    return await apiFetch<ProductVariant>(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(variantData),
    });
  },

  async deleteProductVariant(slug: string, variantId: number): Promise<void> {
    const url = buildUrl(`products/${slug}/variants/${variantId}/`);
    await apiFetch<void>(url, { method: 'DELETE' });
  },

  async createCategory(categoryData: { name: string; description?: string; is_active?: boolean }): Promise<Category> {
    const url = buildUrl('categories/');
    return await apiFetch<Category>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(categoryData),
    });
  },

  async updateCategory(slug: string, categoryData: Partial<Category>): Promise<Category> {
    const url = buildUrl(`categories/${slug}/`);
    return await apiFetch<Category>(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(categoryData),
    });
  },

  async deleteCategory(slug: string): Promise<void> {
    const url = buildUrl(`categories/${slug}/`);
    await apiFetch<void>(url, { method: 'DELETE' });
  },
};

export const authApi = api;

