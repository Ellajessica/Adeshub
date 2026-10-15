import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError } from '../../services/api';
import type { DashboardResponse } from '../../types/admin';
import type { Order } from '../../types/api';
import { SalesChart } from '../../components/admin/SalesChart';
import { PaymentStatusBadge, FulfilmentStatusBadge } from '../../components/admin/OrderStatusBadge';
import { OrderDetailDrawer } from '../../components/admin/OrderDetailDrawer';
import {
  PoundSterling,
  ShoppingBag,
  Clock,
  PackageCheck,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  RefreshCw,
  Eye,
  AlertCircle,
  Truck
} from 'lucide-react';
import './AdminDashboardPage.css';

export const AdminDashboardPage: React.FC = () => {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Drawer state for inspecting recent orders
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const loadDashboard = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.getAdminDashboard();
      setData(res);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to load administrative dashboard statistics.');
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const handleInspectOrder = (order: Order) => {
    setSelectedOrder(order);
    setIsDrawerOpen(true);
  };

  const handleOrderUpdated = (updatedOrder: Order) => {
    setSelectedOrder(updatedOrder);
    // Reload dashboard metrics to reflect status update
    loadDashboard();
  };

  if (isLoading) {
    return (
      <div className="dashboard-loading-state">
        <div className="admin-spinner" />
        <p>Retrieving store metrics & real transaction statistics...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="dashboard-error-state">
        <AlertCircle size={40} className="text-error" />
        <h3>Failed to Load Dashboard</h3>
        <p>{error || 'An unexpected error occurred while fetching data.'}</p>
        <button type="button" className="btn-retry" onClick={loadDashboard}>
          <RefreshCw size={16} /> Try Again
        </button>
      </div>
    );
  }

  const { metrics, sales_over_time, recent_orders, urgent_stock_items } = data;

  return (
    <div className="admin-dashboard-view">
      {/* Page Title & Controls */}
      <div className="dashboard-topbar">
        <div>
          <h1 className="dashboard-page-title">Business Overview</h1>
          <p className="dashboard-page-subtitle">
            Real-time financial performance, order pipeline, and inventory status
          </p>
        </div>
        <div className="dashboard-topbar-actions">
          <button type="button" className="btn-refresh-stats" onClick={loadDashboard} title="Refresh data">
            <RefreshCw size={15} />
            <span>Refresh Stats</span>
          </button>
        </div>
      </div>

      {/* KPI Summary Cards Grid */}
      <div className="kpi-cards-grid">
        {/* Total Sales (Net Revenue) */}
        <div className="kpi-card highlight-revenue">
          <div className="kpi-card-header">
            <span className="kpi-label">Total Net Sales</span>
            <div className="kpi-icon-wrap icon-primary">
              <PoundSterling size={20} />
            </div>
          </div>
          <div className="kpi-main-metric">
            £{parseFloat(metrics.total_sales).toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="kpi-footer-note">
            <span>Successfully verified paid orders</span>
          </div>
        </div>

        {/* Orders Awaiting Fulfilment */}
        <div className={`kpi-card ${metrics.awaiting_fulfilment > 0 ? 'highlight-warning' : ''}`}>
          <div className="kpi-card-header">
            <span className="kpi-label">Awaiting Fulfilment</span>
            <div className="kpi-icon-wrap icon-warning">
              <Truck size={20} />
            </div>
          </div>
          <div className="kpi-main-metric">{metrics.awaiting_fulfilment}</div>
          <div className="kpi-footer-note">
            <Link to="/admin/orders?order_status=CONFIRMED" className="kpi-link">
              <span>Paid & ready to dispatch</span>
              <ArrowRight size={13} />
            </Link>
          </div>
        </div>

        {/* Total Orders Placed */}
        <div className="kpi-card">
          <div className="kpi-card-header">
            <span className="kpi-label">Total Orders</span>
            <div className="kpi-icon-wrap icon-indigo">
              <ShoppingBag size={20} />
            </div>
          </div>
          <div className="kpi-main-metric">{metrics.total_orders}</div>
          <div className="kpi-footer-note">
            <span>Lifetime orders in database</span>
          </div>
        </div>

        {/* Completed / Delivered */}
        <div className="kpi-card">
          <div className="kpi-card-header">
            <span className="kpi-label">Completed Deliveries</span>
            <div className="kpi-icon-wrap icon-emerald">
              <PackageCheck size={20} />
            </div>
          </div>
          <div className="kpi-main-metric">{metrics.completed_orders}</div>
          <div className="kpi-footer-note">
            <span>Successfully delivered to customers</span>
          </div>
        </div>

        {/* Pending Orders */}
        <div className="kpi-card">
          <div className="kpi-card-header">
            <span className="kpi-label">Pending / Unpaid</span>
            <div className="kpi-icon-wrap icon-amber">
              <Clock size={20} />
            </div>
          </div>
          <div className="kpi-main-metric">{metrics.pending_orders}</div>
          <div className="kpi-footer-note">
            <span>Awaiting customer checkout</span>
          </div>
        </div>

        {/* Low Stock Alerts */}
        <div className={`kpi-card ${metrics.low_stock_products_count > 0 ? 'highlight-alert' : ''}`}>
          <div className="kpi-card-header">
            <span className="kpi-label">Low Stock Alerts</span>
            <div className="kpi-icon-wrap icon-rose">
              <AlertTriangle size={20} />
            </div>
          </div>
          <div className="kpi-main-metric">{metrics.low_stock_products_count}</div>
          <div className="kpi-footer-note">
            <Link to="/admin/products?stock_status=low_stock" className="kpi-link">
              <span>Items at or below threshold</span>
              <ArrowRight size={13} />
            </Link>
          </div>
        </div>
      </div>

      {/* Main Section: Sales Over Time Interactive Chart */}
      <div className="dashboard-chart-section">
        <SalesChart data={sales_over_time} currencySymbol="£" />
      </div>

      {/* Bottom Grid: Recent Orders & Urgent Inventory */}
      <div className="dashboard-bottom-grid">
        {/* Recent Orders Table */}
        <div className="dashboard-panel recent-orders-panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Recent Orders</h3>
              <p className="panel-subtitle">Latest customer purchases across the storefront</p>
            </div>
            <Link to="/admin/orders" className="panel-view-all-link">
              View All Orders <ArrowRight size={14} />
            </Link>
          </div>

          <div className="recent-orders-table-wrapper">
            <table className="recent-orders-table">
              <thead>
                <tr>
                  <th>Order Ref</th>
                  <th>Customer</th>
                  <th>Total (£)</th>
                  <th>Payment</th>
                  <th>Fulfilment</th>
                  <th className="text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {recent_orders.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="empty-table-cell">
                      No recent orders recorded in the system yet.
                    </td>
                  </tr>
                ) : (
                  recent_orders.map((order) => (
                    <tr key={order.id}>
                      <td className="order-ref-cell">
                        <button
                          type="button"
                          className="ref-link-btn"
                          onClick={() => handleInspectOrder(order)}
                        >
                          #{order.order_reference}
                        </button>
                      </td>
                      <td>
                        <div className="customer-cell">
                          <span className="customer-name">{order.customer_name || order.recipient_name}</span>
                          <span className="customer-email">{order.customer_email || 'Guest'}</span>
                        </div>
                      </td>
                      <td className="amount-cell font-bold">
                        £{parseFloat(order.total_amount).toFixed(2)}
                      </td>
                      <td>
                        <PaymentStatusBadge status={order.payment_status} size="sm" />
                      </td>
                      <td>
                        <FulfilmentStatusBadge status={order.order_status} size="sm" />
                      </td>
                      <td className="text-right">
                        <button
                          type="button"
                          className="btn-quick-inspect"
                          onClick={() => handleInspectOrder(order)}
                          title="Inspect Order Details & Fulfilment"
                        >
                          <Eye size={14} /> Inspect
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Urgent Stock Attention Panel */}
        <div className="dashboard-panel stock-attention-panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Inventory Alerts</h3>
              <p className="panel-subtitle">Items requiring replenishment</p>
            </div>
            <Link to="/admin/products" className="panel-view-all-link">
              Inventory <ArrowRight size={14} />
            </Link>
          </div>

          <div className="stock-alerts-list">
            {urgent_stock_items.length === 0 ? (
              <div className="empty-stock-alerts">
                <CheckCircle2 size={32} className="text-success" />
                <p>All catalog products are healthy and above stock thresholds.</p>
              </div>
            ) : (
              urgent_stock_items.map((item) => (
                <div key={item.id} className="stock-alert-item">
                  <div className="stock-item-info">
                    <span className="stock-item-name">{item.name}</span>
                    <span className="stock-item-sku">{item.sku}</span>
                  </div>
                  <div className="stock-item-stat">
                    <span className={`stock-count-badge ${item.is_out_of_stock ? 'out-of-stock' : 'low-stock'}`}>
                      {item.is_out_of_stock ? 'Out of Stock (0)' : `${item.total_stock} left (Thresh: ${item.low_stock_threshold})`}
                    </span>
                    <Link
                      to={`/admin/products?search=${encodeURIComponent(item.sku)}`}
                      className="stock-restock-link"
                    >
                      Restock
                    </Link>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Slide-over Order Detail Drawer */}
      <OrderDetailDrawer
        order={selectedOrder}
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        onOrderUpdated={handleOrderUpdated}
      />
    </div>
  );
};
