import type { Order } from './api';

export interface DashboardMetrics {
  total_orders: number;
  total_sales: string;
  currency: string;
  currency_symbol: string;
  pending_orders: number;
  awaiting_fulfilment: number;
  completed_orders: number;
  cancelled_orders: number;
  refunded_orders_count: number;
  total_refunded_amount: string;
  low_stock_products_count: number;
  out_of_stock_products_count: number;
  total_active_products: number;
}

export interface SalesOverTimePoint {
  date: string;
  label: string;
  revenue: number;
  orders_count: number;
}

export interface UrgentStockItem {
  id: number;
  name: string;
  slug: string;
  sku: string;
  total_stock: number;
  low_stock_threshold: number;
  is_out_of_stock: boolean;
  is_low_stock: boolean;
  price: string;
}

export interface DashboardResponse {
  metrics: DashboardMetrics;
  sales_calculation_rules: {
    net_sales: string;
    refund_handling: string;
    fulfilment_pending: string;
  };
  sales_over_time: SalesOverTimePoint[];
  recent_orders: Order[];
  urgent_stock_items: UrgentStockItem[];
}

export interface AdminOrderFilterParams {
  search?: string;
  payment_status?: string;
  order_status?: string;
  date_from?: string;
  date_to?: string;
  ordering?: string;
  page?: number;
  page_size?: number;
}

export interface AdminProductFilterParams {
  search?: string;
  category?: string;
  stock_status?: string;
  is_active?: string;
  ordering?: string;
  page?: number;
  page_size?: number;
}

export interface ProductFormData {
  name: string;
  category_id: number | null;
  sku: string;
  price: string;
  compare_at_price: string;
  stock_quantity: number;
  low_stock_threshold: number;
  is_active: boolean;
  is_featured: boolean;
  description: string;
}
