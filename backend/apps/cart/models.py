from decimal import Decimal
from typing import TYPE_CHECKING
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from ..products.models import Product, ProductVariant


class Cart(models.Model):
    """
    Cart model supporting both guest session customers and authenticated users.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='carts',
        verbose_name='User'
    )
    session_key = models.CharField(
        'Session Key',
        max_length=255,
        blank=True,
        null=True,
        db_index=True
    )
    created_at = models.DateTimeField('Created At', auto_now_add=True)
    updated_at = models.DateTimeField('Updated At', auto_now=True)

    objects = models.Manager()

    if TYPE_CHECKING:
        items: models.Manager

    class Meta:
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'
        ordering = ['-updated_at']

    def __str__(self):
        if self.user:
            return f"Cart {self.id} (User: {self.user.email})"
        return f"Cart {self.id} (Guest Session: {self.session_key})"

    @property
    def subtotal(self) -> Decimal:
        """
        Dynamically calculate cart subtotal using valid product/variant prices.
        """
        total = Decimal('0.00')
        for item in self.items.all():
            total += item.line_total
        return total

    @property
    def total_quantity(self) -> int:
        """
        Total item quantity across all cart lines.
        """
        aggregate = self.items.aggregate(total=Sum('quantity'))
        return aggregate['total'] or 0

    @property
    def item_count(self) -> int:
        """
        Number of distinct cart lines.
        """
        return self.items.count()


class CartItem(models.Model):
    """
    CartItem model representing a single product/variant line in a cart.
    """
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Cart'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='cart_items',
        verbose_name='Product'
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cart_items',
        verbose_name='Product Variant'
    )
    quantity = models.PositiveIntegerField(
        'Quantity',
        default=1,
        validators=[MinValueValidator(1)]
    )
    created_at = models.DateTimeField('Created At', auto_now_add=True)
    updated_at = models.DateTimeField('Updated At', auto_now=True)

    objects = models.Manager()

    class Meta:
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        ordering = ['created_at']
        unique_together = ('cart', 'product', 'variant')
        constraints = [
            models.CheckConstraint(
                check=Q(quantity__gt=0),
                name='cart_item_quantity_positive'
            ),
        ]

    def __str__(self):
        variant_str = f" ({self.variant.name})" if self.variant else ""
        return f"{self.quantity}x {self.product.name}{variant_str}"

    @property
    def unit_price(self) -> Decimal:
        """
        Get current unit price from product or variant (source of truth).
        """
        if self.variant:
            return self.variant.price
        return self.product.price

    @property
    def line_total(self) -> Decimal:
        """
        Calculate total for this cart item line.
        """
        return self.unit_price * Decimal(self.quantity)

    @property
    def available_stock(self) -> int:
        """
        Get current available stock for product or variant.
        """
        if self.variant:
            return self.variant.stock_quantity
        return self.product.stock_quantity

    def clean(self):
        super().clean()
        if self.quantity is not None and self.quantity < 1:
            raise ValidationError({'quantity': 'Quantity must be at least 1.'})

        if self.product:
            if not self.product.is_active:
                raise ValidationError({'product': f"Product '{self.product.name}' is currently unavailable."})

            if self.product.has_variants and not self.variant:
                raise ValidationError({'variant': f"Please select a variant for '{self.product.name}'."})

            if self.variant:
                if self.variant.product_id != self.product.id:
                    raise ValidationError({'variant': f"Selected variant does not belong to product '{self.product.name}'."})
                if not self.variant.is_active:
                    raise ValidationError({'variant': f"Variant '{self.variant.name}' is currently unavailable."})

            stock = self.available_stock
            if stock <= 0:
                raise ValidationError({'quantity': f"'{self.product.name}' is currently out of stock."})
            if self.quantity > stock:
                raise ValidationError({'quantity': f"Requested quantity ({self.quantity}) exceeds available stock ({stock})."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
