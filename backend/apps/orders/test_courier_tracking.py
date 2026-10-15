from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.products.models import Product, Category
from apps.orders.models import Order, OrderItem
from apps.orders.email_service import send_order_status_update_email


class CourierTrackingTestCase(TestCase):
    client: APIClient

    def setUp(self):
        Order.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        self.client = APIClient()

        self.category = Category.objects.create(name="African Pantry", slug="african-pantry")

        self.product = Product.objects.create(
            name="Egusi Melon Seeds 1kg",
            slug="egusi-melon-seeds-1kg",
            sku="EGU-001",
            price=Decimal("15.00"),
            stock_quantity=20,
            has_variants=False,
            is_active=True,
            category=self.category,
        )

        # Staff user
        self.staff_user = User.objects.create_user(
            email="admin@adeshub.com",
            password="AdminPassword123!",
            first_name="Admin",
            last_name="User",
            user_type=User.UserType.STAFF,
            is_staff=True,
        )

        # Customer user
        self.customer_user = User.objects.create_user(
            email="customer@example.com",
            password="CustomerPassword123!",
            first_name="Alice",
            last_name="Smith",
        )

        # Other customer user (for permission / isolation checks)
        self.other_customer = User.objects.create_user(
            email="other@example.com",
            password="OtherPassword123!",
            first_name="Bob",
            last_name="Jones",
        )

    def _create_test_order(self, order_status=Order.OrderStatus.PROCESSING, payment_status=Order.PaymentStatus.PAID):
        order = Order.objects.create(
            user=self.customer_user,
            recipient_name="Alice Smith",
            phone_number="07999888777",
            address_line1="42 Acacia Avenue",
            city="London",
            postal_code="NW1 4NP",
            country="United Kingdom",
            subtotal=Decimal("30.00"),
            delivery_fee=Decimal("3.99"),
            total_amount=Decimal("33.99"),
            order_status=order_status,
            payment_status=payment_status,
            stripe_checkout_session_id="cs_test_tracking_01",
            stripe_payment_intent_id="pi_test_tracking_01",
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            sku=self.product.sku,
            unit_price=self.product.price,
            quantity=2,
            line_total=Decimal("30.00"),
        )
        return order

    # -------------------------------------------------------------------------
    # 1. Saving courier details
    # -------------------------------------------------------------------------
    def test_saving_courier_details(self):
        order = self._create_test_order()
        self.client.force_authenticate(user=self.staff_user)

        res = self.client.patch(
            f"/api/admin/orders/{order.order_reference}/status/",
            data={
                'courier_name': 'Royal Mail Tracked 24',
                'shipment_reference': 'SHP-2026-RM99',
                'tracking_number': 'GB987654321RM',
                'tracking_url': 'https://www.royalmail.com/track-your-item#/tracking-results/GB987654321RM',
            },
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        order.refresh_from_db()
        self.assertEqual(order.courier_name, 'Royal Mail Tracked 24')
        self.assertEqual(order.shipment_reference, 'SHP-2026-RM99')
        self.assertEqual(order.tracking_number, 'GB987654321RM')
        self.assertEqual(order.tracking_url, 'https://www.royalmail.com/track-your-item#/tracking-results/GB987654321RM')

        # Check serialized response
        self.assertEqual(res.data['courier_name'], 'Royal Mail Tracked 24')
        self.assertEqual(res.data['tracking_number'], 'GB987654321RM')

    # -------------------------------------------------------------------------
    # 2. Saving and validating tracking URLs
    # -------------------------------------------------------------------------
    def test_saving_and_validating_tracking_urls(self):
        order = self._create_test_order()
        self.client.force_authenticate(user=self.staff_user)

        # Valid HTTPS URL succeeds
        res_valid_https = self.client.patch(
            f"/api/admin/orders/{order.order_reference}/status/",
            data={'tracking_url': 'https://track.dpd.co.uk/p/12345678'},
            format='json'
        )
        self.assertEqual(res_valid_https.status_code, status.HTTP_200_OK)

        # Valid HTTP URL succeeds
        res_valid_http = self.client.patch(
            f"/api/admin/orders/{order.order_reference}/status/",
            data={'tracking_url': 'http://courier.example.com/track?id=99'},
            format='json'
        )
        self.assertEqual(res_valid_http.status_code, status.HTTP_200_OK)

        # Unsafe scheme: javascript: is rejected
        res_js = self.client.patch(
            f"/api/admin/orders/{order.order_reference}/status/",
            data={'tracking_url': 'javascript:alert(document.cookie)'},
            format='json'
        )
        self.assertEqual(res_js.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Tracking URL must start with a valid web protocol", res_js.data['detail'])

        # Unsafe scheme: data: is rejected
        res_data = self.client.patch(
            f"/api/admin/orders/{order.order_reference}/status/",
            data={'tracking_url': 'data:text/html,<script>evil()</script>'},
            format='json'
        )
        self.assertEqual(res_data.status_code, status.HTTP_400_BAD_REQUEST)

        # Incomplete / protocol-less string is rejected
        res_invalid = self.client.patch(
            f"/api/admin/orders/{order.order_reference}/status/",
            data={'tracking_url': 'not_a_valid_url'},
            format='json'
        )
        self.assertEqual(res_invalid.status_code, status.HTTP_400_BAD_REQUEST)

    # -------------------------------------------------------------------------
    # 3. Rejecting unauthorised changes
    # -------------------------------------------------------------------------
    def test_rejecting_unauthorised_changes(self):
        order = self._create_test_order()

        # Anonymous request is rejected
        self.client.logout()
        res_anon = self.client.patch(
            f"/api/admin/orders/{order.order_reference}/status/",
            data={'courier_name': 'Hacker Courier'},
            format='json'
        )
        self.assertIn(res_anon.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

        # Regular customer is rejected
        self.client.force_authenticate(user=self.customer_user)
        res_cust = self.client.patch(
            f"/api/admin/orders/{order.order_reference}/status/",
            data={'courier_name': 'Customer Attempted Change'},
            format='json'
        )
        self.assertEqual(res_cust.status_code, status.HTTP_403_FORBIDDEN)

        # Verify DB remained unchanged
        order.refresh_from_db()
        self.assertEqual(order.courier_name, '')

    # -------------------------------------------------------------------------
    # 4. Preventing unpaid orders from being dispatched
    # -------------------------------------------------------------------------
    def test_preventing_unpaid_orders_from_being_dispatched(self):
        # Order is unpaid (PENDING payment)
        order = self._create_test_order(
            order_status=Order.OrderStatus.PROCESSING,
            payment_status=Order.PaymentStatus.PENDING
        )
        self.client.force_authenticate(user=self.staff_user)

        res = self.client.patch(
            f"/api/admin/orders/{order.order_reference}/status/",
            data={
                'order_status': 'SHIPPED',
                'courier_name': 'DHL Express',
                'tracking_number': 'DHL123456',
            },
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Cannot dispatch or complete an unpaid order", res.data['detail'])

        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.OrderStatus.PROCESSING)
        self.assertIsNone(order.dispatched_at)

    # -------------------------------------------------------------------------
    # 5. Preserving existing order status-transition rules
    # -------------------------------------------------------------------------
    def test_preserving_existing_order_status_transition_rules(self):
        order = self._create_test_order(order_status=Order.OrderStatus.CONFIRMED)
        self.client.force_authenticate(user=self.staff_user)

        # Cannot skip directly from CONFIRMED to SHIPPED (must go CONFIRMED -> PROCESSING -> SHIPPED)
        res_skip = self.client.patch(
            f"/api/admin/orders/{order.order_reference}/status/",
            data={'order_status': 'SHIPPED'},
            format='json'
        )
        self.assertEqual(res_skip.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid status transition", res_skip.data['detail'])

        # Advance CONFIRMED -> PROCESSING succeeds
        res_proc = self.client.patch(
            f"/api/admin/orders/{order.order_reference}/status/",
            data={'order_status': 'PROCESSING'},
            format='json'
        )
        self.assertEqual(res_proc.status_code, status.HTTP_200_OK)

        # Advance PROCESSING -> SHIPPED with tracking succeeds
        res_ship = self.client.patch(
            f"/api/admin/orders/{order.order_reference}/status/",
            data={
                'order_status': 'SHIPPED',
                'courier_name': 'Evri Next Day',
                'tracking_number': 'EVR883311',
            },
            format='json'
        )
        self.assertEqual(res_ship.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.OrderStatus.SHIPPED)
        self.assertIsNotNone(order.dispatched_at)

    # -------------------------------------------------------------------------
    # 6. Displaying tracking information to the correct customer
    # -------------------------------------------------------------------------
    def test_displaying_tracking_information_to_correct_customer(self):
        order = self._create_test_order(order_status=Order.OrderStatus.SHIPPED)
        order.courier_name = "DPD UK"
        order.tracking_number = "DPD998877"
        order.tracking_url = "https://track.dpd.co.uk/p/DPD998877"
        order.save()

        # Customer who owns the order can access and see tracking
        self.client.force_authenticate(user=self.customer_user)
        res_owner = self.client.get(f"/api/orders/{order.order_reference}/")
        self.assertEqual(res_owner.status_code, status.HTTP_200_OK)
        self.assertEqual(res_owner.data['courier_name'], "DPD UK")
        self.assertEqual(res_owner.data['tracking_number'], "DPD998877")
        self.assertEqual(res_owner.data['tracking_url'], "https://track.dpd.co.uk/p/DPD998877")

        # Customer order list also returns tracking
        res_list = self.client.get("/api/orders/my-orders/")
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        orders = res_list.data.get('results', res_list.data)
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]['courier_name'], "DPD UK")

        # Other customer cannot access the order
        self.client.force_authenticate(user=self.other_customer)
        res_other = self.client.get(f"/api/orders/{order.order_reference}/")
        self.assertEqual(res_other.status_code, status.HTTP_404_NOT_FOUND)

    # -------------------------------------------------------------------------
    # 7. Dispatch emails containing available tracking information
    # -------------------------------------------------------------------------
    def test_dispatch_email_contains_available_tracking_information(self):
        order = self._create_test_order(order_status=Order.OrderStatus.PROCESSING)
        order.courier_name = "Royal Mail 24"
        order.tracking_number = "RM123456789GB"
        order.tracking_url = "https://www.royalmail.com/track-your-item#/tracking-results/RM123456789GB"
        order.save()

        with patch('apps.orders.email_service.send_transactional_email') as mock_send:
            mock_send.return_value = {'success': True, 'provider': 'test'}
            res = send_order_status_update_email(order, Order.OrderStatus.SHIPPED)

            self.assertEqual(res['status'], 'sent')
            self.assertTrue(mock_send.called)

            call_kwargs = mock_send.call_args[1]
            subject = call_kwargs['subject']
            text_body = call_kwargs['text_content']
            html_body = call_kwargs['html_content']

            # Check email content contains courier tracking info
            self.assertIn("AdesHub Order Dispatched", subject)
            self.assertIn("Royal Mail 24", text_body)
            self.assertIn("RM123456789GB", text_body)
            self.assertIn("Royal Mail 24", html_body)
            self.assertIn("RM123456789GB", html_body)
            self.assertIn(order.tracking_url, html_body)

    # -------------------------------------------------------------------------
    # 8. Preventing duplicate notifications
    # -------------------------------------------------------------------------
    def test_preventing_duplicate_notifications(self):
        order = self._create_test_order(order_status=Order.OrderStatus.SHIPPED)
        order.last_status_email_sent = Order.OrderStatus.SHIPPED
        order.save(update_fields=['last_status_email_sent'])

        self.client.force_authenticate(user=self.staff_user)

        with patch('apps.orders.email_service.send_order_status_update_email') as mock_email:
            # Updating courier details while remaining in SHIPPED status
            res = self.client.patch(
                f"/api/admin/orders/{order.order_reference}/status/",
                data={
                    'order_status': 'SHIPPED',
                    'tracking_number': 'UPDATED-TRACK-999',
                },
                format='json'
            )
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            # Duplicate email MUST NOT be sent
            mock_email.assert_not_called()

        # Directly testing send_order_status_update_email idempotency
        email_res = send_order_status_update_email(order, Order.OrderStatus.SHIPPED)
        self.assertEqual(email_res['status'], 'already_sent')
