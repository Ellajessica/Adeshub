from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.products.models import Category, Product, ProductVariant


class Command(BaseCommand):
    help = 'Seeds clean, realistic sample African grocery data with variants for storefront testing.'

    def handle(self, *args, **options):
        self.stdout.write('Seeding sample catalog data with variants and simple products...')

        # Categories
        cat_grains, _ = Category.objects.get_or_create(
            name='Grains & Flour',
            defaults={
                'description': 'African staples including Basmati rice, Ijebu Garri, Yam Flour (Elubo), and Plantain Flour.',
                'is_active': True
            }
        )

        cat_oil, _ = Category.objects.get_or_create(
            name='Oils & Seasonings',
            defaults={
                'description': 'Unrefined Red Palm Oil, Vegetable Oil, Knorr Cubes, and Suya Spice mixtures.',
                'is_active': True
            }
        )

        cat_tubers, _ = Category.objects.get_or_create(
            name='Fresh Produce & Tubers',
            defaults={
                'description': 'Fresh Pona Yams, Sweet Potatoes, Plantains, and Bitter Leaf.',
                'is_active': True
            }
        )

        # 1. Royal Basmati Rice (Variant Product)
        p1, _ = Product.objects.update_or_create(
            sku='SMPL-RICE-01',
            defaults={
                'name': 'Royal Basmati Rice',
                'category': cat_grains,
                'price': Decimal('5.99'),
                'compare_at_price': Decimal('6.99'),
                'stock_quantity': 0,
                'has_variants': True,
                'is_featured': True,
                'is_active': True,
                'description': 'Premium long-grain Basmati rice, aged and polished for rich aroma and fluffy texture. Ideal for traditional party Jollof rice, fried rice, and white rice dishes.'
            }
        )
        ProductVariant.objects.update_or_create(
            product=p1,
            name='2kg Bag',
            defaults={
                'sku': 'SMPL-RICE-2KG',
                'price': Decimal('5.99'),
                'compare_at_price': Decimal('6.99'),
                'stock_quantity': 20,
                'is_active': True
            }
        )
        ProductVariant.objects.update_or_create(
            product=p1,
            name='5kg Bag',
            defaults={
                'sku': 'SMPL-RICE-5KG',
                'price': Decimal('13.99'),
                'compare_at_price': Decimal('15.50'),
                'stock_quantity': 15,
                'is_active': True
            }
        )
        ProductVariant.objects.update_or_create(
            product=p1,
            name='10kg Bag',
            defaults={
                'sku': 'SMPL-RICE-10KG',
                'price': Decimal('26.99'),
                'compare_at_price': Decimal('29.99'),
                'stock_quantity': 10,
                'is_active': True
            }
        )

        # 2. Ijebu White Garri (Variant Product)
        p2, _ = Product.objects.update_or_create(
            sku='SMPL-GARRI-01',
            defaults={
                'name': 'Ijebu White Garri',
                'category': cat_grains,
                'price': Decimal('2.99'),
                'compare_at_price': Decimal('3.49'),
                'stock_quantity': 0,
                'has_variants': True,
                'is_featured': True,
                'is_active': True,
                'description': 'Crispy, pleasantly sour Ijebu garri processed from finest cassava tubers. Milled finely for drinking with cold water and groundnuts, or making firm smooth Eba.'
            }
        )
        ProductVariant.objects.update_or_create(
            product=p2,
            name='1kg Bag',
            defaults={
                'sku': 'SMPL-GARRI-1KG',
                'price': Decimal('2.99'),
                'compare_at_price': Decimal('3.49'),
                'stock_quantity': 25,
                'is_active': True
            }
        )
        ProductVariant.objects.update_or_create(
            product=p2,
            name='2kg Bag',
            defaults={
                'sku': 'SMPL-GARRI-2KG',
                'price': Decimal('5.49'),
                'compare_at_price': Decimal('6.20'),
                'stock_quantity': 20,
                'is_active': True
            }
        )
        ProductVariant.objects.update_or_create(
            product=p2,
            name='5kg Bag',
            defaults={
                'sku': 'SMPL-GARRI-5KG',
                'price': Decimal('12.50'),
                'compare_at_price': Decimal('14.00'),
                'stock_quantity': 10,
                'is_active': True
            }
        )

        # 3. Pure Red Palm Oil (Variant Product)
        p3, _ = Product.objects.update_or_create(
            sku='SMPL-PALM-01',
            defaults={
                'name': 'Pure Red Palm Oil',
                'category': cat_oil,
                'price': Decimal('4.50'),
                'compare_at_price': Decimal('5.20'),
                'stock_quantity': 0,
                'has_variants': True,
                'is_featured': True,
                'is_active': True,
                'description': '100% natural, unrefined red palm oil extracted directly from ripe oil palm fruit. Adds authentic flavor, rich aroma, and natural color to Egusi, Ogbono, and Banga soups.'
            }
        )
        ProductVariant.objects.update_or_create(
            product=p3,
            name='1L Bottle',
            defaults={
                'sku': 'SMPL-PALM-1L',
                'price': Decimal('4.50'),
                'compare_at_price': Decimal('5.20'),
                'stock_quantity': 30,
                'is_active': True
            }
        )
        ProductVariant.objects.update_or_create(
            product=p3,
            name='2L Bottle',
            defaults={
                'sku': 'SMPL-PALM-2L',
                'price': Decimal('8.50'),
                'compare_at_price': Decimal('9.99'),
                'stock_quantity': 18,
                'is_active': True
            }
        )
        ProductVariant.objects.update_or_create(
            product=p3,
            name='5L Container',
            defaults={
                'sku': 'SMPL-PALM-5L',
                'price': Decimal('19.99'),
                'compare_at_price': Decimal('22.50'),
                'stock_quantity': 8,
                'is_active': True
            }
        )

        # 4. Fresh Pona Yam Tubers (Simple Product - NO VARIANTS)
        Product.objects.update_or_create(
            sku='SMPL-YAM-01',
            defaults={
                'name': 'Fresh Pona Yam Tubers',
                'category': cat_tubers,
                'price': Decimal('6.50'),
                'compare_at_price': Decimal('7.50'),
                'stock_quantity': 12,
                'has_variants': False,
                'is_featured': False,
                'is_active': True,
                'description': 'Freshly harvested Pona white yam tubers. Naturally sweet and dry, perfect for authentic Pounded Yam, boiled yam with egg sauce, or crispy fried yam.'
            }
        )

        # 5. Suya Seasoning Mix (Simple Product - NO VARIANTS)
        Product.objects.update_or_create(
            sku='SMPL-SUYA-01',
            defaults={
                'name': 'Authentic Suya Seasoning Mix',
                'category': cat_oil,
                'price': Decimal('3.99'),
                'compare_at_price': Decimal('4.50'),
                'stock_quantity': 40,
                'has_variants': False,
                'is_featured': False,
                'is_active': True,
                'description': 'Traditional Hausa Yaji suya spice blend crafted from roasted kuli-kuli (peanuts), ginger, chili peppers, and aromatic spices. Brings authentic street suya flavor to grilled meats.'
            }
        )

        # 6. Whole Egusi Seeds (Variant Product)
        p6, _ = Product.objects.update_or_create(
            sku='SMPL-EGUSI-01',
            defaults={
                'name': 'Whole Egusi Seeds (Melon)',
                'category': cat_grains,
                'price': Decimal('4.99'),
                'compare_at_price': Decimal('5.50'),
                'stock_quantity': 0,
                'has_variants': True,
                'is_featured': False,
                'is_active': True,
                'description': 'Hand-picked whole melon seeds (Egusi), cleaned and ready for grinding. Essential staple ingredient for preparing rich, flavorful Nigerian Egusi soup.'
            }
        )
        ProductVariant.objects.update_or_create(
            product=p6,
            name='500g Pack',
            defaults={
                'sku': 'SMPL-EGUSI-500G',
                'price': Decimal('4.99'),
                'compare_at_price': Decimal('5.50'),
                'stock_quantity': 15,
                'is_active': True
            }
        )
        ProductVariant.objects.update_or_create(
            product=p6,
            name='1kg Pack',
            defaults={
                'sku': 'SMPL-EGUSI-1KG',
                'price': Decimal('8.99'),
                'compare_at_price': Decimal('9.99'),
                'stock_quantity': 10,
                'is_active': True
            }
        )

        self.stdout.write(self.style.SUCCESS('Successfully seeded sample development catalog data with variants and simple products!'))
