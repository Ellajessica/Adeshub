from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework.authtoken.models import Token
from apps.accounts.models import User
from .models import Category, Product, ProductVariant, ProductImage


class CategoryModelTests(TestCase):
    """
    Automated tests for Category model.
    """

    def test_category_creation_and_slug_generation(self):
        """Test category creation automatically generates unique slug."""
        category = Category.objects.create(name='Grains & Rice', description='Fresh African grains')
        self.assertEqual(category.name, 'Grains & Rice')
        self.assertEqual(category.slug, 'grains-rice')
        self.assertTrue(category.is_active)

    def test_duplicate_category_name_slug_uniqueness(self):
        """Test slug generation ensures uniqueness even with similar names."""
        cat1 = Category.objects.create(name='Spices')
        cat2 = Category.objects.create(name='Spices!')
        self.assertEqual(cat1.slug, 'spices')
        self.assertNotEqual(cat2.slug, cat1.slug)
        self.assertTrue(cat2.slug.startswith('spices-'))


class ProductModelTests(TestCase):
    """
    Automated tests for Product model.
    """

    def setUp(self):
        self.category = Category.objects.create(name='Tubers', description='Fresh yams and cassava')

    def test_product_creation_and_validation(self):
        """Test product creation with valid attributes."""
        product = Product.objects.create(
            name='Abakaliki Rice 50kg',
            category=self.category,
            sku='RICE-ABK-50KG',
            price=Decimal('45000.00'),
            compare_at_price=Decimal('50000.00'),
            stock_quantity=20,
            is_featured=True
        )
        self.assertEqual(product.slug, 'abakaliki-rice-50kg')
        self.assertEqual(product.category, self.category)
        self.assertEqual(product.total_stock, 20)
        self.assertTrue(product.is_in_stock)
        self.assertFalse(product.is_low_stock)

    def test_negative_price_raises_validation_error(self):
        """Test product creation with negative price raises ValidationError."""
        product = Product(
            name='Invalid Price Item',
            sku='INV-001',
            price=Decimal('-500.00'),
            stock_quantity=10
        )
        with self.assertRaises(ValidationError):
            product.full_clean()

    def test_negative_stock_raises_validation_error(self):
        """Test product creation with negative stock raises ValidationError."""
        product = Product(
            name='Invalid Stock Item',
            sku='INV-002',
            price=Decimal('1000.00'),
            stock_quantity=-5
        )
        with self.assertRaises(ValidationError):
            product.full_clean()


class ProductVariantTests(TestCase):
    """
    Automated tests for Product Variant and inventory behavior.
    """

    def setUp(self):
        self.product = Product.objects.create(
            name='Premium Red Palm Oil',
            sku='PALM-OIL-BASE',
            price=Decimal('3500.00'),
            has_variants=True
        )

    def test_variant_creation_and_stock_aggregation(self):
        """Test variants creation updates product stock calculation."""
        var1 = ProductVariant.objects.create(
            product=self.product,
            name='1 Litre Bottle',
            sku='PALM-OIL-1L',
            price=Decimal('3500.00'),
            stock_quantity=15
        )
        var2 = ProductVariant.objects.create(
            product=self.product,
            name='4 Litre Gallon',
            sku='PALM-OIL-4L',
            price=Decimal('13000.00'),
            stock_quantity=10
        )
        self.assertEqual(self.product.variants.count(), 2)
        self.assertEqual(self.product.total_stock, 25)
        self.assertTrue(self.product.is_in_stock)


class ProductAPITests(APITestCase):
    """
    Automated tests for Catalog REST API endpoints.
    """

    client: APIClient

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Snacks', description='African traditional snacks')
        self.product = Product.objects.create(
            name='Chin Chin Crunchy Snack',
            category=self.category,
            sku='SNACK-CHIN-01',
            price=Decimal('1200.00'),
            stock_quantity=50,
            is_featured=True,
            is_active=True
        )

        self.staff_user = User.objects.create_superuser(
            email='catalogadmin@adeshub.com',
            password='AdminPassword123!'
        )
        self.staff_token, _ = Token.objects.get_or_create(user=self.staff_user)

    def test_public_category_list_api(self):
        """Test public GET /api/categories/ returns active categories."""
        url = reverse('products:category-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data if isinstance(response.data, list) else response.data.get('results', [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'Snacks')

    def test_public_product_list_and_filters_api(self):
        """Test public GET /api/products/ with search and category filters."""
        url = reverse('products:product-list')

        # Baseline list
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

        # Category filter
        response_cat = self.client.get(f"{url}?category={self.category.slug}")
        self.assertEqual(len(response_cat.data['results']), 1)

        # Search filter
        response_search = self.client.get(f"{url}?search=Chin")
        self.assertEqual(len(response_search.data['results']), 1)

    def test_unauthorized_product_creation_fails(self):
        """Test unauthenticated user cannot POST to create a product (401/403)."""
        url = reverse('products:product-list')
        payload = {
            'name': 'Unauthorized Item',
            'sku': 'UNAUTH-01',
            'price': '500.00',
            'stock_quantity': 10
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_product_creation_success(self):
        """Test authorized staff user can create a product via API."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.staff_token.key}')
        url = reverse('products:product-list')
        payload = {
            'name': 'Pounded Yam Flour 5kg',
            'category_id': self.category.id,
            'sku': 'YAM-FLOUR-5KG',
            'price': '7500.00',
            'stock_quantity': 30,
            'is_featured': True
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Pounded Yam Flour 5kg')
        self.assertEqual(response.data['sku'], 'YAM-FLOUR-5KG')

    def test_product_detail_returns_variants_and_description(self):
        """Test GET /api/products/<slug>/ returns full description, images, and variants array."""
        product_with_var = Product.objects.create(
            name='Royal Basmati Rice',
            category=self.category,
            sku='RICE-ROYAL-BASE',
            price=Decimal('5.99'),
            description='Premium aged basmati rice for party Jollof.',
            has_variants=True,
            is_active=True
        )
        var_5kg = ProductVariant.objects.create(
            product=product_with_var,
            name='5kg Bag',
            sku='RICE-ROYAL-5KG',
            price=Decimal('13.99'),
            stock_quantity=15,
            is_active=True
        )
        url = reverse('products:product-detail', kwargs={'slug': product_with_var.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Royal Basmati Rice')
        self.assertEqual(response.data['description'], 'Premium aged basmati rice for party Jollof.')
        self.assertTrue(response.data['has_variants'])
        self.assertEqual(len(response.data['variants']), 1)
        self.assertEqual(response.data['variants'][0]['name'], '5kg Bag')
        self.assertEqual(response.data['variants'][0]['price'], '13.99')
        self.assertEqual(response.data['variants'][0]['stock_quantity'], 15)


class CloudflareR2StorageTests(TestCase):
    """
    Automated unit tests for Cloudflare R2 custom storage backend and URL generation.
    """

    def test_custom_domain_sanitization(self):
        """Test custom domain strips protocol and trailing slashes."""
        from config.storage_backends import CloudflareR2MediaStorage
        storage = CloudflareR2MediaStorage()
        with self.settings(AWS_S3_CUSTOM_DOMAIN='https://pub-abc123xyz.r2.dev/'):
            self.assertEqual(storage.custom_domain, 'pub-abc123xyz.r2.dev')

        with self.settings(AWS_S3_CUSTOM_DOMAIN='http://media.adeshubafricanstore.com'):
            self.assertEqual(storage.custom_domain, 'media.adeshubafricanstore.com')

    def test_r2_storage_attributes(self):
        """Test R2 required attributes (no ACL, s3v4, no overwrite)."""
        from config.storage_backends import CloudflareR2MediaStorage
        self.assertIsNone(CloudflareR2MediaStorage.default_acl)
        self.assertFalse(CloudflareR2MediaStorage.file_overwrite)
        self.assertEqual(CloudflareR2MediaStorage.signature_version, 's3v4')

    def test_querystring_auth_defaults_with_custom_domain(self):
        """Test querystring auth defaults to False when custom domain is set."""
        from config.storage_backends import CloudflareR2MediaStorage
        storage = CloudflareR2MediaStorage()
        with self.settings(AWS_S3_CUSTOM_DOMAIN='pub-abc123xyz.r2.dev'):
            self.assertFalse(storage.querystring_auth)

    def test_image_url_generation_in_serializer(self):
        """Test ProductListSerializer returns valid image URL."""
        from apps.products.serializers import ProductListSerializer
        category = Category.objects.create(name='Flour', slug='flour')
        product = Product.objects.create(
            name='Yam Flour',
            category=category,
            sku='YAM-FLOUR-TEST',
            price=Decimal('10.00'),
            stock_quantity=5
        )
        ProductImage.objects.create(
            product=product,
            image='products/test_yam.png',
            is_primary=True
        )
        serializer = ProductListSerializer(product)
        primary_url = serializer.data['primary_image']
        self.assertIsNotNone(primary_url)
        self.assertTrue('products/test_yam.png' in primary_url)
