from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from apps.accounts.models import User
from apps.products.models import Product, ProductVariant, Category
from apps.orders.models import Order, OrderItem


class AdminDashboardAndOrdersTests(APITestCase):
    client: APIClient

    def setUp(self):
        Order.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        User.objects.all().delete()

        self.client = APIClient()

        # Users
        self.admin_user = User.objects.create_superuser(
            email="admin@adeshub.com",
            password="AdminPassword123!",
            first_name="Admin",
            last_name="Manager"
        )
        self.admin_token, _ = Token.objects.get_or_create(user=self.admin_user)

        self.customer_user = User.objects.create_user(
            email="customer@example.com",
            password="CustomerPassword123!",
            first_name="John",
            last_name="Customer"
        )
        self.customer_token, _ = Token.objects.get_or_create(user=self.customer_user)

        self.other_customer = User.objects.create_user(
            email="other@example.com",
            password="OtherPassword123!",
            first_name="Other",
            last_name="Customer"
        )
        self.other_token, _ = Token.objects.get_or_create(user=self.other_customer)

        # Products
        self.category = Category.objects.create(name="Staples", slug="staples")

        self.product1 = Product.objects.create(
            name="Yam Tubers",
            slug="yam-tubers",
            sku="YAM-100",
            price=Decimal("12.50"),
            stock_quantity=15,
            low_stock_threshold=5,
            has_variants=False,
            is_active=True,
            category=self.category
        )

        self.product_low = Product.objects.create(
            name="Plantain Flour",
            slug="plantain-flour",
            sku="PLN-200",
            price=Decimal("5.00"),
            stock_quantity=3,
            low_stock_threshold=5,
            has_variants=False,
            is_active=True,
            category=self.category
        )

        self.product_variant = Product.objects.create(
            name="Palm Oil",
            slug="palm-oil",
            sku="OIL-300",
            price=Decimal("8.00"),
            stock_quantity=0,
            low_stock_threshold=4,
            has_variants=True,
            is_active=True,
            category=self.category
        )
        self.variant1 = ProductVariant.objects.create(
            product=self.product_variant,
            name="1 Litre",
            sku="OIL-300-1L",
            price=Decimal("8.00"),
            stock_quantity=8,
            is_active=True
        )

        # Orders:
        # Order 1: PAID, CONFIRMED (Awaiting fulfilment)
        self.order1 = Order.objects.create(
            order_reference="ADH-20261013-0001",
            user=self.customer_user,
            recipient_name="John Customer",
            phone_number="07111222333",
            address_line1="12 High Street",
            city="London",
            postal_code="E1 6AN",
            subtotal=Decimal("25.00"),
            delivery_fee=Decimal("3.99"),
            total_amount=Decimal("28.99"),
            order_status=Order.OrderStatus.CONFIRMED,
            payment_status=Order.PaymentStatus.PAID,
            stripe_checkout_session_id="cs_test_0001",
            stripe_payment_intent_id="pi_test_0001"
        )
        OrderItem.objects.create(
            order=self.order1,
            product=self.product1,
            product_name=self.product1.name,
            sku=self.product1.sku,
            unit_price=Decimal("12.50"),
            quantity=2,
            line_total=Decimal("25.00")
        )

        # Order 2: PAID, DELIVERED (Completed)
        self.order2 = Order.objects.create(
            order_reference="ADH-20261013-0002",
            user=self.customer_user,
            recipient_name="John Customer",
            phone_number="07111222333",
            address_line1="12 High Street",
            city="London",
            postal_code="E1 6AN",
            subtotal=Decimal("50.00"),
            delivery_fee=Decimal("0.00"),
            total_amount=Decimal("50.00"),
            order_status=Order.OrderStatus.DELIVERED,
            payment_status=Order.PaymentStatus.PAID,
            stripe_checkout_session_id="cs_test_0002",
            stripe_payment_intent_id="pi_test_0002"
        )

        # Order 3: PENDING, CONFIRMED (Unpaid / pending payment)
        self.order3 = Order.objects.create(
            order_reference="ADH-20261013-0003",
            guest_email="guest@example.com",
            recipient_name="Guest Buyer",
            phone_number="07222333444",
            address_line1="45 Market Road",
            city="Manchester",
            postal_code="M1 1AA",
            subtotal=Decimal("15.00"),
            delivery_fee=Decimal("3.99"),
            total_amount=Decimal("18.99"),
            order_status=Order.OrderStatus.CONFIRMED,
            payment_status=Order.PaymentStatus.PENDING
        )

        # Order 4: CANCELLED (Unpaid or cancelled)
        self.order4 = Order.objects.create(
            order_reference="ADH-20261013-0004",
            user=self.customer_user,
            recipient_name="John Customer",
            phone_number="07111222333",
            address_line1="12 High Street",
            city="London",
            postal_code="E1 6AN",
            subtotal=Decimal("10.00"),
            delivery_fee=Decimal("3.99"),
            total_amount=Decimal("13.99"),
            order_status=Order.OrderStatus.CANCELLED,
            payment_status=Order.PaymentStatus.FAILED
        )

        # Order 5: REFUNDED
        self.order5 = Order.objects.create(
            order_reference="ADH-20261013-0005",
            user=self.other_customer,
            recipient_name="Other Customer",
            phone_number="07333444555",
            address_line1="88 Kings Road",
            city="Birmingham",
            postal_code="B1 1BB",
            subtotal=Decimal("30.00"),
            delivery_fee=Decimal("3.99"),
            total_amount=Decimal("33.99"),
            order_status=Order.OrderStatus.CONFIRMED,
            payment_status=Order.PaymentStatus.REFUNDED
        )

    # -------------------------------------------------------------
    # 1. PERMISSION TESTS
    # -------------------------------------------------------------
    def test_unauthenticated_cannot_access_admin_dashboard(self):
        url = "/api/admin/dashboard/"
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_customer_cannot_access_admin_dashboard(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.customer_token.key}")
        url = "/api/admin/dashboard/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_access_admin_dashboard(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        url = "/api/admin/dashboard/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_customer_cannot_access_admin_orders(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.customer_token.key}")
        url = "/api/admin/orders/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_cannot_view_other_customers_order_detail(self):
        # Customer 2 trying to view Customer 1's order via storefront detail
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.other_token.key}")
        url = f"/api/orders/{self.order1.order_reference}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -------------------------------------------------------------
    # 2. DASHBOARD STATISTICS TESTS
    # -------------------------------------------------------------
    def test_dashboard_metrics_calculation(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        url = "/api/admin/dashboard/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        metrics = response.data['metrics']

        # Total orders = 5
        self.assertEqual(metrics['total_orders'], 5)

        # Total Sales from PAID orders only (order1: 28.99 + order2: 50.00 = 78.99)
        # Excludes pending (order3: 18.99), cancelled (order4: 13.99), refunded (order5: 33.99)
        self.assertEqual(Decimal(metrics['total_sales']), Decimal("78.99"))

        # Refunded amount tracked
        self.assertEqual(Decimal(metrics['total_refunded_amount']), Decimal("33.99"))
        self.assertEqual(metrics['refunded_orders_count'], 1)

        # Orders awaiting fulfilment (PAID and CONFIRMED or PROCESSING): order1
        self.assertEqual(metrics['awaiting_fulfilment'], 1)

        # Completed orders: order2 (DELIVERED)
        self.assertEqual(metrics['completed_orders'], 1)

        # Cancelled orders: order4
        self.assertEqual(metrics['cancelled_orders'], 1)

        # Low stock products count: product_low (stock=3, threshold=5)
        self.assertGreaterEqual(metrics['low_stock_products_count'], 1)

        # Sales over time array has 30 items
        self.assertEqual(len(response.data['sales_over_time']), 30)

    # -------------------------------------------------------------
    # 3. ORDER LISTING AND FILTERING TESTS
    # -------------------------------------------------------------
    def test_admin_orders_list_and_search(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")

        # List all
        res = self.client.get("/api/admin/orders/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 5)

        # Search by order reference
        res = self.client.get("/api/admin/orders/?search=0001")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 1)
        self.assertEqual(res.data['results'][0]['order_reference'], "ADH-20261013-0001")

        # Search by guest email
        res = self.client.get("/api/admin/orders/?search=guest@example.com")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 1)

        # Filter by payment status
        res = self.client.get("/api/admin/orders/?payment_status=PAID")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 2)

        res = self.client.get("/api/admin/orders/?payment_status=REFUNDED")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 1)

        # Filter by fulfilment status
        res = self.client.get("/api/admin/orders/?order_status=DELIVERED")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 1)

        # Filter by date
        today_str = timezone.now().strftime('%Y-%m-%d')
        res = self.client.get(f"/api/admin/orders/?date_from={today_str}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 5)

    def test_admin_order_detail_view(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        url = f"/api/admin/orders/{self.order1.order_reference}/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['order_reference'], self.order1.order_reference)
        self.assertEqual(res.data['stripe_checkout_session_id'], "cs_test_0001")
        self.assertEqual(len(res.data['items']), 1)
        self.assertEqual(res.data['items'][0]['product_name'], "Yam Tubers")

    # -------------------------------------------------------------
    # 4. FULFILMENT STATUS TRANSITIONS AND INVENTORY RESTORATION
    # -------------------------------------------------------------
    def test_valid_status_transition_confirmed_to_processing(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        url = f"/api/admin/orders/{self.order1.order_reference}/status/"
        res = self.client.patch(url, {'order_status': 'PROCESSING'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.order1.refresh_from_db()
        self.assertEqual(self.order1.order_status, Order.OrderStatus.PROCESSING)

    def test_valid_status_transition_processing_to_shipped_then_delivered(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        url = f"/api/admin/orders/{self.order1.order_reference}/status/"

        # CONFIRMED -> PROCESSING
        self.client.patch(url, {'order_status': 'PROCESSING'})

        # PROCESSING -> SHIPPED
        res = self.client.patch(url, {'order_status': 'SHIPPED'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.order1.refresh_from_db()
        self.assertEqual(self.order1.order_status, Order.OrderStatus.SHIPPED)

        # SHIPPED -> DELIVERED
        res = self.client.patch(url, {'order_status': 'DELIVERED'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.order1.refresh_from_db()
        self.assertEqual(self.order1.order_status, Order.OrderStatus.DELIVERED)

    def test_invalid_status_transition_delivered_to_pending_fails(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        url = f"/api/admin/orders/{self.order2.order_reference}/status/"  # order2 is DELIVERED
        res = self.client.patch(url, {'order_status': 'PENDING'})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cannot be transitioned", res.data['detail'])

    def test_invalid_status_transition_cancelled_to_processing_fails(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        url = f"/api/admin/orders/{self.order4.order_reference}/status/"  # order4 is CANCELLED
        res = self.client.patch(url, {'order_status': 'PROCESSING'})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cannot be transitioned", res.data['detail'])

    def test_cancelling_order_restores_item_inventory(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        # Per Phase 10 Rule 10/12: Unpaid orders restore inventory upon admin cancellation
        self.order1.payment_status = Order.PaymentStatus.PENDING
        self.order1.save(update_fields=['payment_status'])
        initial_stock = self.product1.stock_quantity  # 15
        # order1 contains 2 units of product1
        url = f"/api/admin/orders/{self.order1.order_reference}/status/"
        res = self.client.patch(url, {'order_status': 'CANCELLED'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock_quantity, initial_stock + 2)

    # -------------------------------------------------------------
    # 5. PAYMENT STATUS INTEGRITY
    # -------------------------------------------------------------
    def test_payment_status_cannot_be_modified_via_dashboard(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        url = f"/api/admin/orders/{self.order3.order_reference}/status/"  # order3 is PENDING payment
        res = self.client.patch(url, {
            'order_status': 'CONFIRMED',
            'payment_status': 'PAID'
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Payment status cannot be updated manually", res.data['detail'])

        # Ensure payment status remained PENDING
        self.order3.refresh_from_db()
        self.assertEqual(self.order3.payment_status, Order.PaymentStatus.PENDING)

    # -------------------------------------------------------------
    # 6. PRODUCT MANAGEMENT AND STOCK CONTROLS
    # -------------------------------------------------------------
    def test_admin_quick_stock_update(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        url = f"/api/admin/products/{self.product1.slug}/stock/"
        res = self.client.post(url, {'stock_quantity': 50})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock_quantity, 50)

    def test_admin_quick_stock_update_rejects_negative(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        url = f"/api/admin/products/{self.product1.slug}/stock/"
        res = self.client.post(url, {'stock_quantity': -10})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_product_variant_detail_crud(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        url = f"/api/products/{self.product_variant.slug}/variants/{self.variant1.id}/"

        # GET
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['name'], "1 Litre")

        # PATCH
        res = self.client.patch(url, {'price': '9.50', 'stock_quantity': 20})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.variant1.refresh_from_db()
        self.assertEqual(self.variant1.price, Decimal("9.50"))
        self.assertEqual(self.variant1.stock_quantity, 20)

        # DELETE
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ProductVariant.objects.filter(pk=self.variant1.id).exists())
