export interface CategorySummary {
  id: number;
  name: string;
  slug: string;
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  description: string;
  image: string | null;
  is_active: boolean;
  product_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProductImage {
  id: number;
  image: string;
  alt_text: string;
  is_primary: boolean;
  display_order: number;
  created_at: string;
}

export interface ProductVariant {
  id: number;
  product: number;
  name: string;
  sku: string;
  price: string;
  compare_at_price: string | null;
  stock_quantity: number;
  is_active: boolean;
  is_in_stock: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductListItem {
  id: number;
  name: string;
  slug: string;
  category: CategorySummary | null;
  sku: string;
  price: string;
  compare_at_price: string | null;
  stock_quantity: number;
  total_stock: number;
  is_in_stock: boolean;
  has_variants: boolean;
  is_active: boolean;
  is_featured: boolean;
  primary_image: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductDetail extends ProductListItem {
  description: string;
  low_stock_threshold: number;
  is_low_stock: boolean;
  images: ProductImage[];
  variants: ProductVariant[];
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ProductFilterParams {
  category?: string;
  featured?: boolean;
  in_stock?: boolean;
  search?: string;
  page?: number;
}

export interface CartItemProduct {
  id: number;
  name: string;
  slug: string;
  sku: string;
  primary_image: string | null;
  price: string;
  has_variants: boolean;
  is_active: boolean;
  is_in_stock: boolean;
  stock_quantity: number;
}

export interface CartItemVariant {
  id: number;
  name: string;
  sku: string;
  price: string;
  is_active: boolean;
  is_in_stock: boolean;
  stock_quantity: number;
}

export interface CartItem {
  id: number;
  product: CartItemProduct;
  variant: CartItemVariant | null;
  quantity: number;
  unit_price: string;
  line_total: string;
  created_at: string;
  updated_at: string;
}

export interface Cart {
  id: number;
  items: CartItem[];
  subtotal: string;
  total_quantity: number;
  item_count: number;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: number;
  email: string;
  username?: string | null;
  first_name: string;
  last_name: string;
  full_name: string;
  display_name?: string;
  phone_number: string;
  user_type: string;
  is_active: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  date_joined: string;
  updated_at: string;
}

export interface Address {
  id: number;
  recipient_name: string;
  phone_number: string;
  address_line1: string;
  address_line2: string;
  city: string;
  county_region: string;
  postal_code: string;
  country: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface AddressInput {
  recipient_name: string;
  phone_number: string;
  address_line1: string;
  address_line2?: string;
  city: string;
  county_region?: string;
  postal_code: string;
  country?: string;
  is_default?: boolean;
}

export interface OrderItem {
  id: number;
  product: number | null;
  variant: number | null;
  product_name: string;
  variant_name: string;
  sku: string;
  unit_price: string;
  quantity: number;
  line_total: string;
  created_at: string;
}

export interface Order {
  id: number;
  order_reference: string;
  customer_name: string;
  customer_email: string;
  recipient_name: string;
  phone_number: string;
  address_line1: string;
  address_line2: string;
  city: string;
  county_region: string;
  postal_code: string;
  country: string;
  subtotal: string;
  delivery_fee: string;
  total_amount: string;
  order_status: 'PENDING' | 'CONFIRMED' | 'PROCESSING' | 'SHIPPED' | 'DELIVERED' | 'CANCELLED';
  payment_status: 'PENDING' | 'PAID' | 'FAILED' | 'REFUNDED';
  delivery_method_name?: string;
  courier_name?: string;
  shipment_reference?: string;
  tracking_number?: string;
  tracking_url?: string;
  dispatched_at?: string | null;
  delivered_at?: string | null;
  stripe_checkout_session_id?: string | null;
  stripe_payment_intent_id?: string | null;
  confirmation_email_sent?: boolean;
  confirmation_email_sent_at?: string | null;
  email_delivery_status?: string;
  notes: string;
  items: OrderItem[];
  created_at: string;
  updated_at: string;
}

export interface DeliveryMethod {
  id: number;
  name: string;
  code: string;
  description: string;
  base_fee: string;
  free_delivery_threshold: string | null;
  estimated_days: string;
  is_default: boolean;
  calculated_fee?: string;
  is_free?: boolean;
}

export interface DeliveryQuoteResponse {
  methods: DeliveryMethod[];
  selected_method_name: string;
  subtotal: string;
  delivery_fee: string;
  final_total: string;
  is_free_delivery: boolean;
  free_delivery_threshold: string | null;
  amount_needed_for_free_delivery: string | null;
  currency: string;
}

export interface StripeCheckoutResponse {
  order_reference: string;
  session_id: string;
  checkout_url: string;
  total_amount: string;
  currency: string;
}

export interface OrderPaymentStatusResponse {
  order_reference: string;
  order_status: string;
  payment_status: 'PENDING' | 'PAID' | 'FAILED' | 'REFUNDED';
  total_amount: string;
  currency: string;
  stripe_checkout_session_id: string | null;
  stripe_payment_intent_id: string | null;
  is_paid: boolean;
  is_cancelled: boolean;
  confirmation_email_sent?: boolean;
  email_delivery_status?: string;
  customer_email?: string;
}

export interface StripeConfigResponse {
  publishable_key: string;
  currency: string;
  is_configured: boolean;
}

export interface CreateOrderPayload {
  address_id?: number | null;
  delivery_method_code?: string;
  recipient_name?: string;
  phone_number?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  county_region?: string;
  postal_code?: string;
  country?: string;
  guest_email?: string;
  notes?: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  password_confirm: string;
  first_name?: string;
  last_name?: string;
  phone_number?: string;
}


