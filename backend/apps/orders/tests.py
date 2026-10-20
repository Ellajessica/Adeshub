from decimal import Decimal
from unittest.mock import patch, MagicMock
import stripe
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase
from rest_framework import status

from apps.accounts.models import User
from apps.products.models import Product, ProductVariant, Category
from apps.cart.models import Cart, CartItem
from apps.accounts.models import Address
from .models import Order, OrderItem


class OrdersBackendTestCase(APITestCase):
    client: APIClient

    def setUp(self):
        Order.objects.all().delete()
        Cart.objects.all().delete()
        self.client = APIClient()

        # Category
        self.category = Category.objects.create(name="Groceries", slug="groceries")

        # Simple Product
        self.simple_product = Product.objects.create(
            name="Fresh Pona Yam",
            slug="fresh-pona-yam",
            sku="YAM-001",
            price=Decimal("6.50"),
            stock_quantity=10,
            has_variants=False,
            is_active=True,
            category=self.category
        )

        # Product with Variants
        self.variant_product = Product.objects.create(
            name="Red Palm Oil",
            slug="red-palm-oil",
            sku="OIL-001",
            price=Decimal("4.50"),
            stock_quantity=0,
            has_variants=True,
            is_active=True,
            category=self.category
        )

        self.variant_2l = ProductVariant.objects.create(
            product=self.variant_product,
            name="2L Bottle",
            sku="OIL-001-2L",
            price=Decimal("8.50"),
            stock_quantity=5,
            is_active=True
        )

        # Customer User
        self.user = User.objects.create_user(
            email="customer@example.com",
            password="Password123!",
            first_name="Jane",
            last_name="Doe",
            phone_number="07123456789"
        )

        # Saved Address
        self.address = Address.objects.create(
            user=self.user,
            recipient_name="Jane Doe",
            phone_number="07123456789",
            address_line1="10 High Street",
            city="London",
            postal_code="SW1A 1AA",
            country="United Kingdom",
            is_default=True
        )

    def test_create_order_authenticated_with_saved_address(self):
        """
        Test successful order creation for authenticated user using saved address.
        Verify:
        - Authoritative prices
        - Stock deduction (10 -> 8 for Yam, 5 -> 4 for 2L Palm Oil)
        - Cart clearing
        - Historical snapshotting
        """
        self.client.force_authenticate(user=self.user)

        # 1. Add simple product (qty 2) and variant product (qty 1) to cart
        self.client.post('/api/cart/items/', {'product': self.simple_product.id, 'quantity': 2})
        self.client.post('/api/cart/items/', {
            'product': self.variant_product.id,
            'variant': self.variant_2l.id,
            'quantity': 1
        })

        # Verify cart has items before order
        cart_res = self.client.get('/api/cart/')
        self.assertEqual(len(cart_res.data['items']), 2)

        # 2. Create order using saved address
        order_res = self.client.post('/api/orders/', {'address_id': self.address.id})
        self.assertEqual(order_res.status_code, status.HTTP_201_CREATED)
        self.assertIn('order_reference', order_res.data)

        order_ref = order_res.data['order_reference']
        order = Order.objects.get(order_reference=order_ref)

        # Expected subtotal: (6.50 * 2) + (8.50 * 1) = 13.00 + 8.50 = 21.50
        self.assertEqual(order.subtotal, Decimal("21.50"))
        # Standard delivery fee £3.99 for orders under £50
        self.assertEqual(order.delivery_fee, Decimal("3.99"))
        self.assertEqual(order.total_amount, Decimal("25.49"))
        self.assertEqual(order.order_status, Order.OrderStatus.CONFIRMED)
        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)

        # Verify stock deduction
        self.simple_product.refresh_from_db()
        self.variant_2l.refresh_from_db()
        self.assertEqual(self.simple_product.stock_quantity, 8)
        self.assertEqual(self.variant_2l.stock_quantity, 4)

        # Verify cart is cleared after order creation
        cart_res_after = self.client.get('/api/cart/')
        self.assertEqual(len(cart_res_after.data['items']), 0)

    def test_insufficient_stock_preserves_cart_and_fails_order(self):
        """
        Test that ordering quantity > stock fails gracefully, rolls back, and preserves cart.
        """
        self.client.force_authenticate(user=self.user)

        # Add 3 units of variant (stock is 5)
        self.client.post('/api/cart/items/', {
            'product': self.variant_product.id,
            'variant': self.variant_2l.id,
            'quantity': 3
        })

        # Reduce stock concurrently to 2
        self.variant_2l.stock_quantity = 2
        self.variant_2l.save()

        # Try to place order
        order_res = self.client.post('/api/orders/', {'address_id': self.address.id})
        self.assertEqual(order_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Insufficient stock', order_res.data['detail'])

        # Verify cart was NOT cleared
        cart_res = self.client.get('/api/cart/')
        self.assertEqual(len(cart_res.data['items']), 1)

    def test_customer_order_history_permissions(self):
        """
        Test that customers can only view their own order history and order details.
        """
        user_1 = User.objects.create_user(email="perm_user1@example.com", password="Password123!")
        addr_1 = Address.objects.create(
            user=user_1,
            recipient_name="User One",
            phone_number="07111111111",
            address_line1="1 First Street",
            city="London",
            postal_code="E1 1AA"
        )

        # Create order for user 1
        self.client.force_authenticate(user=user_1)
        self.client.post('/api/cart/items/', {'product': self.simple_product.id, 'quantity': 1})
        res = self.client.post('/api/orders/', {'address_id': addr_1.id})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        order_ref = res.data['order_reference']

        # User 1 views order history
        history_res = self.client.get('/api/orders/my-orders/')
        self.assertEqual(history_res.status_code, status.HTTP_200_OK)
        results = history_res.data.get('results', history_res.data)
        self.assertEqual(len(results), 1)

        # Create user 2
        user_2 = User.objects.create_user(email="perm_user2@example.com", password="Password123!")
        self.client.force_authenticate(user=user_2)

        # User 2 views order history -> should be empty
        other_history = self.client.get('/api/orders/my-orders/')
        other_results = other_history.data.get('results', other_history.data)
        self.assertEqual(len(other_results), 0)

        # User 2 tries to view User 1's order detail -> HTTP 404
        detail_res = self.client.get(f'/api/orders/{order_ref}/')
        self.assertEqual(detail_res.status_code, status.HTTP_404_NOT_FOUND)


class StripePaymentIntegrationTestCase(APITestCase):
    client: APIClient

    def setUp(self):
        Order.objects.all().delete()
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="stripe_test@example.com",
            password="Password123!",
            first_name="Stripe",
            last_name="Tester"
        )
        self.other_user = User.objects.create_user(
            email="other_stripe@example.com",
            password="Password123!",
            first_name="Other",
            last_name="Customer"
        )

        self.category = Category.objects.create(name="Stripe Groceries", slug="stripe-groceries")
        self.product = Product.objects.create(
            name="Yam Tuber",
            slug="yam-tuber",
            sku="YAM-STRIPE",
            price=Decimal("10.00"),
            stock_quantity=50,
            has_variants=False,
            is_active=True,
            category=self.category
        )

        # Create an Order
        self.order = Order.objects.create(
            user=self.user,
            recipient_name="Stripe Tester",
            phone_number="07000000000",
            address_line1="123 Stripe Way",
            city="London",
            postal_code="EC1A 1BB",
            country="United Kingdom",
            subtotal=Decimal("20.00"),
            delivery_fee=Decimal("3.99"),
            total_amount=Decimal("23.99"),
            order_status=Order.OrderStatus.CONFIRMED,
            payment_status=Order.PaymentStatus.PENDING
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name="Yam Tuber",
            sku="YAM-STRIPE",
            unit_price=Decimal("10.00"),
            quantity=2,
            line_total=Decimal("20.00")
        )

    def test_stripe_config_endpoint(self):
        with override_settings(STRIPE_PUBLISHABLE_KEY="pk_test_sample_123", STRIPE_CURRENCY="gbp"):
            res = self.client.get("/api/orders/stripe/config/")
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(res.data["publishable_key"], "pk_test_sample_123")
            self.assertEqual(res.data["currency"], "gbp")

    def test_checkout_session_missing_stripe_secret_key(self):
        self.client.force_authenticate(user=self.user)
        with override_settings(STRIPE_SECRET_KEY=""):
            res = self.client.post(f"/api/orders/{self.order.order_reference}/create-checkout-session/")
            self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
            self.assertIn("not configured", res.data["detail"].lower())

    def test_checkout_session_ownership_enforcement(self):
        # Unauthenticated user attempting to create checkout session for user order -> 401
        res_unauth = self.client.post(f"/api/orders/{self.order.order_reference}/create-checkout-session/")
        self.assertEqual(res_unauth.status_code, status.HTTP_401_UNAUTHORIZED)

        # Authenticated other user attempting to create checkout session for user order -> 403
        self.client.force_authenticate(user=self.other_user)
        res_other = self.client.post(f"/api/orders/{self.order.order_reference}/create-checkout-session/")
        self.assertEqual(res_other.status_code, status.HTTP_403_FORBIDDEN)

    @patch("apps.orders.stripe_service.stripe.checkout.Session.create")
    def test_checkout_session_creation_success_and_authoritative_gbp_calculation(self, mock_session_create):
        mock_session = MagicMock()
        mock_session.id = "cs_test_sample_session_12345"
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_sample_session_12345"
        mock_session_create.return_value = mock_session

        self.client.force_authenticate(user=self.user)
        with override_settings(STRIPE_SECRET_KEY="sk_test_mock_secret", STRIPE_CURRENCY="gbp"):
            res = self.client.post(f"/api/orders/{self.order.order_reference}/create-checkout-session/")
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(res.data["session_id"], "cs_test_sample_session_12345")
            self.assertEqual(res.data["checkout_url"], "https://checkout.stripe.com/pay/cs_test_sample_session_12345")
            self.assertEqual(res.data["total_amount"], "23.99")
            self.assertEqual(res.data["currency"], "gbp")

            # Verify Stripe checkout parameters
            mock_session_create.assert_called_once()
            call_kwargs = mock_session_create.call_args[1]
            self.assertEqual(call_kwargs["client_reference_id"], self.order.order_reference)
            self.assertEqual(call_kwargs["mode"], "payment")
            self.assertIn("metadata", call_kwargs)
            self.assertEqual(call_kwargs["metadata"]["order_reference"], self.order.order_reference)

            # Verify line items total matches order total £23.99 -> 2399 pence
            total_pence = sum(
                item["price_data"]["unit_amount"] * item["quantity"]
                for item in call_kwargs["line_items"]
            )
            self.assertEqual(total_pence, 2399)

            # Verify session ID was persisted on order
            self.order.refresh_from_db()
            self.assertEqual(self.order.stripe_checkout_session_id, "cs_test_sample_session_12345")

    def test_prevent_duplicate_payment_for_already_paid_order(self):
        self.order.payment_status = Order.PaymentStatus.PAID
        self.order.save()

        self.client.force_authenticate(user=self.user)
        with override_settings(STRIPE_SECRET_KEY="sk_test_mock_secret"):
            res = self.client.post(f"/api/orders/{self.order.order_reference}/create-checkout-session/")
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("already been paid", res.data["detail"])

    def test_prevent_payment_for_cancelled_order(self):
        self.order.order_status = Order.OrderStatus.CANCELLED
        self.order.save()

        self.client.force_authenticate(user=self.user)
        with override_settings(STRIPE_SECRET_KEY="sk_test_mock_secret"):
            res = self.client.post(f"/api/orders/{self.order.order_reference}/create-checkout-session/")
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("cancelled", res.data["detail"].lower())

    def test_order_payment_status_endpoint(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get(f"/api/orders/{self.order.order_reference}/payment-status/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["payment_status"], Order.PaymentStatus.PENDING)
        self.assertFalse(res.data["is_paid"])

    def test_webhook_missing_signature(self):
        res = self.client.post("/api/orders/webhook/", data=b"{}", content_type="application/json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Missing Stripe-Signature", res.data["detail"])

    @patch("apps.orders.stripe_service.stripe.Webhook.construct_event")
    def test_webhook_invalid_signature(self, mock_construct_event):
        mock_construct_event.side_effect = stripe.error.SignatureVerificationError("Invalid signature", "sig")
        with override_settings(STRIPE_WEBHOOK_SECRET="whsec_test_secret"):
            res = self.client.post(
                "/api/orders/webhook/",
                data=b"{}",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="invalid_signature_header"
            )
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("Invalid signature", res.data["detail"])

    @patch("apps.orders.stripe_service.stripe.Webhook.construct_event")
    def test_webhook_successful_payment_marks_order_paid(self, mock_construct_event):
        mock_construct_event.return_value = {
            "id": "evt_test_123",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "client_reference_id": self.order.order_reference,
                    "currency": "gbp",
                    "amount_total": 2399,
                    "payment_status": "paid",
                    "payment_intent": "pi_test_success_999",
                }
            }
        }

        with override_settings(STRIPE_WEBHOOK_SECRET="whsec_test_secret", STRIPE_CURRENCY="gbp"):
            res = self.client.post(
                "/api/orders/webhook/",
                data=b'{"id":"evt_test_123"}',
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="valid_signature_header"
            )
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(res.data["status"], "payment_confirmed")

            self.order.refresh_from_db()
            self.assertEqual(self.order.payment_status, Order.PaymentStatus.PAID)
            self.assertEqual(self.order.stripe_payment_intent_id, "pi_test_success_999")

    @patch("apps.orders.stripe_service.stripe.Webhook.construct_event")
    def test_webhook_idempotency_duplicate_delivery(self, mock_construct_event):
        self.order.payment_status = Order.PaymentStatus.PAID
        self.order.stripe_payment_intent_id = "pi_test_existing"
        self.order.save()

        mock_construct_event.return_value = {
            "id": "evt_test_duplicate",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_duplicate",
                    "client_reference_id": self.order.order_reference,
                    "currency": "gbp",
                    "amount_total": 2399,
                    "payment_status": "paid",
                    "payment_intent": "pi_test_existing",
                }
            }
        }

        with override_settings(STRIPE_WEBHOOK_SECRET="whsec_test_secret", STRIPE_CURRENCY="gbp"):
            res = self.client.post(
                "/api/orders/webhook/",
                data=b'{"id":"evt_test_duplicate"}',
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="valid_sig"
            )
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(res.data["status"], "already_processed")

            self.order.refresh_from_db()
            self.assertEqual(self.order.payment_status, Order.PaymentStatus.PAID)

    @patch("apps.orders.stripe_service.stripe.Webhook.construct_event")
    def test_webhook_amount_mismatch_rejected(self, mock_construct_event):
        mock_construct_event.return_value = {
            "id": "evt_test_amount_mismatch",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_mismatch",
                    "client_reference_id": self.order.order_reference,
                    "currency": "gbp",
                    "amount_total": 500,  # 500 pence instead of 2399 pence!
                    "payment_status": "paid",
                }
            }
        }

        with override_settings(STRIPE_WEBHOOK_SECRET="whsec_test_secret", STRIPE_CURRENCY="gbp"):
            res = self.client.post(
                "/api/orders/webhook/",
                data=b'{"id":"evt_test_amount_mismatch"}',
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="valid_sig"
            )
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(res.data["status"], "error")
            self.assertEqual(res.data["reason"], "amount_mismatch")

            self.order.refresh_from_db()
            self.assertEqual(self.order.payment_status, Order.PaymentStatus.PENDING)

    @patch("apps.orders.stripe_service.stripe.Webhook.construct_event")
    def test_webhook_currency_mismatch_rejected(self, mock_construct_event):
        mock_construct_event.return_value = {
            "id": "evt_test_currency_mismatch",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_mismatch",
                    "client_reference_id": self.order.order_reference,
                    "currency": "usd",  # USD instead of GBP
                    "amount_total": 2399,
                    "payment_status": "paid",
                }
            }
        }

        with override_settings(STRIPE_WEBHOOK_SECRET="whsec_test_secret", STRIPE_CURRENCY="gbp"):
            res = self.client.post(
                "/api/orders/webhook/",
                data=b'{"id":"evt_test_currency_mismatch"}',
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="valid_sig"
            )
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(res.data["status"], "error")
            self.assertEqual(res.data["reason"], "currency_mismatch")

            self.order.refresh_from_db()
            self.assertEqual(self.order.payment_status, Order.PaymentStatus.PENDING)

    @patch("apps.orders.stripe_service.stripe.Webhook.construct_event")
    def test_webhook_expired_session_marks_order_failed(self, mock_construct_event):
        mock_construct_event.return_value = {
            "id": "evt_test_expired",
            "type": "checkout.session.expired",
            "data": {
                "object": {
                    "id": "cs_test_expired",
                    "client_reference_id": self.order.order_reference,
                }
            }
        }

        with override_settings(STRIPE_WEBHOOK_SECRET="whsec_test_secret"):
            res = self.client.post(
                "/api/orders/webhook/",
                data=b'{"id":"evt_test_expired"}',
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="valid_sig"
            )
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(res.data["status"], "session_expired")

            self.order.refresh_from_db()
            self.assertEqual(self.order.payment_status, Order.PaymentStatus.FAILED)

    @patch("apps.orders.stripe_service.stripe.Webhook.construct_event")
    def test_webhook_payment_intent_failed_marks_order_failed(self, mock_construct_event):
        mock_construct_event.return_value = {
            "id": "evt_test_pi_failed",
            "type": "payment_intent.payment_failed",
            "data": {
                "object": {
                    "id": "pi_test_failed_888",
                    "metadata": {"order_reference": self.order.order_reference},
                }
            }
        }

        with override_settings(STRIPE_WEBHOOK_SECRET="whsec_test_secret"):
            res = self.client.post(
                "/api/orders/webhook/",
                data=b'{"id":"evt_test_pi_failed"}',
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="valid_sig"
            )
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(res.data["status"], "payment_failed")

            self.order.refresh_from_db()
            self.assertEqual(self.order.payment_status, Order.PaymentStatus.FAILED)
            self.assertEqual(self.order.stripe_payment_intent_id, "pi_test_failed_888")

    @patch("apps.orders.stripe_service.stripe.Webhook.construct_event")
    def test_webhook_payment_intent_succeeded_marks_order_paid(self, mock_construct_event):
        mock_construct_event.return_value = {
            "id": "evt_test_pi_succeeded",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test_succeeded_777",
                    "currency": "gbp",
                    "amount_received": 2399,
                    "metadata": {"order_reference": self.order.order_reference},
                }
            }
        }

        with override_settings(STRIPE_WEBHOOK_SECRET="whsec_test_secret", STRIPE_CURRENCY="gbp"):
            res = self.client.post(
                "/api/orders/webhook/",
                data=b'{"id":"evt_test_pi_succeeded"}',
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="valid_sig"
            )
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(res.data["status"], "payment_confirmed")

            self.order.refresh_from_db()
            self.assertEqual(self.order.payment_status, Order.PaymentStatus.PAID)
            self.assertEqual(self.order.stripe_payment_intent_id, "pi_test_succeeded_777")

    @patch("apps.orders.stripe_service.stripe.Webhook.construct_event")
    def test_webhook_charge_refunded_marks_order_refunded(self, mock_construct_event):
        self.order.payment_status = Order.PaymentStatus.PAID
        self.order.stripe_payment_intent_id = "pi_test_to_refund"
        self.order.save()

        mock_construct_event.return_value = {
            "id": "evt_test_charge_refunded",
            "type": "charge.refunded",
            "data": {
                "object": {
                    "id": "ch_test_refund_123",
                    "payment_intent": "pi_test_to_refund",
                    "metadata": {"order_reference": self.order.order_reference},
                }
            }
        }

        with override_settings(STRIPE_WEBHOOK_SECRET="whsec_test_secret"):
            res = self.client.post(
                "/api/orders/webhook/",
                data=b'{"id":"evt_test_charge_refunded"}',
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="valid_sig"
            )
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(res.data["status"], "order_refunded")

            self.order.refresh_from_db()
            self.assertEqual(self.order.payment_status, Order.PaymentStatus.REFUNDED)

    @patch("apps.orders.stripe_service.stripe.Webhook.construct_event")
    def test_webhook_arbitrary_event_returns_200_ignored(self, mock_construct_event):
        # Simulates Stripe sending arbitrary events when listening to all events (e.g., customer.created, charge.succeeded)
        mock_construct_event.return_value = {
            "id": "evt_test_customer_created",
            "type": "customer.created",
            "data": {
                "object": {
                    "id": "cus_test_999",
                }
            }
        }

        with override_settings(STRIPE_WEBHOOK_SECRET="whsec_test_secret"):
            res = self.client.post(
                "/api/orders/webhook/",
                data=b'{"id":"evt_test_customer_created"}',
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="valid_sig"
            )
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(res.data["status"], "ignored")
            self.assertIn("acknowledged", res.data["message"])


class TransactionalEmailAndGuestOrderSecurityTestCase(APITestCase):
    client: APIClient

    def setUp(self):
        Order.objects.all().delete()
        self.client = APIClient()

        self.category = Category.objects.create(name="African Groceries", slug="african-groceries")
        self.product = Product.objects.create(
            name="Plantain Chips",
            slug="plantain-chips",
            sku="CHIPS-001",
            price=Decimal("2.50"),
            stock_quantity=20,
            has_variants=False,
            is_active=True,
            category=self.category
        )

        # 1. Registered Customer Order
        self.customer = User.objects.create_user(
            email="buyer@example.com",
            password="Password123!",
            first_name="Amara",
            last_name="Okonkwo"
        )
        self.registered_order = Order.objects.create(
            user=self.customer,
            recipient_name="Amara Okonkwo",
            phone_number="07111222333",
            address_line1="45 Greenwich Lane",
            city="London",
            postal_code="SE10 9XX",
            country="United Kingdom",
            subtotal=Decimal("10.00"),
            delivery_fee=Decimal("3.99"),
            total_amount=Decimal("13.99"),
            order_status=Order.OrderStatus.CONFIRMED,
            payment_status=Order.PaymentStatus.PAID,
            stripe_checkout_session_id="cs_test_registered_session"
        )
        OrderItem.objects.create(
            order=self.registered_order,
            product=self.product,
            product_name="Plantain Chips",
            sku="CHIPS-001",
            unit_price=Decimal("2.50"),
            quantity=4,
            line_total=Decimal("10.00")
        )

        # 2. Guest Order
        self.guest_order = Order.objects.create(
            user=None,
            guest_email="guest.buyer@example.com",
            recipient_name="Kofi Mensah",
            phone_number="07444555666",
            address_line1="78 High Street",
            city="Manchester",
            postal_code="M1 1AA",
            country="United Kingdom",
            subtotal=Decimal("7.50"),
            delivery_fee=Decimal("3.99"),
            total_amount=Decimal("11.49"),
            order_status=Order.OrderStatus.CONFIRMED,
            payment_status=Order.PaymentStatus.PAID,
            stripe_checkout_session_id="cs_test_guest_session"
        )
        OrderItem.objects.create(
            order=self.guest_order,
            product=self.product,
            product_name="Plantain Chips",
            sku="CHIPS-001",
            unit_price=Decimal("2.50"),
            quantity=3,
            line_total=Decimal("7.50")
        )

    def test_send_order_confirmation_email_success_and_idempotency(self):
        from apps.orders.email_service import send_order_confirmation_email
        from django.core import mail

        # 1. First send: verify email dispatched and database record updated
        result = send_order_confirmation_email(self.registered_order)
        self.assertEqual(result["status"], "sent")
        self.registered_order.refresh_from_db()
        self.assertTrue(self.registered_order.confirmation_email_sent)
        self.assertIsNotNone(self.registered_order.confirmation_email_sent_at)
        self.assertEqual(self.registered_order.email_delivery_status, "ACCEPTED")
        self.assertEqual(len(mail.outbox), 1)

        sent_email = mail.outbox[0]
        self.assertIn("Payment Confirmation", sent_email.subject)
        self.assertIn("AdesHub Order", sent_email.subject)
        self.assertIn(self.registered_order.order_reference, sent_email.subject)
        self.assertEqual(sent_email.to, ["buyer@example.com"])
        self.assertIn("Amara Okonkwo", sent_email.body)
        self.assertIn("Plantain Chips", sent_email.body)
        self.assertIn("13.99", sent_email.body)

        # 2. Duplicate send attempt: verify idempotency (no second email created)
        duplicate_result = send_order_confirmation_email(self.registered_order)
        self.assertEqual(duplicate_result["status"], "already_sent")
        self.assertEqual(len(mail.outbox), 1)

    def test_send_order_status_update_emails(self):
        from apps.orders.email_service import send_order_status_update_email
        from django.core import mail

        # Test Shipped notification
        res_shipped = send_order_status_update_email(self.registered_order, Order.OrderStatus.SHIPPED)
        self.assertEqual(res_shipped["status"], "sent")
        self.registered_order.refresh_from_db()
        self.assertEqual(self.registered_order.last_status_email_sent, Order.OrderStatus.SHIPPED)
        self.assertIn("Dispatched", mail.outbox[-1].subject)

        # Test Delivered notification
        res_delivered = send_order_status_update_email(self.registered_order, Order.OrderStatus.DELIVERED)
        self.assertEqual(res_delivered["status"], "sent")
        self.registered_order.refresh_from_db()
        self.assertEqual(self.registered_order.last_status_email_sent, Order.OrderStatus.DELIVERED)
        self.assertIn("Delivered", mail.outbox[-1].subject)

    def test_guest_order_detail_security(self):
        ref = self.guest_order.order_reference

        # A. Unauthenticated request without email or session -> 403 guest_email_required
        res_no_auth = self.client.get(f"/api/orders/{ref}/")
        self.assertEqual(res_no_auth.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res_no_auth.data["code"], "guest_email_required")

        # B. Incorrect email -> 403 invalid_guest_email
        res_wrong_email = self.client.get(f"/api/orders/{ref}/?email=wrong.guest@example.com")
        self.assertEqual(res_wrong_email.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res_wrong_email.data["code"], "invalid_guest_email")

        # C. Matching email -> 200 OK with full order details
        res_valid_email = self.client.get(f"/api/orders/{ref}/?email=guest.buyer@example.com")
        self.assertEqual(res_valid_email.status_code, status.HTTP_200_OK)
        self.assertEqual(res_valid_email.data["order_reference"], ref)
        self.assertEqual(len(res_valid_email.data["items"]), 1)
        self.assertEqual(res_valid_email.data["items"][0]["product_name"], "Plantain Chips")

        # D. Matching Stripe session ID -> 200 OK
        res_session = self.client.get(f"/api/orders/{ref}/?session_id=cs_test_guest_session")
        self.assertEqual(res_session.status_code, status.HTTP_200_OK)
        self.assertEqual(res_session.data["order_reference"], ref)

    def test_payment_status_masks_pii_for_unverified_queries(self):
        ref = self.guest_order.order_reference

        # Query without session or email verification
        res_unverified = self.client.get(f"/api/orders/{ref}/payment-status/")
        self.assertEqual(res_unverified.status_code, status.HTTP_200_OK)
        self.assertEqual(res_unverified.data["customer_email"], "")
        self.assertIsNone(res_unverified.data["stripe_checkout_session_id"])

        # Query with valid session verification
        res_verified = self.client.get(f"/api/orders/{ref}/payment-status/?session_id=cs_test_guest_session")
        self.assertEqual(res_verified.status_code, status.HTTP_200_OK)
        self.assertEqual(res_verified.data["customer_email"], "guest.buyer@example.com")

    def test_webhook_checkout_session_completed_sends_email_and_marks_paid(self):
        """Test A: Verified successful payment webhook marks order PAID and sends confirmation email."""
        from django.core import mail
        from unittest.mock import patch
        import json

        mail.outbox.clear()
        ref = self.registered_order.order_reference
        self.registered_order.payment_status = Order.PaymentStatus.PENDING
        self.registered_order.confirmation_email_sent = False
        self.registered_order.email_delivery_status = 'PENDING'
        self.registered_order.save()
        self.assertEqual(self.registered_order.payment_status, Order.PaymentStatus.PENDING)

        payload = {
            'id': 'evt_test_completed_123',
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_test_session_abc',
                    'client_reference_id': ref,
                    'payment_status': 'paid',
                    'amount_total': 1399,
                    'currency': 'gbp',
                    'payment_intent': 'pi_test_intent_789',
                    'metadata': {
                        'order_reference': ref
                    }
                }
            }
        }
        payload_bytes = json.dumps(payload).encode('utf-8')

        with patch('stripe.Webhook.construct_event') as mock_construct:
            mock_construct.return_value = payload
            response = self.client.post(
                '/api/orders/webhook/',
                data=payload_bytes,
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='t=123,v1=test_sig'
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.registered_order.refresh_from_db()
        self.assertEqual(self.registered_order.payment_status, Order.PaymentStatus.PAID)
        self.assertTrue(self.registered_order.confirmation_email_sent)
        self.assertEqual(self.registered_order.email_delivery_status, 'ACCEPTED')

        # Verify email dispatched to the customer
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.to, ['buyer@example.com'])
        self.assertIn('Payment Confirmation', sent_email.subject)
        self.assertIn(ref, sent_email.subject)

    def test_webhook_failed_or_cancelled_does_not_send_confirmation_email(self):
        """Test B: Unsuccessful / failed payment does NOT send an order confirmation email."""
        from django.core import mail
        from unittest.mock import patch
        import json

        mail.outbox.clear()
        ref = self.guest_order.order_reference
        self.guest_order.payment_status = Order.PaymentStatus.PENDING
        self.guest_order.confirmation_email_sent = False
        self.guest_order.email_delivery_status = 'PENDING'
        self.guest_order.save()
        self.assertEqual(self.guest_order.payment_status, Order.PaymentStatus.PENDING)

        payload = {
            'id': 'evt_test_expired_123',
            'type': 'checkout.session.expired',
            'data': {
                'object': {
                    'id': 'cs_test_guest_session',
                    'client_reference_id': ref,
                    'payment_status': 'unpaid',
                    'metadata': {
                        'order_reference': ref
                    }
                }
            }
        }
        payload_bytes = json.dumps(payload).encode('utf-8')

        with patch('stripe.Webhook.construct_event') as mock_construct:
            mock_construct.return_value = payload
            response = self.client.post(
                '/api/orders/webhook/',
                data=payload_bytes,
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='t=123,v1=test_sig'
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.guest_order.refresh_from_db()
        self.assertEqual(self.guest_order.payment_status, Order.PaymentStatus.FAILED)
        self.assertFalse(self.guest_order.confirmation_email_sent)
        # Ensure 0 emails sent
        self.assertEqual(len(mail.outbox), 0)

    def test_duplicate_webhook_does_not_send_duplicate_emails(self):
        """Test C: Replaying duplicate successful webhook event does not send duplicate confirmation emails."""
        from django.core import mail
        from unittest.mock import patch
        import json

        mail.outbox.clear()
        ref = self.registered_order.order_reference
        self.registered_order.payment_status = Order.PaymentStatus.PENDING
        self.registered_order.confirmation_email_sent = False
        self.registered_order.email_delivery_status = 'PENDING'
        self.registered_order.save()

        payload = {
            'id': 'evt_test_dup_123',
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_test_session_dup',
                    'client_reference_id': ref,
                    'payment_status': 'paid',
                    'amount_total': 1399,
                    'currency': 'gbp',
                    'payment_intent': 'pi_test_dup',
                    'metadata': {
                        'order_reference': ref
                    }
                }
            }
        }
        payload_bytes = json.dumps(payload).encode('utf-8')

        with patch('stripe.Webhook.construct_event') as mock_construct:
            mock_construct.return_value = payload
            # First delivery
            res1 = self.client.post(
                '/api/orders/webhook/',
                data=payload_bytes,
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='t=123,v1=test_sig'
            )
            self.assertEqual(res1.status_code, status.HTTP_200_OK)
            self.assertEqual(len(mail.outbox), 1)

            # Replay duplicate delivery
            res2 = self.client.post(
                '/api/orders/webhook/',
                data=payload_bytes,
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='t=123,v1=test_sig'
            )
            self.assertEqual(res2.status_code, status.HTTP_200_OK)
            self.assertEqual(res2.data.get('status'), 'already_processed')
            # Still exactly 1 email dispatched (idempotency preserved)
            self.assertEqual(len(mail.outbox), 1)

    def test_email_sending_failure_preserves_paid_order_and_records_failure(self):
        """Test D: If email delivery fails, the order remains PAID and records failure for safe diagnosis."""
        from unittest.mock import patch
        from apps.orders.email_service import send_order_confirmation_email

        self.registered_order.payment_status = Order.PaymentStatus.PAID
        self.registered_order.confirmation_email_sent = False
        self.registered_order.email_delivery_status = 'PENDING'
        self.registered_order.save()

        with patch('django.core.mail.EmailMultiAlternatives.send', side_effect=Exception('SMTP Connection timeout')):
            result = send_order_confirmation_email(self.registered_order, max_retries=0)

        self.assertEqual(result['status'], 'failed')
        self.registered_order.refresh_from_db()
        # Crucial: Payment status MUST remain PAID
        self.assertEqual(self.registered_order.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(self.registered_order.email_delivery_status, 'FAILED')
        self.assertFalse(self.registered_order.confirmation_email_sent)

        # Retry after email issue is resolved succeeds safely without creating duplicate orders
        retry_result = send_order_confirmation_email(self.registered_order)
        self.assertEqual(retry_result['status'], 'sent')
        self.registered_order.refresh_from_db()
        self.assertTrue(self.registered_order.confirmation_email_sent)
        self.assertEqual(self.registered_order.email_delivery_status, 'ACCEPTED')

    def test_payment_status_view_reconciles_stripe_session_and_triggers_email(self):
        """Test E: Payment status check endpoint verifies paid Stripe session directly and dispatches email."""
        from django.core import mail
        from unittest.mock import patch

        mail.outbox.clear()
        ref = self.guest_order.order_reference
        session_id = self.guest_order.stripe_checkout_session_id
        self.guest_order.payment_status = Order.PaymentStatus.PENDING
        self.guest_order.confirmation_email_sent = False
        self.guest_order.email_delivery_status = 'PENDING'
        self.guest_order.save()
        self.assertEqual(self.guest_order.payment_status, Order.PaymentStatus.PENDING)

        expected_pence = round(self.guest_order.total_amount * 100)
        mock_session_obj = {
            'id': session_id,
            'payment_status': 'paid',
            'amount_total': expected_pence,
            'currency': 'gbp',
            'payment_intent': 'pi_reconciled_999',
            'customer_details': {'email': 'guest.buyer@example.com'},
        }

        with patch('stripe.checkout.Session.retrieve', return_value=mock_session_obj):
            response = self.client.get(f"/api/orders/{ref}/payment-status/?session_id={session_id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_paid'])
        self.guest_order.refresh_from_db()
        self.assertEqual(self.guest_order.payment_status, Order.PaymentStatus.PAID)
        self.assertTrue(self.guest_order.confirmation_email_sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['guest.buyer@example.com'])

    @patch("resend.Emails.send")
    def test_send_order_confirmation_email_via_resend_sdk(self, mock_resend_send):
        """Test order confirmation email sends via official Resend SDK when RESEND_API_KEY is configured."""
        from django.test import override_settings
        from apps.orders.email_service import send_order_confirmation_email

        mock_resend_send.return_value = {"id": "msg_resend_order_789"}

        with override_settings(
            RESEND_API_KEY="re_mock_order_key",
            EMAIL_FROM="AdesHub <noreply@adeshubafricanstore.com>",
            EMAIL_REPLY_TO="Info@adeshub.co.uk",
        ):
            res = send_order_confirmation_email(self.registered_order)

        self.assertEqual(res["status"], "sent")
        self.registered_order.refresh_from_db()
        self.assertTrue(self.registered_order.confirmation_email_sent)
        self.assertEqual(self.registered_order.email_delivery_status, "ACCEPTED")

        mock_resend_send.assert_called_once()
        call_params = mock_resend_send.call_args[0][0]
        self.assertEqual(call_params["from"], "AdesHub <noreply@adeshubafricanstore.com>")
        self.assertEqual(call_params["to"], "buyer@example.com")
        self.assertIn(self.registered_order.order_reference, call_params["subject"])
        self.assertEqual(call_params["reply_to"], "Info@adeshub.co.uk")
        self.assertIn("13.99", call_params["text"])
        self.assertIn("Plantain Chips", call_params["text"])
        self.assertIn("SE10 9XX", call_params["text"])

    @patch("resend.Emails.send")
    def test_resend_stripe_webhook_retry_prevents_duplicate_email(self, mock_resend_send):
        """Test Stripe webhook retries and duplicate events do NOT send duplicate Resend emails."""
        from django.test import override_settings
        import json

        mock_resend_send.return_value = {"id": "msg_resend_single_send"}

        ref = self.registered_order.order_reference
        self.registered_order.payment_status = Order.PaymentStatus.PENDING
        self.registered_order.confirmation_email_sent = False
        self.registered_order.email_delivery_status = 'PENDING'
        self.registered_order.save()

        expected_pence = round(self.registered_order.total_amount * 100)
        payload = {
            'id': 'evt_test_resend_webhook_retry',
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_test_resend_retry_session',
                    'client_reference_id': ref,
                    'payment_status': 'paid',
                    'amount_total': expected_pence,
                    'currency': 'gbp',
                    'payment_intent': 'pi_test_resend_999',
                    'customer_details': {'email': 'buyer@example.com'},
                    'metadata': {'order_reference': ref},
                }
            }
        }
        raw_body = json.dumps(payload).encode('utf-8')

        with override_settings(
            STRIPE_WEBHOOK_SECRET="whsec_test_secret",
            STRIPE_CURRENCY="gbp",
            RESEND_API_KEY="re_mock_order_key",
            EMAIL_FROM="AdesHub <noreply@adeshubafricanstore.com>",
        ):
            with patch("apps.orders.stripe_service.stripe.Webhook.construct_event", return_value=payload):
                # 1. First webhook event arrival
                first_resp = self.client.post(
                    "/api/orders/webhook/",
                    data=raw_body,
                    content_type="application/json",
                    HTTP_STRIPE_SIGNATURE="valid_sig_1"
                )
                self.assertEqual(first_resp.status_code, status.HTTP_200_OK)
                self.assertEqual(first_resp.data["status"], "payment_confirmed")

                # Verify email sent via Resend once
                self.assertEqual(mock_resend_send.call_count, 1)

                # 2. Second webhook event arrival (Stripe retry or duplicate notification)
                second_resp = self.client.post(
                    "/api/orders/webhook/",
                    data=raw_body,
                    content_type="application/json",
                    HTTP_STRIPE_SIGNATURE="valid_sig_2"
                )
                self.assertEqual(second_resp.status_code, status.HTTP_200_OK)
                self.assertEqual(second_resp.data["status"], "already_processed")

                # Verify Resend was NOT called again (call_count remains 1)
                self.assertEqual(mock_resend_send.call_count, 1)

    @patch("resend.Emails.send")
    def test_resend_order_confirmation_failure_preserves_payment_status(self, mock_resend_send):
        """Test that a Resend API delivery failure does not invalidate an otherwise successful payment."""
        from django.test import override_settings
        from apps.orders.email_service import send_order_confirmation_email

        mock_resend_send.side_effect = Exception("Resend 500 internal server error")

        self.registered_order.payment_status = Order.PaymentStatus.PAID
        self.registered_order.confirmation_email_sent = False
        self.registered_order.email_delivery_status = 'PENDING'
        self.registered_order.save()

        with override_settings(
            RESEND_API_KEY="re_mock_order_key",
            EMAIL_FROM="AdesHub <noreply@adeshubafricanstore.com>",
        ):
            result = send_order_confirmation_email(self.registered_order, max_retries=0)

        self.assertEqual(result["status"], "failed")
        self.registered_order.refresh_from_db()

        # Payment MUST remain intact (PAID)
        self.assertEqual(self.registered_order.payment_status, Order.PaymentStatus.PAID)
        self.assertFalse(self.registered_order.confirmation_email_sent)
        self.assertEqual(self.registered_order.email_delivery_status, "FAILED")


