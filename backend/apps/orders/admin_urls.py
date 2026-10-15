from django.urls import path
from .admin_views import (
    AdminDashboardStatsView,
    AdminOrderListView,
    AdminOrderDetailView,
    AdminOrderStatusUpdateView,
    AdminProductListView,
    AdminProductStockUpdateView,
)

app_name = 'admin-api'

urlpatterns = [
    path('dashboard/', AdminDashboardStatsView.as_view(), name='admin-dashboard'),
    path('orders/', AdminOrderListView.as_view(), name='admin-order-list'),
    path('orders/<str:reference>/', AdminOrderDetailView.as_view(), name='admin-order-detail'),
    path('orders/<str:reference>/status/', AdminOrderStatusUpdateView.as_view(), name='admin-order-status-update'),
    path('products/', AdminProductListView.as_view(), name='admin-product-list'),
    path('products/<slug:slug>/stock/', AdminProductStockUpdateView.as_view(), name='admin-product-stock-update'),
]
