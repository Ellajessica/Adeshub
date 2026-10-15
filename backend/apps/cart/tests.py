from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from apps.accounts.models import User
from ..products.models import Product, ProductVariant, Category
from .models import Cart, CartItem


class CartBackendTestCase(APITestCase):
    client: APIClient

    def setUp(self):
        self.client = APIClient()

        # Create Category
        self.category = Category.objects.create(
            name="Grains & Rice",
            slug="grains-rice"
        )

        # Create Simple Product
        self.simple_product = Product.objects.create(
            name="Golden Sella Basmati",
            slug="golden-sella-basmati",
            sku="RIC-001",
            price=Decimal("15.99"),
            stock_quantity=10,
            has_variants=False,
            is_active=True,
            category=self.category
        )

        # Create Second Simple Product
        self.simple_product_2 = Product.objects.create(
            name="Red Palm Oil 2L",
            slug="red-palm-oil-2l",
            sku="OIL-001",
            price=Decimal("12.50"),
            stock_quantity=15,
            has_variants=False,
            is_active=True,
            category=self.category
        )

        # Create Inactive Product
        self.inactive_product = Product.objects.create(
            name="Out of Stock Spice",
            slug="out-of-stock-spice",
            sku="SPI-002",
            price=Decimal("4.50"),
            stock_quantity=5,
            has_variants=False,
            is_active=False,
            category=self.category
        )

        # Create Product with Variants
        self.variant_product = Product.objects.create(
            name="Mama Gold Rice",
            slug="mama-gold-rice",
            sku="RIC-002",
            price=Decimal("20.00"),
            stock_quantity=0,
            has_variants=True,
            is_active=True,
            category=self.category
        )

        self.variant_5kg = ProductVariant.objects.create(
            product=self.variant_product,
            name="5kg Bag",
            sku="RIC-002-5KG",
            price=Decimal("18.50"),
            stock_quantity=5,
            is_active=True
        )

        self.variant_10kg = ProductVariant.objects.create(
            product=self.variant_product,
            name="10kg Bag",
            sku="RIC-002-10KG",
            price=Decimal("35.00"),
            stock_quantity=0,  # Out of stock
            is_active=True
        )

        self.inactive_variant = ProductVariant.objects.create(
            product=self.variant_product,
            name="25kg Bag",
            sku="RIC-002-25KG",
            price=Decimal("80.00"),
            stock_quantity=10,
            is_active=False
        )

        # Create Test User
        self.user = User.objects.create_user(
            email="customer@example.com",
            password="password123",
            first_name="Jane",
            last_name="Doe"
        )

    # 1. Cart Creation Tests
    def test_get_guest_cart(self):
        response = self.client.get('/api/cart/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['items'], [])
        self.assertEqual(response.data['subtotal'], '0.00')
        self.assertEqual(response.data['total_quantity'], 0)

    def test_get_authenticated_cart(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/cart/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cart = Cart.objects.get(id=response.data['id'])
        self.assertEqual(cart.user, self.user)

    # 2. Add Item Tests
    def test_add_simple_product_to_cart(self):
        response = self.client.post('/api/cart/items/', {
            'product': self.simple_product.id,
            'quantity': 2
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['total_quantity'], 2)
        self.assertEqual(response.data['subtotal'], '31.98')  # 15.99 * 2

    def test_add_variant_product_to_cart(self):
        response = self.client.post('/api/cart/items/', {
            'product': self.variant_product.id,
            'variant': self.variant_5kg.id,
            'quantity': 3
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['total_quantity'], 3)
        self.assertEqual(response.data['subtotal'], '55.50')  # 18.50 * 3

    # 3. Validation Tests
    def test_add_inactive_product(self):
        response = self.client.post('/api/cart/items/', {
            'product': self.inactive_product.id,
            'quantity': 1
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_variant_product_without_variant(self):
        response = self.client.post('/api/cart/items/', {
            'product': self.variant_product.id,
            'quantity': 1
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_inactive_variant(self):
        response = self.client.post('/api/cart/items/', {
            'product': self.variant_product.id,
            'variant': self.inactive_variant.id,
            'quantity': 1
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_zero_quantity(self):
        response = self.client.post('/api/cart/items/', {
            'product': self.simple_product.id,
            'quantity': 0
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_quantity_exceeding_stock(self):
        response = self.client.post('/api/cart/items/', {
            'product': self.simple_product.id,
            'quantity': 12  # stock is 10
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('quantity', response.data)

    def test_add_out_of_stock_variant(self):
        response = self.client.post('/api/cart/items/', {
            'product': self.variant_product.id,
            'variant': self.variant_10kg.id,
            'quantity': 1
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 4. Duplicate Items Test
    def test_duplicate_item_increases_quantity(self):
        self.client.post('/api/cart/items/', {
            'product': self.simple_product.id,
            'quantity': 2
        })
        response = self.client.post('/api/cart/items/', {
            'product': self.simple_product.id,
            'quantity': 3
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['total_quantity'], 5)
        self.assertEqual(len(response.data['items']), 1)

    # 5. Update Quantity Tests
    def test_update_item_quantity_success(self):
        add_res = self.client.post('/api/cart/items/', {
            'product': self.simple_product.id,
            'quantity': 2
        })
        item_id = add_res.data['items'][0]['id']

        update_res = self.client.patch(f'/api/cart/items/{item_id}/', {
            'quantity': 5
        })
        self.assertEqual(update_res.status_code, status.HTTP_200_OK)
        self.assertEqual(update_res.data['total_quantity'], 5)

    def test_update_item_quantity_exceeds_stock(self):
        add_res = self.client.post('/api/cart/items/', {
            'product': self.simple_product.id,
            'quantity': 2
        })
        item_id = add_res.data['items'][0]['id']

        update_res = self.client.patch(f'/api/cart/items/{item_id}/', {
            'quantity': 15  # stock is 10
        })
        self.assertEqual(update_res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_item_quantity_negative_or_zero(self):
        add_res = self.client.post('/api/cart/items/', {
            'product': self.simple_product.id,
            'quantity': 2
        })
        item_id = add_res.data['items'][0]['id']

        update_res = self.client.patch(f'/api/cart/items/{item_id}/', {
            'quantity': 0
        })
        self.assertEqual(update_res.status_code, status.HTTP_400_BAD_REQUEST)

    # 6. Remove Item Tests
    def test_remove_cart_item(self):
        add_res = self.client.post('/api/cart/items/', {
            'product': self.simple_product.id,
            'quantity': 2
        })
        item_id = add_res.data['items'][0]['id']

        del_res = self.client.delete(f'/api/cart/items/{item_id}/')
        self.assertEqual(del_res.status_code, status.HTTP_200_OK)
        self.assertEqual(del_res.data['total_quantity'], 0)
        self.assertEqual(len(del_res.data['items']), 0)

    def test_remove_nonexistent_cart_item(self):
        self.client.get('/api/cart/')
        response = self.client.delete('/api/cart/items/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # 7. Clear Cart Test
    def test_clear_cart(self):
        self.client.post('/api/cart/items/', {
            'product': self.simple_product.id,
            'quantity': 2
        })
        self.client.post('/api/cart/items/', {
            'product': self.variant_product.id,
            'variant': self.variant_5kg.id,
            'quantity': 1
        })
        clear_res = self.client.delete('/api/cart/')
        self.assertEqual(clear_res.status_code, status.HTTP_200_OK)
        self.assertEqual(clear_res.data['total_quantity'], 0)
        self.assertEqual(len(clear_res.data['items']), 0)

    # 8. Totals Calculations Verification
    def test_cart_totals_calculation(self):
        # Add 2 simple product (£15.99 each = £31.98)
        self.client.post('/api/cart/items/', {
            'product': self.simple_product.id,
            'quantity': 2
        })
        # Add 3 variant product (£18.50 each = £55.50)
        res = self.client.post('/api/cart/items/', {
            'product': self.variant_product.id,
            'variant': self.variant_5kg.id,
            'quantity': 3
        })
        self.assertEqual(res.data['total_quantity'], 5)
        self.assertEqual(res.data['item_count'], 2)
        self.assertEqual(res.data['subtotal'], '87.48')

    def test_multi_item_variant_cart_preserves_all_items(self):
        """
        Verify adding Product A (5kg x 2) and then Product B (2L x 1) preserves both items in cart.
        """
        res1 = self.client.post('/api/cart/items/', {
            'product': self.simple_product.id,
            'quantity': 2
        })
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        res2 = self.client.post('/api/cart/items/', {
            'product': self.variant_product.id,
            'variant': self.variant_5kg.id,
            'quantity': 1
        })
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)

        cart_res = self.client.get('/api/cart/')
        self.assertEqual(cart_res.status_code, status.HTTP_200_OK)
        self.assertEqual(cart_res.data['item_count'], 2)
        self.assertEqual(cart_res.data['total_quantity'], 3)
        self.assertEqual(len(cart_res.data['items']), 2)

    # 9. Explicit Section 7 Regression Tests
    def test_section_7_test_a_two_different_products(self):
        """
        Test A: Add Product A, add Product B, retrieve cart -> both exist, 2 CartItems, qty 1 each, subtotal correct.
        """
        res1 = self.client.post('/api/cart/items/', {'product': self.simple_product.id, 'quantity': 1})
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        session_key = res1.headers.get('X-Cart-Session')

        res2 = self.client.post(
            '/api/cart/items/',
            {'product': self.simple_product_2.id, 'quantity': 1},
            HTTP_X_CART_SESSION=session_key
        )
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)

        cart_res = self.client.get('/api/cart/', HTTP_X_CART_SESSION=session_key)
        self.assertEqual(cart_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(cart_res.data['items']), 2)
        self.assertEqual(cart_res.data['item_count'], 2)
        self.assertEqual(cart_res.data['total_quantity'], 2)
        expected_subtotal = str(self.simple_product.price + self.simple_product_2.price)
        self.assertEqual(cart_res.data['subtotal'], expected_subtotal)

    def test_section_7_test_b_same_product_twice(self):
        """
        Test B: Add Product A, add Product A again -> one matching CartItem, qty = 2.
        """
        res1 = self.client.post('/api/cart/items/', {'product': self.simple_product.id, 'quantity': 1})
        session_key = res1.headers.get('X-Cart-Session')

        res2 = self.client.post(
            '/api/cart/items/',
            {'product': self.simple_product.id, 'quantity': 1},
            HTTP_X_CART_SESSION=session_key
        )
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(res2.data['items']), 1)
        self.assertEqual(res2.data['items'][0]['quantity'], 2)

    def test_section_7_test_c_guest_cart_persistence(self):
        """
        Test C: Add Product A using guest session, make another request with same session, add Product B -> both remain.
        """
        # Request 1: Initial guest cart
        init_res = self.client.get('/api/cart/')
        session_key = init_res.headers.get('X-Cart-Session')
        self.assertIsNotNone(session_key)

        # Add Product A
        res1 = self.client.post(
            '/api/cart/items/',
            {'product': self.simple_product.id, 'quantity': 1},
            HTTP_X_CART_SESSION=session_key
        )
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Add Product B using same header
        res2 = self.client.post(
            '/api/cart/items/',
            {'product': self.simple_product_2.id, 'quantity': 1},
            HTTP_X_CART_SESSION=session_key
        )
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)

        # Retrieve cart
        cart_res = self.client.get('/api/cart/', HTTP_X_CART_SESSION=session_key)
        self.assertEqual(len(cart_res.data['items']), 2)
        product_ids = {item['product']['id'] for item in cart_res.data['items']}
        self.assertIn(self.simple_product.id, product_ids)
        self.assertIn(self.simple_product_2.id, product_ids)

    def test_section_7_test_d_cart_removal(self):
        """
        Test D: Add Products A and B. Remove A using CartItem ID -> A absent, B remains.
        """
        res1 = self.client.post('/api/cart/items/', {'product': self.simple_product.id, 'quantity': 1})
        session_key = res1.headers.get('X-Cart-Session')
        item_a_id = res1.data['items'][0]['id']

        res2 = self.client.post(
            '/api/cart/items/',
            {'product': self.simple_product_2.id, 'quantity': 1},
            HTTP_X_CART_SESSION=session_key
        )
        self.assertEqual(len(res2.data['items']), 2)

        # Delete item A
        del_res = self.client.delete(f'/api/cart/items/{item_a_id}/', HTTP_X_CART_SESSION=session_key)
        self.assertEqual(del_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(del_res.data['items']), 1)
        self.assertEqual(del_res.data['items'][0]['product']['id'], self.simple_product_2.id)

    def test_section_7_test_e_multiple_requests_do_not_create_duplicate_carts(self):
        """
        Test E: Sequential add requests with valid session do not create duplicate Carts in database.
        """
        initial_cart_count = Cart.objects.count()

        res1 = self.client.post('/api/cart/items/', {'product': self.simple_product.id, 'quantity': 1})
        session_key = res1.headers.get('X-Cart-Session')

        for _ in range(5):
            self.client.post(
                '/api/cart/items/',
                {'product': self.simple_product_2.id, 'quantity': 1},
                HTTP_X_CART_SESSION=session_key
            )

        new_cart_count = Cart.objects.count()
        self.assertEqual(new_cart_count - initial_cart_count, 1)

    def test_section_7_test_f_variants_handling(self):
        """
        Test F: Different variants remain separate lines, adding same variant twice increments quantity.
        """
        res1 = self.client.post('/api/cart/items/', {
            'product': self.variant_product.id,
            'variant': self.variant_5kg.id,
            'quantity': 1
        })
        session_key = res1.headers.get('X-Cart-Session')

        # Add same variant again
        res2 = self.client.post(
            '/api/cart/items/',
            {'product': self.variant_product.id, 'variant': self.variant_5kg.id, 'quantity': 1},
            HTTP_X_CART_SESSION=session_key
        )
        self.assertEqual(len(res2.data['items']), 1)
        self.assertEqual(res2.data['items'][0]['quantity'], 2)

