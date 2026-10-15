from datetime import timedelta
from decimal import Decimal
from typing import Any
from django.db import transaction
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status, exceptions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from apps.accounts.permissions import IsAdminOrStaff
from apps.products.models import Product, ProductVariant
from apps.products.serializers import ProductDetailSerializer
from .models import Order, OrderItem
from .serializers import OrderSerializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class AdminDashboardStatsView(APIView):
    """
    GET /api/admin/dashboard/
    Staff-only endpoint returning business metrics, real database aggregations,
    financial totals (excluding unpaid, failed, and cancelled), refund details,
    sales-over-time trend, and recent orders.
    """
    permission_classes = [IsAdminOrStaff]

    def get(self, request, *args, **kwargs):
        now = timezone.now()
        thirty_days_ago = now.date() - timedelta(days=29)

        # 1. Total Orders count
        total_orders = Order.objects.count()

        # 2. Total Net Sales from successfully paid orders
        # Rule: Exclude UNPAID (PENDING), FAILED, CANCELLED, and REFUNDED orders.
        paid_orders_qs = Order.objects.filter(
            payment_status=Order.PaymentStatus.PAID
        ).exclude(order_status=Order.OrderStatus.CANCELLED)

        total_sales_agg = paid_orders_qs.aggregate(total=Sum('total_amount'))
        total_sales = total_sales_agg['total'] or Decimal('0.00')

        # 3. Refunded orders and totals
        refunded_orders_qs = Order.objects.filter(
            payment_status=Order.PaymentStatus.REFUNDED
        )
        refunded_orders_count = refunded_orders_qs.count()
        total_refunded_agg = refunded_orders_qs.aggregate(total=Sum('total_amount'))
        total_refunded_amount = total_refunded_agg['total'] or Decimal('0.00')

        # 4. Pending orders (pending payment or pending initial review)
        pending_orders = Order.objects.filter(
            Q(order_status=Order.OrderStatus.PENDING) |
            Q(payment_status=Order.PaymentStatus.PENDING)
        ).count()

        # 5. Orders awaiting fulfilment (successfully paid orders that need picking/packing/dispatch)
        awaiting_fulfilment = Order.objects.filter(
            payment_status=Order.PaymentStatus.PAID,
            order_status__in=[Order.OrderStatus.CONFIRMED, Order.OrderStatus.PROCESSING]
        ).count()

        # 6. Completed / Delivered orders
        completed_orders = Order.objects.filter(
            order_status=Order.OrderStatus.DELIVERED
        ).count()

        # 7. Cancelled orders
        cancelled_orders = Order.objects.filter(
            order_status=Order.OrderStatus.CANCELLED
        ).count()

        # 8. Inventory health statistics
        all_active_products = list(Product.objects.filter(is_active=True).prefetch_related('variants'))
        low_stock_products_count = sum(1 for p in all_active_products if p.is_low_stock)
        out_of_stock_products_count = sum(1 for p in all_active_products if not p.is_in_stock)
        total_active_products = len(all_active_products)

        # 9. Sales over time (daily data for the last 30 days)
        daily_sales_query = (
            Order.objects.filter(
                created_at__date__gte=thirty_days_ago,
                payment_status=Order.PaymentStatus.PAID
            )
            .exclude(order_status=Order.OrderStatus.CANCELLED)
            .annotate(order_date=TruncDate('created_at'))
            .values('order_date')
            .annotate(
                daily_revenue=Sum('total_amount'),
                daily_orders=Count('id')
            )
            .order_by('order_date')
        )

        daily_sales_map = {
            item['order_date'].strftime('%Y-%m-%d'): {
                'revenue': float(item['daily_revenue'] or 0),
                'orders_count': item['daily_orders'] or 0,
            }
            for item in daily_sales_query
        }

        # Build complete 30-day continuous timeline
        sales_over_time = []
        for i in range(30):
            day = thirty_days_ago + timedelta(days=i)
            day_str = day.strftime('%Y-%m-%d')
            day_data = daily_sales_map.get(day_str, {'revenue': 0.0, 'orders_count': 0})
            sales_over_time.append({
                'date': day_str,
                'label': day.strftime('%b %d'),
                'revenue': day_data['revenue'],
                'orders_count': day_data['orders_count'],
            })

        # 10. Recent Orders (top 8)
        recent_orders_qs = Order.objects.select_related('user').prefetch_related('items').order_by('-created_at')[:8]
        recent_orders = OrderSerializer(recent_orders_qs, many=True, context={'request': request}).data

        # 11. Urgent stock attention items
        urgent_stock_items = []
        for p in all_active_products:
            if not p.is_in_stock or p.is_low_stock:
                urgent_stock_items.append({
                    'id': p.id,
                    'name': p.name,
                    'slug': p.slug,
                    'sku': p.sku,
                    'total_stock': p.total_stock,
                    'low_stock_threshold': p.low_stock_threshold,
                    'is_out_of_stock': not p.is_in_stock,
                    'is_low_stock': p.is_low_stock,
                    'price': str(p.price),
                })
        urgent_stock_items = sorted(urgent_stock_items, key=lambda x: x['total_stock'])[:6]

        return Response({
            'metrics': {
                'total_orders': total_orders,
                'total_sales': str(total_sales),
                'currency': 'GBP',
                'currency_symbol': '£',
                'pending_orders': pending_orders,
                'awaiting_fulfilment': awaiting_fulfilment,
                'completed_orders': completed_orders,
                'cancelled_orders': cancelled_orders,
                'refunded_orders_count': refunded_orders_count,
                'total_refunded_amount': str(total_refunded_amount),
                'low_stock_products_count': low_stock_products_count,
                'out_of_stock_products_count': out_of_stock_products_count,
                'total_active_products': total_active_products,
            },
            'sales_calculation_rules': {
                'net_sales': 'Sum of total_amount for orders where payment_status is PAID and order_status is not CANCELLED.',
                'refund_handling': 'Orders with payment_status REFUNDED are deducted from net sales and tracked separately in total_refunded_amount.',
                'fulfilment_pending': 'Orders where payment_status is PAID and order_status is CONFIRMED or PROCESSING.',
            },
            'sales_over_time': sales_over_time,
            'recent_orders': recent_orders,
            'urgent_stock_items': urgent_stock_items,
        }, status=status.HTTP_200_OK)


class AdminOrderListView(generics.ListAPIView):
    """
    GET /api/admin/orders/
    Staff-only paginated order listing with comprehensive multi-criteria filtering:
    - Search by order reference, recipient name, customer email, phone, postal code
    - Filter by payment status (PENDING, PAID, FAILED, REFUNDED)
    - Filter by fulfilment status (PENDING, CONFIRMED, PROCESSING, SHIPPED, DELIVERED, CANCELLED)
    - Filter by date range (date_from, date_to)
    - Ordering (-created_at, created_at, -total_amount, total_amount)
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAdminOrStaff]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Order.objects.select_related('user').prefetch_related('items').all()
        request: Any = self.request

        # Search parameter
        search = (request.query_params.get('search') or '').strip()
        if search:
            queryset = queryset.filter(
                Q(order_reference__icontains=search) |
                Q(recipient_name__icontains=search) |
                Q(guest_email__icontains=search) |
                Q(user__email__icontains=search) |
                Q(phone_number__icontains=search) |
                Q(postal_code__icontains=search) |
                Q(city__icontains=search)
            )

        # Payment status filter
        payment_status = (request.query_params.get('payment_status') or '').strip().upper()
        if payment_status and payment_status in Order.PaymentStatus.values:
            queryset = queryset.filter(payment_status=payment_status)

        # Fulfilment status filter
        order_status = (
            request.query_params.get('order_status') or
            request.query_params.get('fulfilment_status') or
            ''
        ).strip().upper()
        if order_status and order_status in Order.OrderStatus.values:
            queryset = queryset.filter(order_status=order_status)

        # Date range filters
        date_from = request.query_params.get('date_from', '').strip()
        if date_from:
            try:
                queryset = queryset.filter(created_at__date__gte=date_from)
            except Exception:
                pass

        date_to = request.query_params.get('date_to', '').strip()
        if date_to:
            try:
                queryset = queryset.filter(created_at__date__lte=date_to)
            except Exception:
                pass

        # Ordering
        ordering = request.query_params.get('ordering', '-created_at').strip()
        valid_orderings = [
            '-created_at', 'created_at',
            '-total_amount', 'total_amount',
            'order_reference', '-order_reference'
        ]
        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by('-created_at')

        return queryset


class AdminOrderDetailView(generics.RetrieveAPIView):
    """
    GET /api/admin/orders/<reference>/
    Staff-only detailed order view including all snapshots, line items,
    customer details, and Stripe reference tokens.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAdminOrStaff]
    lookup_field = 'order_reference'
    lookup_url_kwarg = 'reference'

    def get_queryset(self):
        return Order.objects.select_related('user').prefetch_related('items').all()


class AdminOrderStatusUpdateView(APIView):
    """
    PATCH /api/admin/orders/<reference>/status/
    Update order fulfilment status with strict validation against an allowed
    state machine transition graph.
    
    Security & Integrity Rules:
    - Only authorized staff can transition status.
    - Payment status cannot be altered through this endpoint.
    - Transitions to terminal states (DELIVERED, CANCELLED) are strictly validated.
    - Cancelling an order restores inventory atomically.
    - Original prices, quantities, and totals remain immutable.
    """
    permission_classes = [IsAdminOrStaff]

    # Valid transitions state machine:
    # Key: Current Status -> Value: Allowed target statuses
    VALID_TRANSITIONS: dict[str, list[str]] = {
        Order.OrderStatus.PENDING: [Order.OrderStatus.CONFIRMED, Order.OrderStatus.CANCELLED],
        Order.OrderStatus.CONFIRMED: [Order.OrderStatus.PROCESSING, Order.OrderStatus.CANCELLED],
        Order.OrderStatus.PROCESSING: [Order.OrderStatus.SHIPPED, Order.OrderStatus.CANCELLED],
        Order.OrderStatus.SHIPPED: [Order.OrderStatus.DELIVERED, Order.OrderStatus.CANCELLED],
        Order.OrderStatus.DELIVERED: [],  # Terminal state
        Order.OrderStatus.CANCELLED: [],  # Terminal state
    }

    def patch(self, request, reference, *args, **kwargs):
        # 1. Guard against attempting to forge payment_status
        if 'payment_status' in request.data:
            return Response(
                {
                    'detail': 'Payment status cannot be updated manually from the dashboard. '
                              'Payment status is authoritative and derived strictly from verified payment gateway webhooks.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        order = get_object_or_404(
            Order.objects.select_related('user').prefetch_related('items'),
            order_reference=reference
        )

        current_status = order.order_status
        raw_new_status = request.data.get('order_status')
        new_status = raw_new_status.strip().upper() if raw_new_status else current_status

        if raw_new_status and new_status not in Order.OrderStatus.values:
            return Response(
                {
                    'detail': f"Invalid order status '{new_status}'. Allowed choices are: {', '.join(Order.OrderStatus.values)}."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate tracking URL if provided
        tracking_url = request.data.get('tracking_url')
        if tracking_url is not None:
            tracking_url = str(tracking_url).strip()
            if tracking_url:
                import urllib.parse
                try:
                    parsed_url = urllib.parse.urlparse(tracking_url)
                    if parsed_url.scheme.lower() not in ('http', 'https') or not parsed_url.netloc:
                        return Response(
                            {'detail': "Tracking URL must start with a valid web protocol ('http://' or 'https://') and include a valid domain."},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                except Exception:
                    return Response(
                        {'detail': "Tracking URL is invalid or malformed."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        # Check allowed status transitions if status is changing
        status_changing = (raw_new_status is not None) and (new_status != current_status)
        if status_changing:
            allowed_next_states = self.VALID_TRANSITIONS.get(current_status, [])
            if new_status not in allowed_next_states:
                if current_status in (Order.OrderStatus.DELIVERED, Order.OrderStatus.CANCELLED):
                    msg = f"Order #{order.order_reference} is already {current_status} and cannot be transitioned to any other status."
                else:
                    formatted_allowed = ', '.join(allowed_next_states) if allowed_next_states else 'None'
                    msg = (
                        f"Invalid status transition from '{current_status}' to '{new_status}'. "
                        f"Allowed next transitions from '{current_status}' are: [{formatted_allowed}]."
                    )
                return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)

            # Rule: Unpaid orders CANNOT be dispatched or delivered
            if new_status in (Order.OrderStatus.SHIPPED, Order.OrderStatus.DELIVERED) and order.payment_status != Order.PaymentStatus.PAID:
                return Response(
                    {
                        'detail': f"Cannot dispatch or complete an unpaid order. Payment status is currently '{order.get_payment_status_display()}'."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 2. Update order and courier tracking details atomically
        update_fields = ['updated_at']
        now = timezone.now()

        with transaction.atomic():
            # Inventory restoration if cancelled
            if status_changing and new_status == Order.OrderStatus.CANCELLED and current_status != Order.OrderStatus.CANCELLED:
                if order.payment_status != Order.PaymentStatus.PAID and not order.inventory_restored:
                    from .inventory_service import restore_order_inventory
                    restore_order_inventory(
                        order=order,
                        reason=f"React admin status change to CANCELLED by staff",
                        target_order_status=None
                    )

            if status_changing:
                order.order_status = new_status
                update_fields.append('order_status')

                # Set timestamps when transitioning
                if new_status == Order.OrderStatus.SHIPPED and not order.dispatched_at:
                    order.dispatched_at = now
                    update_fields.append('dispatched_at')
                elif new_status == Order.OrderStatus.DELIVERED and not order.delivered_at:
                    order.delivered_at = now
                    update_fields.append('delivered_at')

            # Optional courier tracking fields
            if 'courier_name' in request.data:
                order.courier_name = str(request.data['courier_name'] or '').strip()
                update_fields.append('courier_name')
            if 'shipment_reference' in request.data:
                order.shipment_reference = str(request.data['shipment_reference'] or '').strip()
                update_fields.append('shipment_reference')
            if 'tracking_number' in request.data:
                order.tracking_number = str(request.data['tracking_number'] or '').strip()
                update_fields.append('tracking_number')
            if 'tracking_url' in request.data:
                order.tracking_url = tracking_url or ''
                update_fields.append('tracking_url')

            order.save(update_fields=list(set(update_fields)))

        # 3. Trigger asynchronous email notification if status genuinely changed
        if status_changing and new_status in (Order.OrderStatus.SHIPPED, Order.OrderStatus.DELIVERED, Order.OrderStatus.CANCELLED):
            try:
                from .email_service import send_order_status_update_email_async
                send_order_status_update_email_async(order.id, new_status)
            except Exception:
                pass

        serializer = OrderSerializer(order, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)



class AdminProductListView(generics.ListAPIView):
    """
    GET /api/admin/products/
    Staff-only product listing including inactive items, low-stock indicators,
    and category filtering for administrative inventory management.
    """
    serializer_class = ProductDetailSerializer
    permission_classes = [IsAdminOrStaff]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Product.objects.select_related('category').prefetch_related('images', 'variants').all()
        request: Any = self.request

        # Search filter
        search = (request.query_params.get('search') or '').strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(sku__icontains=search)
            )

        # Category filter
        category_slug = (request.query_params.get('category') or '').strip()
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        # Active status filter
        is_active_param = request.query_params.get('is_active')
        if is_active_param is not None and is_active_param != '' and is_active_param.lower() != 'all':
            is_active_bool = is_active_param.lower() in ('true', '1', 'yes')
            queryset = queryset.filter(is_active=is_active_bool)

        # Stock status filter (in_stock, low_stock, out_of_stock)
        stock_status = (request.query_params.get('stock_status') or '').strip().lower()
        if stock_status == 'out_of_stock':
            queryset = queryset.filter(
                Q(has_variants=False, stock_quantity=0) |
                Q(has_variants=True)  # We will filter variant products if needed
            )
        elif stock_status == 'in_stock':
            queryset = queryset.filter(
                Q(has_variants=False, stock_quantity__gt=0) |
                Q(has_variants=True)
            )

        ordering = request.query_params.get('ordering', '-created_at').strip()
        valid_orderings = ['-created_at', 'created_at', 'name', '-name', 'price', '-price', 'stock_quantity', '-stock_quantity']
        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by('-created_at')

        return queryset


class AdminProductStockUpdateView(APIView):
    """
    POST /api/admin/products/<slug>/stock/
    Quick stock quantity update endpoint for simple products or specific variants.
    Validates non-negative stock and returns updated product data.
    """
    permission_classes = [IsAdminOrStaff]

    def post(self, request, slug, *args, **kwargs):
        product = get_object_or_404(
            Product.objects.prefetch_related('variants'),
            slug=slug
        )

        stock_quantity = request.data.get('stock_quantity')
        variant_id = request.data.get('variant_id')

        if stock_quantity is None:
            return Response(
                {'detail': "Missing required field 'stock_quantity'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            stock_qty_int = int(stock_quantity)
            if stock_qty_int < 0:
                raise ValueError()
        except (ValueError, TypeError):
            return Response(
                {'detail': 'Stock quantity must be a non-negative integer (0 or greater).'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            if variant_id:
                variant = get_object_or_404(ProductVariant, id=variant_id, product=product)
                variant.stock_quantity = stock_qty_int
                variant.save(update_fields=['stock_quantity', 'updated_at'])
            else:
                product.stock_quantity = stock_qty_int
                product.save(update_fields=['stock_quantity', 'updated_at'])

        # Return updated product detail
        product.refresh_from_db()
        serializer = ProductDetailSerializer(product, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
