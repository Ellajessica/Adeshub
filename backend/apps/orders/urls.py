from django.urls import path
from .views import (
    OrderCreateView,
    CustomerOrderListView,
    CustomerOrderDetailView,
    CreateCheckoutSessionView,
    OrderPaymentStatusView,
    StripeWebhookView,
    StripeConfigView,
    DeliveryQuoteView,
    DeliveryMethodListView,
)

app_name = 'orders'

urlpatterns = [
    path('', OrderCreateView.as_view(), name='order-create'),
    path('delivery-quote/', DeliveryQuoteView.as_view(), name='delivery-quote'),
    path('delivery-methods/', DeliveryMethodListView.as_view(), name='delivery-methods'),
    path('my-orders/', CustomerOrderListView.as_view(), name='customer-order-list'),
    path('webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('stripe/config/', StripeConfigView.as_view(), name='stripe-config'),
    path('<str:reference>/create-checkout-session/', CreateCheckoutSessionView.as_view(), name='order-create-checkout-session'),
    path('<str:reference>/payment-status/', OrderPaymentStatusView.as_view(), name='order-payment-status'),
    path('<str:reference>/', CustomerOrderDetailView.as_view(), name='order-detail'),
]

