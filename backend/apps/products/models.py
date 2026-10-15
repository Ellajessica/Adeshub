from decimal import Decimal
from django.db import models
from django.db.models import Q, Sum
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils.text import slugify


def generate_unique_slug(model_instance, slugable_field_name, slug_field_name='slug'):
    """
    Utility helper to generate a unique slug for a given model instance.
    """
    slug_field = model_instance._meta.get_field(slug_field_name)
    slug_len = slug_field.max_length

    raw_value = getattr(model_instance, slugable_field_name)
    base_slug = slugify(raw_value)[:slug_len - 15] if raw_value else 'item'
    if not base_slug:
        base_slug = 'item'

    slug = base_slug
    model_class = model_instance.__class__
    counter = 1

    while model_class.objects.filter(**{slug_field_name: slug}).exclude(pk=model_instance.pk).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


class Category(models.Model):
    """
    Category model for organizing products in AdesHub.
    """
    name = models.CharField('Category Name', max_length=150, unique=True, db_index=True)
    slug = models.SlugField('Category Slug', max_length=170, unique=True, blank=True, db_index=True)
    description = models.TextField('Description', blank=True)
    image = models.ImageField('Category Image', upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField('Active Status', default=True, db_index=True)

    created_at = models.DateTimeField('Created At', auto_now_add=True)
    updated_at = models.DateTimeField('Updated At', auto_now=True)

    objects = models.Manager()

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, 'name')
        super().save(*args, **kwargs)


class Product(models.Model):
    """
    Product model representing e-commerce items.
    Supports simple products and products with variants.
    """
    name = models.CharField('Product Name', max_length=255, db_index=True)
    slug = models.SlugField('Product Slug', max_length=280, unique=True, blank=True, db_index=True)
    description = models.TextField('Description', blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='Category'
    )
    sku = models.CharField('SKU', max_length=100, unique=True, db_index=True, help_text='Unique Stock Keeping Unit')

    price = models.DecimalField(
        'Price (₦)',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    compare_at_price = models.DecimalField(
        'Compare At Price (₦)',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Original or strike-through price if on sale'
    )

    stock_quantity = models.IntegerField(
        'Stock Quantity',
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Stock quantity for simple products without variants'
    )
    low_stock_threshold = models.IntegerField(
        'Low Stock Threshold',
        default=5,
        validators=[MinValueValidator(0)]
    )

    has_variants = models.BooleanField(
        'Has Variants',
        default=False,
        help_text='Check if product has variants (e.g., 5kg, 10kg, 25kg)'
    )
    is_active = models.BooleanField('Active Status', default=True, db_index=True)
    is_featured = models.BooleanField('Featured Product', default=False, db_index=True)

    created_at = models.DateTimeField('Created At', auto_now_add=True)
    updated_at = models.DateTimeField('Updated At', auto_now=True)

    objects = models.Manager()

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=Q(price__gte=0),
                name='product_price_non_negative'
            ),
            models.CheckConstraint(
                check=Q(stock_quantity__gte=0),
                name='product_stock_non_negative'
            ),
            models.CheckConstraint(
                check=Q(low_stock_threshold__gte=0),
                name='product_low_stock_non_negative'
            ),
            models.CheckConstraint(
                check=Q(compare_at_price__isnull=True) | Q(compare_at_price__gte=0),
                name='product_compare_price_non_negative'
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.price is not None and self.price < Decimal('0.00'):
            raise ValidationError({'price': 'Price cannot be negative.'})
        if self.compare_at_price is not None and self.compare_at_price < Decimal('0.00'):
            raise ValidationError({'compare_at_price': 'Compare at price cannot be negative.'})
        if self.stock_quantity is not None and self.stock_quantity < 0:
            raise ValidationError({'stock_quantity': 'Stock quantity cannot be negative.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.slug:
            self.slug = generate_unique_slug(self, 'name')
        super().save(*args, **kwargs)

    @property
    def primary_image(self):
        img = self.images.filter(is_primary=True).first()
        if not img:
            img = self.images.first()
        return img

    @property
    def total_stock(self):
        if self.has_variants:
            aggregate = self.variants.filter(is_active=True).aggregate(total=Sum('stock_quantity'))
            return aggregate['total'] or 0
        return self.stock_quantity

    @property
    def is_in_stock(self):
        return self.total_stock > 0

    @property
    def is_low_stock(self):
        return 0 < self.total_stock <= self.low_stock_threshold

    @property
    def has_active_variants(self):
        return self.has_variants and self.variants.filter(is_active=True).exists()



class ProductVariant(models.Model):
    """
    ProductVariant model for specific product options (e.g., 5kg bag, 1L bottle).
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name='Product'
    )
    name = models.CharField('Variant Name', max_length=150, help_text="e.g., '5kg Bag', '1 Litre'")
    sku = models.CharField('Variant SKU', max_length=100, unique=True, db_index=True)
    price = models.DecimalField(
        'Price (₦)',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    compare_at_price = models.DecimalField(
        'Compare At Price (₦)',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    stock_quantity = models.IntegerField(
        'Stock Quantity',
        default=0,
        validators=[MinValueValidator(0)]
    )
    is_active = models.BooleanField('Active Status', default=True, db_index=True)

    created_at = models.DateTimeField('Created At', auto_now_add=True)
    updated_at = models.DateTimeField('Updated At', auto_now=True)

    objects = models.Manager()

    class Meta:
        verbose_name = 'Product Variant'
        verbose_name_plural = 'Product Variants'
        unique_together = ('product', 'name')
        ordering = ['name']
        constraints = [
            models.CheckConstraint(
                check=Q(price__gte=0),
                name='variant_price_non_negative'
            ),
            models.CheckConstraint(
                check=Q(stock_quantity__gte=0),
                name='variant_stock_non_negative'
            ),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.name}"

    def clean(self):
        super().clean()
        if self.price is not None and self.price < Decimal('0.00'):
            raise ValidationError({'price': 'Variant price cannot be negative.'})
        if self.stock_quantity is not None and self.stock_quantity < 0:
            raise ValidationError({'stock_quantity': 'Variant stock quantity cannot be negative.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_in_stock(self):
        return self.stock_quantity > 0


class ProductImage(models.Model):
    """
    ProductImage model for supporting multiple product images and primary image selection.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Product'
    )
    image = models.ImageField('Image File', upload_to='products/')
    alt_text = models.CharField('Alt Text', max_length=255, blank=True)
    is_primary = models.BooleanField('Primary Image', default=False)
    display_order = models.PositiveIntegerField('Display Order', default=0)

    created_at = models.DateTimeField('Created At', auto_now_add=True)

    class Meta:
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'
        ordering = ['display_order', 'id']

    def __str__(self):
        return f"Image for {self.product.name}"

    def save(self, *args, **kwargs):
        if self.is_primary:
            # Unset primary flag on other images for this product
            ProductImage.objects.filter(product=self.product, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
