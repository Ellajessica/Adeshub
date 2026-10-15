from typing import Any
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, permissions, exceptions
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.cart.views import get_or_create_cart, get_cart_session_key
from apps.products.models import Product, ProductVariant
from .models import Order, OrderItem, DeliveryMethod
from .serializers import OrderSerializer, CreateOrderSerializer, DeliveryMethodSerializer
from .shipping_service import (
    calculate_order_delivery_fee,
    get_delivery_quote_payload,
    get_active_delivery_methods,
    ShippingConfigurationError,
)
import stripe
from .stripe_service import (
    is_stripe_configured,
    create_stripe_checkout_session,
    verify_and_process_webhook,
)


class OrderCreateView(APIView):
    """
    POST /api/orders/ - Create an order from the current shopping cart.
    Authoritative backend pricing, stock validation, atomic transactions,
    address snapshotting, configurable delivery fee calculation, and safe cart clearing.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        cart = get_or_create_cart(request)
        cart_items = list(cart.items.all().select_related('product', 'variant'))

        if not cart_items:
            return Response(
                {'detail': 'Your shopping cart is empty.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CreateOrderSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        address_obj = validated_data.get('address_obj')

        if address_obj:
            recipient_name = address_obj.recipient_name
            phone_number = address_obj.phone_number
            address_line1 = address_obj.address_line1
            address_line2 = address_obj.address_line2
            city = address_obj.city
            county_region = address_obj.county_region
            postal_code = address_obj.postal_code
            country = address_obj.country
        else:
            recipient_name = validated_data['recipient_name']
            phone_number = validated_data['phone_number']
            address_line1 = validated_data['address_line1']
            address_line2 = validated_data.get('address_line2', '')
            city = validated_data['city']
            county_region = validated_data.get('county_region', '')
            postal_code = validated_data['postal_code']
            country = validated_data.get('country', 'United Kingdom')

        user = request.user if request.user.is_authenticated else None
        guest_email = validated_data.get('guest_email', '')
        delivery_method_code = validated_data.get('delivery_method_code', 'standard')

        try:
            with transaction.atomic():
                # 1. Authoritative price calculation and stock validation with DB row locks
                subtotal = Decimal('0.00')
                order_items_data = []

                for item in cart_items:
                    if item.variant:
                        variant = ProductVariant.objects.select_for_update().get(pk=item.variant.id)
                        if not variant.is_active or not item.product.is_active:
                            raise ValueError(f"'{item.product.name} ({variant.name})' is no longer available.")
                        if variant.stock_quantity < item.quantity:
                            raise ValueError(
                                f"Insufficient stock for '{item.product.name} ({variant.name})'. "
                                f"Available stock: {variant.stock_quantity}, requested: {item.quantity}."
                            )
                        unit_price = variant.price
                        product_name = item.product.name
                        variant_name = variant.name
                        sku = variant.sku
                        # Deduct stock
                        variant.stock_quantity -= item.quantity
                        variant.save()
                    else:
                        product = Product.objects.select_for_update().get(pk=item.product.id)
                        if not product.is_active:
                            raise ValueError(f"'{product.name}' is currently unavailable.")
                        if product.stock_quantity < item.quantity:
                            raise ValueError(
                                f"Insufficient stock for '{product.name}'. "
                                f"Available stock: {product.stock_quantity}, requested: {item.quantity}."
                            )
                        unit_price = product.price
                        product_name = product.name
                        variant_name = ''
                        sku = product.sku
                        # Deduct stock
                        product.stock_quantity -= item.quantity
                        product.save()

                    line_total = unit_price * Decimal(item.quantity)
                    subtotal += line_total

                    order_items_data.append({
                        'product': item.product,
                        'variant': item.variant,
                        'product_name': product_name,
                        'variant_name': variant_name,
                        'sku': sku,
                        'unit_price': unit_price,
                        'quantity': item.quantity,
                        'line_total': line_total,
                    })

                # Authoritative Delivery Fee calculation via configurable shipping service
                try:
                    delivery_fee, method_name = calculate_order_delivery_fee(
                        subtotal=subtotal,
                        method_code=delivery_method_code
                    )
                except ShippingConfigurationError as ship_cfg_err:
                    raise ValueError(str(ship_cfg_err))

                total_amount = subtotal + delivery_fee

                # 2. Create Order
                order = Order.objects.create(
                    user=user,
                    guest_email=guest_email,
                    recipient_name=recipient_name,
                    phone_number=phone_number,
                    address_line1=address_line1,
                    address_line2=address_line2,
                    city=city,
                    county_region=county_region,
                    postal_code=postal_code,
                    country=country,
                    subtotal=subtotal,
                    delivery_fee=delivery_fee,
                    total_amount=total_amount,
                    delivery_method_name=method_name,
                    order_status=Order.OrderStatus.CONFIRMED,
                    payment_status=Order.PaymentStatus.PENDING,
                    notes=validated_data.get('notes', '')
                )

                # 3. Create OrderItems
                for item_data in order_items_data:
                    OrderItem.objects.create(
                        order=order,
                        product=item_data['product'],
                        variant=item_data['variant'],
                        product_name=item_data['product_name'],
                        variant_name=item_data['variant_name'],
                        sku=item_data['sku'],
                        unit_price=item_data['unit_price'],
                        quantity=item_data['quantity'],
                        line_total=item_data['line_total'],
                    )

                # 4. Clear cart after successful order creation
                cart.items.all().delete()

        except ValueError as err:
            return Response({'detail': str(err)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as err:
            return Response(
                {'detail': 'An error occurred while creating your order. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        order_serializer = OrderSerializer(order, context={'request': request})
        response = Response(order_serializer.data, status=status.HTTP_201_CREATED)
        session_key = get_cart_session_key(request)

        if session_key:
            response['X-Cart-Session'] = session_key
        return response


class CustomerOrderListView(generics.ListAPIView):
    """
    GET /api/orders/my-orders/ - List order history for the authenticated customer.
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items')


class CustomerOrderDetailView(generics.RetrieveAPIView):
    """
    GET /api/orders/<reference>/ - View details of a specific order.
    Customers can access their own orders; Staff/Admin can access all orders.
    Guest orders require verification of the guest email address.
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'order_reference'
    lookup_url_kwarg = 'reference'

    def get_object(self):
        order = get_object_or_404(
            Order.objects.prefetch_related('items'),
            order_reference=self.kwargs['reference']
        )
        user = self.request.user
        is_staff = getattr(user, 'is_staff', False)
        is_superuser = getattr(user, 'is_superuser', False)

        if order.user:
            # Order belongs to a registered customer
            if not user.is_authenticated:
                raise Http404("Order not found.")
            if not (user == order.user or is_staff or is_superuser):
                raise Http404("Order not found.")
            return order

        # Guest order (order.user is None)
        if user.is_authenticated and (is_staff or is_superuser):
            return order

        request: Any = self.request
        # Session token verification (for guest returning directly from Stripe Checkout)
        session_id_param = (
            request.query_params.get('session_id') or
            self.request.headers.get('X-Stripe-Session-Id') or
            ''
        ).strip()
        if session_id_param and order.stripe_checkout_session_id and session_id_param == order.stripe_checkout_session_id:
            return order

        # Secure guest verification: check query param ?email=... or header X-Guest-Email
        email_param = (
            request.query_params.get('email') or
            self.request.headers.get('X-Guest-Email') or
            ''
        ).strip().lower()

        if email_param and order.guest_email and email_param == order.guest_email.strip().lower():
            return order

        if not email_param:
            raise exceptions.PermissionDenied(
                detail={'detail': 'Please enter the email address used when placing this order.', 'code': 'guest_email_required'}
            )

        raise exceptions.PermissionDenied(
            detail={'detail': 'The email address provided does not match this guest order.', 'code': 'invalid_guest_email'}
        )


class CreateCheckoutSessionView(APIView):
    """
    POST /api/orders/<reference>/create-checkout-session/
    Initiate Stripe Checkout session for an eligible unpaid order.
    Calculates authoritative GBP amounts and validates order ownership.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, reference, *args, **kwargs):
        order = get_object_or_404(Order, order_reference=reference)

        # 1. Ownership validation
        if order.user:
            if not request.user.is_authenticated:
                return Response(
                    {'detail': 'Authentication required to pay for this order.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            if not (request.user == order.user or request.user.is_staff or request.user.is_superuser):
                return Response(
                    {'detail': 'You do not have permission to pay for this order.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        # 2. Eligibility checks
        if order.payment_status == Order.PaymentStatus.PAID:
            return Response(
                {
                    'detail': f'Order #{order.order_reference} has already been paid.',
                    'order_reference': order.order_reference,
                    'payment_status': order.payment_status,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if order.order_status == Order.OrderStatus.CANCELLED:
            return Response(
                {
                    'detail': f'Order #{order.order_reference} is cancelled and cannot be paid.',
                    'order_reference': order.order_reference,
                    'order_status': order.order_status,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Stripe configuration check
        if not is_stripe_configured():
            return Response(
                {
                    'detail': 'Stripe payment gateway is not configured. Please set STRIPE_SECRET_KEY in the environment.',
                    'is_configured': False
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # 4. Create Checkout Session
        try:
            session = create_stripe_checkout_session(order, request=request)
            return Response({
                'order_reference': order.order_reference,
                'session_id': session.id,
                'checkout_url': session.url,
                'total_amount': str(order.total_amount),
                'currency': getattr(settings, 'STRIPE_CURRENCY', 'gbp').lower(),
            }, status=status.HTTP_200_OK)
        except ValueError as err:
            return Response({'detail': str(err)}, status=status.HTTP_400_BAD_REQUEST)
        except RuntimeError as err:
            return Response({'detail': str(err)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except stripe.error.StripeError as err:
            return Response({
                'detail': f"Stripe gateway error: {getattr(err, 'user_message', str(err))}",
                'code': getattr(err, 'code', 'stripe_error'),
            }, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as err:
            return Response({
                'detail': 'An unexpected error occurred while initiating Stripe payment.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrderPaymentStatusView(APIView):
    """
    GET /api/orders/<reference>/payment-status/
    Retrieve real-time payment status for an order.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, reference, *args, **kwargs):
        order = get_object_or_404(Order, order_reference=reference)
        session_id = request.query_params.get('session_id', '').strip()
        email_param = (
            request.query_params.get('email') or
            request.headers.get('X-Guest-Email') or
            ''
        ).strip().lower()

        is_verified_by_session = bool(
            session_id and
            order.stripe_checkout_session_id and
            session_id == order.stripe_checkout_session_id
        )
        is_email_match = bool(
            order.guest_email and
            email_param and
            email_param == order.guest_email.strip().lower()
        )

        if order.user:
            if not is_verified_by_session:
                if not request.user.is_authenticated:
                    return Response(
                        {'detail': 'Authentication required to check payment status.'},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
                if not (request.user == order.user or request.user.is_staff or request.user.is_superuser):
                    return Response(
                        {'detail': 'You do not have permission to view payment status for this order.'},
                        status=status.HTTP_403_FORBIDDEN
                    )

        is_authorized_for_pii = (
            (order.user and request.user.is_authenticated and (request.user == order.user or request.user.is_staff or request.user.is_superuser)) or
            is_verified_by_session or
            is_email_match or
            (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser))
        )

        # Direct server-to-server payment verification fallback if Stripe session completed but webhook was delayed
        if (
            is_verified_by_session and
            order.payment_status == Order.PaymentStatus.PENDING and
            session_id
        ):
            try:
                import stripe
                from .stripe_service import get_stripe_secret_key
                secret_key = get_stripe_secret_key()
                if secret_key:
                    stripe_session = stripe.checkout.Session.retrieve(session_id, api_key=secret_key)
                    if stripe_session and stripe_session.get('payment_status') == 'paid':
                        expected_currency = getattr(settings, 'STRIPE_CURRENCY', 'gbp').lower()
                        session_currency = (stripe_session.get('currency') or '').lower()
                        amount_total = stripe_session.get('amount_total')
                        expected_pence = round(order.total_amount * 100)

                        if session_currency == expected_currency and amount_total == expected_pence:
                            order.payment_status = Order.PaymentStatus.PAID
                            if stripe_session.get('payment_intent'):
                                order.stripe_payment_intent_id = str(stripe_session.get('payment_intent'))
                            cust_email = stripe_session.get('customer_details', {}).get('email') or stripe_session.get('customer_email')
                            if cust_email and not order.user and not order.guest_email:
                                order.guest_email = cust_email.strip().lower()
                            if order.order_status == Order.OrderStatus.PENDING:
                                order.order_status = Order.OrderStatus.CONFIRMED

                            order.save(update_fields=[
                                'payment_status', 'stripe_payment_intent_id',
                                'order_status', 'guest_email', 'updated_at'
                            ])

                            # Trigger confirmation email asynchronously
                            try:
                                from .email_service import send_order_confirmation_email_async
                                send_order_confirmation_email_async(order.id)
                            except Exception as email_err:
                                logger.error("Failed to trigger confirmation email for order %s: %s", order.order_reference, email_err)
            except Exception as reconcile_err:
                logger.warning("Could not reconcile Stripe session %s for order %s: %s", session_id, order.order_reference, reconcile_err)

        customer_email = (order.user.email if order.user else (order.guest_email or '')) if is_authorized_for_pii else ''

        return Response({
            'order_reference': order.order_reference,
            'order_status': order.order_status,
            'payment_status': order.payment_status,
            'total_amount': str(order.total_amount),
            'currency': getattr(settings, 'STRIPE_CURRENCY', 'gbp').lower(),
            'stripe_checkout_session_id': order.stripe_checkout_session_id if is_authorized_for_pii else None,
            'stripe_payment_intent_id': order.stripe_payment_intent_id if is_authorized_for_pii else None,
            'is_paid': order.payment_status == Order.PaymentStatus.PAID,
            'is_cancelled': order.order_status == Order.OrderStatus.CANCELLED,
            'confirmation_email_sent': order.confirmation_email_sent,
            'confirmation_email_sent_at': order.confirmation_email_sent_at,
            'email_delivery_status': order.email_delivery_status,
            'customer_email': customer_email,
        }, status=status.HTTP_200_OK)


class StripeWebhookView(APIView):
    """
    POST /api/orders/webhook/
    Webhook endpoint for receiving asynchronous events from Stripe.
    Validates webhook signature, checks amount/currency, and processes payment events idempotently.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        if not sig_header:
            return Response(
                {'detail': 'Missing Stripe-Signature header.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = verify_and_process_webhook(payload, sig_header)
            return Response(result, status=status.HTTP_200_OK)
        except stripe.error.SignatureVerificationError as err:
            return Response(
                {'detail': f'Invalid signature: {str(err)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ValueError as err:
            return Response(
                {'detail': f'Invalid payload: {str(err)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except RuntimeError as err:
            return Response(
                {'detail': str(err)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as err:
            return Response(
                {'detail': f'Error processing Stripe webhook: {str(err)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StripeConfigView(APIView):
    """
    GET /api/orders/stripe/config/
    Return safe public Stripe configuration (publishable key and currency).
    Never exposes secret keys or webhook secrets.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        pub_key = getattr(settings, 'STRIPE_PUBLISHABLE_KEY', '').strip()
        sec_key = getattr(settings, 'STRIPE_SECRET_KEY', '').strip()
        currency = getattr(settings, 'STRIPE_CURRENCY', 'gbp').lower()

        return Response({
            'publishable_key': pub_key,
            'currency': currency,
            'is_configured': bool(pub_key and sec_key),
        }, status=status.HTTP_200_OK)


class DeliveryQuoteView(APIView):
    """
    GET /api/orders/delivery-quote/
    Returns authoritative delivery quote, available methods, and financial breakdown for frontend.
    Accepts optional ?subtotal=<amount>&method=<code_slug>, or falls back to active cart.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        subtotal_param = request.query_params.get('subtotal')
        method_code = request.query_params.get('method') or 'standard'

        if subtotal_param is not None and str(subtotal_param).strip() != '':
            try:
                subtotal = Decimal(str(subtotal_param).strip())
                if subtotal < Decimal('0.00'):
                    return Response({'detail': 'Subtotal cannot be negative.'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception:
                return Response({'detail': 'Invalid subtotal query parameter.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            cart = get_or_create_cart(request)
            subtotal = Decimal(str(cart.subtotal or '0.00'))

        try:
            quote_payload = get_delivery_quote_payload(subtotal, method_code)
            return Response(quote_payload, status=status.HTTP_200_OK)
        except ShippingConfigurationError as err:
            return Response({'detail': str(err)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class DeliveryMethodListView(APIView):
    """
    GET /api/orders/delivery-methods/
    Public listing of active store delivery methods.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        methods = get_active_delivery_methods()
        serializer = DeliveryMethodSerializer(methods, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


