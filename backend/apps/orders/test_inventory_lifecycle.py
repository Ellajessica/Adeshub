from datetime import timedelta
from decimal import Decimal
import json
from unittest.mock import patch, MagicMock
from django.conf import settings
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from apps.accounts.models import User
from apps.products.models import Product, ProductVariant, Category
from apps.orders.models import Order, OrderItem
from apps.orders.inventory_service import restore_order_inventory


class InventoryLifecycleTestCase(APITestCase):
    client: APIClient

    def setUp(self):
        Order.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        self.client = APIClient()

        # Category
        self.category = Category.objects.create(name="African Foods", slug="african-foods")

        # Simple Product (10 in stock)
        self.simple_product = Product.objects.create(
            name="Brown Beans 5kg",
            slug="brown-beans-5kg",
            sku="BEANS-001",
            price=Decimal("12.50"),
            stock_quantity=10,
            has_variants=False,
            is_active=True,
            category=self.category,
        )

        # Variant Product (Parent product + variant with 8 in stock)
        self.variant_product = Product.objects.create(
            name="Palm Oil",
            slug="palm-oil",
            sku="PALM-001",
            price=Decimal("5.00"),
            stock_quantity=0,
            has_variants=True,
            is_active=True,
            category=self.category,
        )
        self.variant_2l = ProductVariant.objects.create(
            product=self.variant_product,
            name="2 Litres",
            sku="PALM-001-2L",
            price=Decimal("9.00"),
            stock_quantity=8,
            is_active=True,
        )

        # Staff User for Admin API tests
        self.staff_user = User.objects.create_user(
            email="staff@adeshub.com",
            password="StaffPassword123!",
            first_name="Store",
            last_name="Manager",
            user_type=User.UserType.STAFF,
            is_staff=True,
        )

        # Customer User
        self.customer_user = User.objects.create_user(
            email="shopper@example.com",
            password="CustomerPassword123!",
            first_name="Jane",
            last_name="Doe",
        )

    def _create_unpaid_order(self, simple_qty=3, variant_qty=0, minutes_old=0):
        """Helper to create an order and deduct stock identically to checkout."""
        subtotal = Decimal('0.00')
        order = Order.objects.create(
            user=self.customer_user,
            recipient_name="Jane Doe",
            phone_number="07123456789",
            address_line1="12 High Street",
            city="London",
            postal_code="SE10 9XX",
            country="United Kingdom",
            subtotal=Decimal('0.00'),
            delivery_fee=Decimal('3.99'),
            total_amount=Decimal('3.99'),
            order_status=Order.OrderStatus.CONFIRMED,
            payment_status=Order.PaymentStatus.PENDING,
            inventory_restored=False,
            stripe_checkout_session_id="cs_test_session_lifecycle",
        )

        if minutes_old > 0:
            past_time = timezone.now() - timedelta(minutes=minutes_old)
            Order.objects.filter(pk=order.pk).update(created_at=past_time)
            order.refresh_from_db()

        if simple_qty > 0:
            self.simple_product.stock_quantity -= simple_qty
            self.simple_product.save(update_fields=['stock_quantity'])
            line_total = self.simple_product.price * simple_qty
            subtotal += line_total
            OrderItem.objects.create(
                order=order,
                product=self.simple_product,
                product_name=self.simple_product.name,
                sku=self.simple_product.sku,
                unit_price=self.simple_product.price,
                quantity=simple_qty,
                line_total=line_total,
            )

        if variant_qty > 0:
            self.variant_2l.stock_quantity -= variant_qty
            self.variant_2l.save(update_fields=['stock_quantity'])
            line_total = self.variant_2l.price * variant_qty
            subtotal += line_total
            OrderItem.objects.create(
                order=order,
                product=self.variant_product,
                variant=self.variant_2l,
                product_name=self.variant_product.name,
                variant_name=self.variant_2l.name,
                sku=self.variant_2l.sku,
                unit_price=self.variant_2l.price,
                quantity=variant_qty,
                line_total=line_total,
            )

        order.subtotal = subtotal
        order.total_amount = subtotal + order.delivery_fee
        order.save(update_fields=['subtotal', 'total_amount'])
        return order

    # -------------------------------------------------------------------------
    # 1. Successful payment does not restore stock
    # -------------------------------------------------------------------------
    def test_successful_payment_does_not_restore_stock(self):
        order = self._create_unpaid_order(simple_qty=3)
        self.assertEqual(self.simple_product.stock_quantity, 7)

        expected_pence = round(order.total_amount * 100)
        payload = {
            'id': 'evt_test_paid_1',
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': order.stripe_checkout_session_id,
                    'client_reference_id': order.order_reference,
                    'payment_status': 'paid',
                    'amount_total': expected_pence,
                    'currency': 'gbp',
                    'payment_intent': 'pi_test_success_1',
                    'metadata': {'order_reference': order.order_reference},
                }
            }
        }

        with override_settings(STRIPE_WEBHOOK_SECRET="whsec_test"):
            with patch('apps.orders.stripe_service.stripe.Webhook.construct_event', return_value=payload):
                res = self.client.post(
                    '/api/orders/webhook/',
                    data=json.dumps(payload).encode('utf-8'),
                    content_type='application/json',
                    HTTP_STRIPE_SIGNATURE='valid_sig'
                )
                self.assertEqual(res.status_code, status.HTTP_200_OK)

        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        self.assertFalse(order.inventory_restored)

        # Stock remains at 7 (NOT restored)
        self.simple_product.refresh_from_db()
        self.assertEqual(self.simple_product.stock_quantity, 7)

    # -------------------------------------------------------------------------
    # 2. Checkout Session expiration restores stock
    # -------------------------------------------------------------------------
    def test_checkout_session_expiration_restores_stock(self):
        order = self._create_unpaid_order(simple_qty=4)
        self.assertEqual(self.simple_product.stock_quantity, 6)

        payload = {
            'id': 'evt_test_expired_1',
            'type': 'checkout.session.expired',
            'data': {
                'object': {
                    'id': order.stripe_checkout_session_id,
                    'client_reference_id': order.order_reference,
                    'metadata': {'order_reference': order.order_reference},
                }
            }
        }

        with override_settings(STRIPE_WEBHOOK_SECRET="whsec_test"):
            with patch('apps.orders.stripe_service.stripe.Webhook.construct_event', return_value=payload):
                res = self.client.post(
                    '/api/orders/webhook/',
                    data=json.dumps(payload).encode('utf-8'),
                    content_type='application/json',
                    HTTP_STRIPE_SIGNATURE='valid_sig'
                )
                self.assertEqual(res.status_code, status.HTTP_200_OK)
                self.assertEqual(res.data['status'], 'session_expired')

        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.FAILED)
        self.assertEqual(order.order_status, Order.OrderStatus.CANCELLED)
        self.assertTrue(order.inventory_restored)
        self.assertIsNotNone(order.inventory_restored_at)

        # Stock restored from 6 back to 10
        self.simple_product.refresh_from_db()
        self.assertEqual(self.simple_product.stock_quantity, 10)

    # -------------------------------------------------------------------------
    # 3. Duplicate expiration webhooks restore stock only once
    # -------------------------------------------------------------------------
    def test_duplicate_expiration_webhooks_restore_stock_only_once(self):
        order = self._create_unpaid_order(simple_qty=4)
        self.assertEqual(self.simple_product.stock_quantity, 6)

        payload = {
            'id': 'evt_test_expired_dup',
            'type': 'checkout.session.expired',
            'data': {
                'object': {
                    'id': order.stripe_checkout_session_id,
                    'client_reference_id': order.order_reference,
                    'metadata': {'order_reference': order.order_reference},
                }
            }
        }

        with override_settings(STRIPE_WEBHOOK_SECRET="whsec_test"):
            with patch('apps.orders.stripe_service.stripe.Webhook.construct_event', return_value=payload):
                # First webhook delivery
                res1 = self.client.post(
                    '/api/orders/webhook/',
                    data=json.dumps(payload).encode('utf-8'),
                    content_type='application/json',
                    HTTP_STRIPE_SIGNATURE='valid_sig'
                )
                self.assertEqual(res1.status_code, status.HTTP_200_OK)

                self.simple_product.refresh_from_db()
                self.assertEqual(self.simple_product.stock_quantity, 10)

                # Second duplicate delivery
                res2 = self.client.post(
                    '/api/orders/webhook/',
                    data=json.dumps(payload).encode('utf-8'),
                    content_type='application/json',
                    HTTP_STRIPE_SIGNATURE='valid_sig'
                )
                self.assertEqual(res2.status_code, status.HTTP_200_OK)

        # Stock MUST remain 10 (NEVER double-restored to 14)
        self.simple_product.refresh_from_db()
        self.assertEqual(self.simple_product.stock_quantity, 10)

    # -------------------------------------------------------------------------
    # 4. Duplicate payment failure events cannot restore stock twice
    # -------------------------------------------------------------------------
    def test_duplicate_payment_failure_events_cannot_restore_stock_twice(self):
        order = self._create_unpaid_order(simple_qty=3)
        self.assertEqual(self.simple_product.stock_quantity, 7)

        payload = {
            'id': 'evt_test_pi_fail_dup',
            'type': 'payment_intent.payment_failed',
            'data': {
                'object': {
                    'id': 'pi_declined_123',
                    'metadata': {'order_reference': order.order_reference},
                }
            }
        }

        with override_settings(STRIPE_WEBHOOK_SECRET="whsec_test"):
            with patch('apps.orders.stripe_service.stripe.Webhook.construct_event', return_value=payload):
                res1 = self.client.post(
                    '/api/orders/webhook/',
                    data=json.dumps(payload).encode('utf-8'),
                    content_type='application/json',
                    HTTP_STRIPE_SIGNATURE='valid_sig'
                )
                self.assertEqual(res1.status_code, status.HTTP_200_OK)

                res2 = self.client.post(
                    '/api/orders/webhook/',
                    data=json.dumps(payload).encode('utf-8'),
                    content_type='application/json',
                    HTTP_STRIPE_SIGNATURE='valid_sig'
                )
                self.assertEqual(res2.status_code, status.HTTP_200_OK)

        # Stock is NOT prematurely restored while session is active
        self.simple_product.refresh_from_db()
        self.assertEqual(self.simple_product.stock_quantity, 7)
        order.refresh_from_db()
        self.assertFalse(order.inventory_restored)

    # -------------------------------------------------------------------------
    # 5. An eligible abandoned order is restored by the cleanup command
    # -------------------------------------------------------------------------
    def test_eligible_abandoned_order_is_restored_by_cleanup_command(self):
        # 90 minutes old, unpaid order
        order = self._create_unpaid_order(simple_qty=5, minutes_old=90)
        self.assertEqual(self.simple_product.stock_quantity, 5)

        call_command('cleanup_abandoned_orders', timeout_minutes=60, skip_stripe_check=True)

        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.OrderStatus.CANCELLED)
        self.assertEqual(order.payment_status, Order.PaymentStatus.FAILED)
        self.assertTrue(order.inventory_restored)

        # Restored to 10
        self.simple_product.refresh_from_db()
        self.assertEqual(self.simple_product.stock_quantity, 10)

    # -------------------------------------------------------------------------
    # 6. Running the cleanup command twice is safe
    # -------------------------------------------------------------------------
    def test_running_cleanup_command_twice_is_safe(self):
        order = self._create_unpaid_order(simple_qty=5, minutes_old=90)
        self.assertEqual(self.simple_product.stock_quantity, 5)

        # First run restores
        call_command('cleanup_abandoned_orders', timeout_minutes=60, skip_stripe_check=True)
        self.simple_product.refresh_from_db()
        self.assertEqual(self.simple_product.stock_quantity, 10)

        # Second run is completely idempotent
        call_command('cleanup_abandoned_orders', timeout_minutes=60, skip_stripe_check=True)
        self.simple_product.refresh_from_db()
        self.assertEqual(self.simple_product.stock_quantity, 10)

    # -------------------------------------------------------------------------
    # 7. Paid orders are never restored by the cleanup command
    # -------------------------------------------------------------------------
    def test_paid_orders_are_never_restored_by_cleanup_command(self):
        order = self._create_unpaid_order(simple_qty=4, minutes_old=120)
        order.payment_status = Order.PaymentStatus.PAID
        order.save(update_fields=['payment_status'])
        self.assertEqual(self.simple_product.stock_quantity, 6)

        call_command('cleanup_abandoned_orders', timeout_minutes=60, skip_stripe_check=True)

        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        self.assertFalse(order.inventory_restored)

        # Stock remains at 6
        self.simple_product.refresh_from_db()
        self.assertEqual(self.simple_product.stock_quantity, 6)

    # -------------------------------------------------------------------------
    # 8. A late expiration event cannot undo a successful payment
    # -------------------------------------------------------------------------
    def test_late_expiration_event_cannot_undo_successful_payment(self):
        order = self._create_unpaid_order(simple_qty=3)
        order.payment_status = Order.PaymentStatus.PAID
        order.order_status = Order.OrderStatus.CONFIRMED
        order.save(update_fields=['payment_status', 'order_status'])
        self.assertEqual(self.simple_product.stock_quantity, 7)

        payload = {
            'id': 'evt_test_late_exp',
            'type': 'checkout.session.expired',
            'data': {
                'object': {
                    'id': order.stripe_checkout_session_id,
                    'client_reference_id': order.order_reference,
                    'metadata': {'order_reference': order.order_reference},
                }
            }
        }

        with override_settings(STRIPE_WEBHOOK_SECRET="whsec_test"):
            with patch('apps.orders.stripe_service.stripe.Webhook.construct_event', return_value=payload):
                res = self.client.post(
                    '/api/orders/webhook/',
                    data=json.dumps(payload).encode('utf-8'),
                    content_type='application/json',
                    HTTP_STRIPE_SIGNATURE='valid_sig'
                )
                self.assertEqual(res.status_code, status.HTTP_200_OK)
                self.assertEqual(res.data['status'], 'already_processed')

        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(order.order_status, Order.OrderStatus.CONFIRMED)
        self.assertFalse(order.inventory_restored)

        # Stock remains at 7
        self.simple_product.refresh_from_db()
        self.assertEqual(self.simple_product.stock_quantity, 7)

    # -------------------------------------------------------------------------
    # 9. Product variants are restored correctly
    # -------------------------------------------------------------------------
    def test_product_variants_are_restored_correctly(self):
        # Order 3 of the 2L Palm Oil variant (initial: 8, drops to 5)
        order = self._create_unpaid_order(simple_qty=0, variant_qty=3)
        self.variant_2l.refresh_from_db()
        self.assertEqual(self.variant_2l.stock_quantity, 5)

        restore_result = restore_order_inventory(order, reason="Test variant restoration")
        self.assertTrue(restore_result['restored'])

        self.variant_2l.refresh_from_db()
        self.assertEqual(self.variant_2l.stock_quantity, 8)

    # -------------------------------------------------------------------------
    # 10. Orders containing multiple products are restored correctly
    # -------------------------------------------------------------------------
    def test_orders_containing_multiple_products_are_restored_correctly(self):
        # Order 2 simple products (10 -> 8) and 3 variants (8 -> 5)
        order = self._create_unpaid_order(simple_qty=2, variant_qty=3)
        self.simple_product.refresh_from_db()
        self.variant_2l.refresh_from_db()
        self.assertEqual(self.simple_product.stock_quantity, 8)
        self.assertEqual(self.variant_2l.stock_quantity, 5)

        restore_result = restore_order_inventory(order, reason="Multi-item order cancellation")
        self.assertTrue(restore_result['restored'])

        self.simple_product.refresh_from_db()
        self.variant_2l.refresh_from_db()
        self.assertEqual(self.simple_product.stock_quantity, 10)
        self.assertEqual(self.variant_2l.stock_quantity, 8)

    # -------------------------------------------------------------------------
    # 11. A failure during restoration does not leave partially restored inventory
    # -------------------------------------------------------------------------
    def test_failure_during_restoration_does_not_leave_partially_restored_inventory(self):
        order = self._create_unpaid_order(simple_qty=2, variant_qty=3)
        self.simple_product.refresh_from_db()
        self.variant_2l.refresh_from_db()
        self.assertEqual(self.simple_product.stock_quantity, 8)
        self.assertEqual(self.variant_2l.stock_quantity, 5)

        # Mock variant save to throw an unhandled DB error
        with patch.object(ProductVariant, 'save', side_effect=RuntimeError("Database failure")):
            with self.assertRaises(RuntimeError):
                restore_order_inventory(order, reason="Simulated failure test")

        # Atomic rollback verification: simple product must NOT have remained restored
        self.simple_product.refresh_from_db()
        self.variant_2l.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(self.simple_product.stock_quantity, 8)
        self.assertEqual(self.variant_2l.stock_quantity, 5)
        self.assertFalse(order.inventory_restored)

    # -------------------------------------------------------------------------
    # 12. React admin cancellation restores eligible unpaid orders once
    # -------------------------------------------------------------------------
    def test_react_admin_cancellation_restores_eligible_unpaid_orders_once(self):
        order = self._create_unpaid_order(simple_qty=4)
        self.assertEqual(self.simple_product.stock_quantity, 6)

        self.client.force_authenticate(user=self.staff_user)
        res = self.client.patch(
            f"/api/admin/orders/{order.order_reference}/status/",
            data={'order_status': 'CANCELLED'},
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.OrderStatus.CANCELLED)
        self.assertTrue(order.inventory_restored)

        self.simple_product.refresh_from_db()
        self.assertEqual(self.simple_product.stock_quantity, 10)

        # Second attempt to cancel terminal state is idempotent and does not restock again
        res2 = self.client.patch(
            f"/api/admin/orders/{order.order_reference}/status/",
            data={'order_status': 'CANCELLED'},
            format='json'
        )
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.simple_product.refresh_from_db()
        self.assertEqual(self.simple_product.stock_quantity, 10)

    # -------------------------------------------------------------------------
    # 13. Django Admin cancellation restores eligible unpaid orders once
    # -------------------------------------------------------------------------
    def test_django_admin_cancellation_restores_eligible_unpaid_orders_once(self):
        order = self._create_unpaid_order(simple_qty=4)
        self.assertEqual(self.simple_product.stock_quantity, 6)

        from apps.orders.admin import OrderAdmin
        from django.contrib.admin.sites import AdminSite

        admin_instance = OrderAdmin(Order, AdminSite())

        mock_request = MagicMock()
        mock_request.user = self.staff_user

        mock_form = MagicMock()
        mock_form.changed_data = ['order_status']

        order.order_status = Order.OrderStatus.CANCELLED
        admin_instance.save_model(mock_request, order, mock_form, change=True)

        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.OrderStatus.CANCELLED)
        self.assertTrue(order.inventory_restored)

        self.simple_product.refresh_from_db()
        self.assertEqual(self.simple_product.stock_quantity, 10)

    # -------------------------------------------------------------------------
    # 14. Paid order cancellation does not trigger an unintended refund
    # -------------------------------------------------------------------------
    def test_paid_order_cancellation_does_not_trigger_unintended_refund(self):
        order = self._create_unpaid_order(simple_qty=3)
        order.payment_status = Order.PaymentStatus.PAID
        order.save(update_fields=['payment_status'])
        self.assertEqual(self.simple_product.stock_quantity, 7)

        self.client.force_authenticate(user=self.staff_user)
        with patch('apps.orders.stripe_service.stripe.Refund.create') as mock_refund:
            res = self.client.patch(
                f"/api/admin/orders/{order.order_reference}/status/",
                data={'order_status': 'CANCELLED'},
                format='json'
            )
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            # Automatic refund MUST NOT be triggered
            mock_refund.assert_not_called()

        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.OrderStatus.CANCELLED)
        # Payment status remains PAID (not automatically changed to REFUNDED)
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        # Paid orders are NOT automatically restocked
        self.assertFalse(order.inventory_restored)
        self.simple_product.refresh_from_db()
        self.assertEqual(self.simple_product.stock_quantity, 7)

    # -------------------------------------------------------------------------
    # 15. Existing stock availability and overselling protection still work
    # -------------------------------------------------------------------------
    def test_existing_stock_availability_and_overselling_protection_still_work(self):
        from apps.cart.models import Cart, CartItem
        # Product has 10 units in stock
        cart = Cart.objects.create(user=self.customer_user)
        # Add 10 items to cart
        CartItem.objects.create(cart=cart, product=self.simple_product, quantity=10)

        # Attempt to create order for 10 units succeeds
        self.client.force_authenticate(user=self.customer_user)
        res1 = self.client.post(
            "/api/orders/",
            data={
                'recipient_name': 'Test Buyer',
                'phone_number': '07000000000',
                'address_line1': '1 Market Road',
                'city': 'London',
                'postal_code': 'SE1 1AA',
            },
            format='json'
        )
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        self.simple_product.refresh_from_db()
        self.assertEqual(self.simple_product.stock_quantity, 0)

        # Attempt to add out-of-stock item raises ValidationError at model level
        from django.core.exceptions import ValidationError
        cart2 = Cart.objects.create(user=self.customer_user)
        with self.assertRaises(ValidationError):
            CartItem.objects.create(cart=cart2, product=self.simple_product, quantity=1)

        # Attempt to add out-of-stock item via cart API endpoint fails with 400
        res_cart = self.client.post(
            "/api/cart/items/",
            data={
                'product_id': self.simple_product.id,
                'quantity': 1,
            },
            format='json'
        )
        self.assertEqual(res_cart.status_code, status.HTTP_400_BAD_REQUEST)
        self.simple_product.refresh_from_db()
        self.assertEqual(self.simple_product.stock_quantity, 0)
