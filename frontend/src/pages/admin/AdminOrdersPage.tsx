import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api, ApiError } from '../../services/api';
import type { Order, PaginatedResponse } from '../../types/api';
import type { AdminOrderFilterParams } from '../../types/admin';
import { PaymentStatusBadge, FulfilmentStatusBadge } from '../../components/admin/OrderStatusBadge';
import { OrderDetailDrawer } from '../../components/admin/OrderDetailDrawer';
import {
  Search,
  X,
  ChevronLeft,
  ChevronRight,
  Eye,
  RefreshCw,
  ShoppingBag,
  AlertCircle,
  Truck
} from 'lucide-react';
import './AdminOrdersPage.css';

export const AdminOrdersPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  const [paymentStatus, setPaymentStatus] = useState(searchParams.get('payment_status') || '');
  const [orderStatus, setOrderStatus] = useState(searchParams.get('order_status') || '');
  const [dateFrom, setDateFrom] = useState(searchParams.get('date_from') || '');
  const [dateTo, setDateTo] = useState(searchParams.get('date_to') || '');
  const [ordering, setOrdering] = useState(searchParams.get('ordering') || '-created_at');
  const [currentPage, setCurrentPage] = useState(parseInt(searchParams.get('page') || '1', 10));
  const [pageSize, setPageSize] = useState(10);

  // Orders data
  const [ordersData, setOrdersData] = useState<PaginatedResponse<Order> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Drawer state for detailed view & status actions
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const fetchOrders = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params: AdminOrderFilterParams = {
        page: currentPage,
        page_size: pageSize,
        ordering,
      };
      if (searchQuery.trim()) params.search = searchQuery.trim();
      if (paymentStatus) params.payment_status = paymentStatus;
      if (orderStatus) params.order_status = orderStatus;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;

      const res = await api.getAdminOrders(params);
      setOrdersData(res);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to load orders.');
      }
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, pageSize, searchQuery, paymentStatus, orderStatus, dateFrom, dateTo, ordering]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  // Sync to URL query params
  useEffect(() => {
    const params: Record<string, string> = {};
    if (searchQuery) params.search = searchQuery;
    if (paymentStatus) params.payment_status = paymentStatus;
    if (orderStatus) params.order_status = orderStatus;
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    if (ordering !== '-created_at') params.ordering = ordering;
    if (currentPage > 1) params.page = String(currentPage);
    setSearchParams(params, { replace: true });
  }, [searchQuery, paymentStatus, orderStatus, dateFrom, dateTo, ordering, currentPage, setSearchParams]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    fetchOrders();
  };

  const handleClearFilters = () => {
    setSearchQuery('');
    setPaymentStatus('');
    setOrderStatus('');
    setDateFrom('');
    setDateTo('');
    setOrdering('-created_at');
    setCurrentPage(1);
  };

  const handleInspectOrder = (order: Order) => {
    setSelectedOrder(order);
    setIsDrawerOpen(true);
  };

  const handleOrderUpdated = (updatedOrder: Order) => {
    setSelectedOrder(updatedOrder);
    // Update the item in local list
    if (ordersData) {
      const updatedResults = ordersData.results.map((o) =>
        o.order_reference === updatedOrder.order_reference ? updatedOrder : o
      );
      setOrdersData({ ...ordersData, results: updatedResults });
    }
  };

  const hasActiveFilters = Boolean(searchQuery || paymentStatus || orderStatus || dateFrom || dateTo);
  const totalCount = ordersData?.count || 0;
  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  return (
    <div className="admin-orders-page">
      {/* Page Header */}
      <div className="orders-page-header">
        <div>
          <h1 className="orders-page-title">Order Management</h1>
          <p className="orders-page-subtitle">
            Track customer checkouts, verify payment status, and manage fulfilment workflows
          </p>
        </div>

        <div className="header-actions">
          <button
            type="button"
            className="btn-refresh-orders"
            onClick={fetchOrders}
            disabled={isLoading}
            title="Refresh order table"
          >
            <RefreshCw size={15} className={isLoading ? 'spin-icon' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="orders-filter-card">
        <form onSubmit={handleSearchSubmit} className="search-form-row">
          <div className="search-input-wrap">
            <Search size={18} className="search-icon" />
            <input
              type="text"
              placeholder="Search by Order Reference, Customer, Email, Postcode..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="orders-search-input"
            />
            {searchQuery && (
              <button
                type="button"
                className="clear-search-btn"
                onClick={() => {
                  setSearchQuery('');
                  setCurrentPage(1);
                }}
              >
                <X size={15} />
              </button>
            )}
          </div>
          <button type="submit" className="btn-search-submit">
            Search
          </button>
        </form>

        <div className="filters-grid">
          {/* Payment Status Dropdown */}
          <div className="filter-field">
            <label htmlFor="filter-payment">Payment Status</label>
            <select
              id="filter-payment"
              value={paymentStatus}
              onChange={(e) => {
                setPaymentStatus(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="">All Payment States</option>
              <option value="PAID">Paid (Verified)</option>
              <option value="PENDING">Pending Payment</option>
              <option value="REFUNDED">Refunded</option>
              <option value="FAILED">Payment Failed</option>
            </select>
          </div>

          {/* Fulfilment Status Dropdown */}
          <div className="filter-field">
            <label htmlFor="filter-fulfilment">Fulfilment Status</label>
            <select
              id="filter-fulfilment"
              value={orderStatus}
              onChange={(e) => {
                setOrderStatus(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="">All Fulfilment Stages</option>
              <option value="PENDING">Pending Review</option>
              <option value="CONFIRMED">Confirmed</option>
              <option value="PROCESSING">Processing (Pick & Pack)</option>
              <option value="SHIPPED">Dispatched / Shipped</option>
              <option value="DELIVERED">Delivered</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
          </div>

          {/* Date From */}
          <div className="filter-field">
            <label htmlFor="filter-date-from">From Date</label>
            <input
              id="filter-date-from"
              type="date"
              value={dateFrom}
              onChange={(e) => {
                setDateFrom(e.target.value);
                setCurrentPage(1);
              }}
            />
          </div>

          {/* Date To */}
          <div className="filter-field">
            <label htmlFor="filter-date-to">To Date</label>
            <input
              id="filter-date-to"
              type="date"
              value={dateTo}
              onChange={(e) => {
                setDateTo(e.target.value);
                setCurrentPage(1);
              }}
            />
          </div>

          {/* Ordering */}
          <div className="filter-field">
            <label htmlFor="filter-ordering">Sort By</label>
            <select
              id="filter-ordering"
              value={ordering}
              onChange={(e) => {
                setOrdering(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="-created_at">Newest First</option>
              <option value="created_at">Oldest First</option>
              <option value="-total_amount">Amount: High to Low</option>
              <option value="total_amount">Amount: Low to High</option>
            </select>
          </div>
        </div>

        {hasActiveFilters && (
          <div className="active-filters-ribbon">
            <span className="filters-hint">Active Filters Applied</span>
            <button type="button" className="btn-clear-all" onClick={handleClearFilters}>
              <X size={14} /> Reset All Filters
            </button>
          </div>
        )}
      </div>

      {/* Orders Table Container */}
      <div className="orders-table-card">
        {error && (
          <div className="table-alert-error">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <div className="orders-table-scroll-wrapper">
          <table className="orders-main-table">
            <thead>
              <tr>
                <th>Order Ref</th>
                <th>Date Placed</th>
                <th>Customer & Address</th>
                <th className="text-center">Items</th>
                <th className="text-right">Total (£)</th>
                <th>Payment</th>
                <th>Fulfilment</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="table-loading-row">
                    <div className="admin-spinner" />
                    <span>Loading orders from database...</span>
                  </td>
                </tr>
              ) : !ordersData || ordersData.results.length === 0 ? (
                <tr>
                  <td colSpan={8} className="table-empty-row">
                    <ShoppingBag size={32} className="text-muted" />
                    <p>No orders matched your search and filter criteria.</p>
                    {hasActiveFilters && (
                      <button type="button" className="btn-reset-empty" onClick={handleClearFilters}>
                        Clear Filters
                      </button>
                    )}
                  </td>
                </tr>
              ) : (
                ordersData.results.map((order) => (
                  <tr key={order.id} className="order-row">
                    <td className="ref-cell font-bold">
                      <button
                        type="button"
                        className="order-ref-link"
                        onClick={() => handleInspectOrder(order)}
                      >
                        #{order.order_reference}
                      </button>
                    </td>

                    <td className="date-cell">
                      <span>
                        {new Date(order.created_at).toLocaleDateString('en-GB', {
                          day: '2-digit',
                          month: 'short',
                          year: 'numeric',
                        })}
                      </span>
                      <span className="time-sub">
                        {new Date(order.created_at).toLocaleTimeString('en-GB', {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </td>

                    <td className="customer-info-cell">
                      <span className="customer-name font-bold">
                        {order.customer_name || order.recipient_name}
                      </span>
                      <span className="customer-sub-text">
                        {order.customer_email || order.city}
                      </span>
                    </td>

                    <td className="text-center font-bold items-count-cell">
                      {order.items.reduce((acc, it) => acc + it.quantity, 0)}
                    </td>

                    <td className="text-right total-cell font-bold">
                      £{parseFloat(order.total_amount).toFixed(2)}
                    </td>

                    <td>
                      <PaymentStatusBadge status={order.payment_status} size="sm" />
                    </td>

                    <td>
                      <FulfilmentStatusBadge status={order.order_status} size="sm" />
                      {order.courier_name && (
                        <div
                          className="table-courier-tag"
                          title={`Courier: ${order.courier_name}${order.tracking_number ? ` (Tracking: ${order.tracking_number})` : ''}`}
                        >
                          <Truck size={11} />
                          <span>{order.courier_name}</span>
                        </div>
                      )}
                    </td>

                    <td className="text-right actions-cell">
                      <button
                        type="button"
                        className="btn-view-order-details"
                        onClick={() => handleInspectOrder(order)}
                        title="View order details and manage status"
                      >
                        <Eye size={14} /> View
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Toolbar */}
        {!isLoading && totalCount > 0 && (
          <div className="orders-pagination-bar">
            <div className="pagination-info">
              Showing{' '}
              <strong>{(currentPage - 1) * pageSize + 1}</strong> to{' '}
              <strong>{Math.min(currentPage * pageSize, totalCount)}</strong> of{' '}
              <strong>{totalCount}</strong> orders
            </div>

            <div className="pagination-controls">
              <div className="page-size-select-wrap">
                <span>Show:</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(parseInt(e.target.value, 10));
                    setCurrentPage(1);
                  }}
                >
                  <option value="10">10</option>
                  <option value="25">25</option>
                  <option value="50">50</option>
                </select>
              </div>

              <div className="page-navigation-buttons">
                <button
                  type="button"
                  className="page-nav-btn"
                  disabled={currentPage <= 1}
                  onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                  aria-label="Previous Page"
                >
                  <ChevronLeft size={16} />
                </button>

                <span className="current-page-indicator">
                  Page {currentPage} of {totalPages}
                </span>

                <button
                  type="button"
                  className="page-nav-btn"
                  disabled={currentPage >= totalPages}
                  onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                  aria-label="Next Page"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Slide-over Detailed Order View & Transition Panel */}
      <OrderDetailDrawer
        order={selectedOrder}
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        onOrderUpdated={handleOrderUpdated}
      />
    </div>
  );
};
