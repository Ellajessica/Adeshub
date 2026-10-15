from decimal import Decimal
from typing import TYPE_CHECKING
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.products.models import Product, ProductVariant


def generate_order_reference():
    """
    Generate a unique, user-friendly order reference number.
    Example: ADH-20261009-A8F2
    """
    today_str = timezone.now().strftime('%Y%m%d')
    unique_suffix = uuid.uuid4().hex[:6].upper()
    return f"ADH-{today_str}-{unique_suffix}"


class Order(models.Model):
    """
    Order model capturing customer checkout orders, delivery address snapshot,
    monetary totals, fulfillment status, and payment status.
    """
    class OrderStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        PROCESSING = 'PROCESSING', 'Processing'
        SHIPPED = 'SHIPPED', 'Dispatched'
        DELIVERED = 'DELIVERED', 'Delivered'
        CANCELLED = 'CANCELLED', 'Cancelled'

    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending Payment'
        PAID = 'PAID', 'Paid'
        FAILED = 'FAILED', 'Payment Failed'
        REFUNDED = 'REFUNDED', 'Refunded'

    order_reference = models.CharField(
        'Order Reference',
        max_length=60,
        unique=True,
        db_index=True,
        default=generate_order_reference
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Customer'
    )
    guest_email = models.EmailField('Guest Email', blank=True)

    # Address snapshot fields (historical record)
    recipient_name = models.CharField('Recipient Name', max_length=255)
    phone_number = models.CharField('Phone Number', max_length=30)
    address_line1 = models.CharField('Address Line 1', max_length=255)
    address_line2 = models.CharField('Address Line 2', max_length=255, blank=True)
    city = models.CharField('City / Town', max_length=100)
    county_region = models.CharField('County / Region', max_length=100, blank=True)
    postal_code = models.CharField('Postal Code', max_length=20)
    country = models.CharField('Country', max_length=100, default='United Kingdom')

    subtotal = models.DecimalField('Subtotal (£)', max_digits=12, decimal_places=2)
    delivery_fee = models.DecimalField('Delivery Fee (£)', max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField('Total Amount (£)', max_digits=12, decimal_places=2)

    order_status = models.CharField(
        'Order Status',
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.CONFIRMED,
        db_index=True
    )
    payment_status = models.CharField(
        'Payment Status',
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True
    )

    # Delivery & Courier Tracking Fields (courier-ready)
    delivery_method_name = models.CharField(
        'Delivery Method',
        max_length=100,
        default='Standard UK Delivery'
    )
    courier_name = models.CharField(
        'Courier / Provider',
        max_length=100,
        blank=True,
        default=''
    )
    shipment_reference = models.CharField(
        'Shipment Reference',
        max_length=100,
        blank=True,
        default=''
    )
    tracking_number = models.CharField(
        'Tracking Number',
        max_length=100,
        blank=True,
        default=''
    )
    tracking_url = models.URLField(
        'Tracking URL',
        max_length=500,
        blank=True,
        default=''
    )
    dispatched_at = models.DateTimeField(
        'Dispatched At',
        null=True,
        blank=True
    )
    delivered_at = models.DateTimeField(
        'Delivered At',
        null=True,
        blank=True
    )

    notes = models.TextField('Order Notes', blank=True)
    stripe_checkout_session_id = models.CharField(
        'Stripe Checkout Session ID',
        max_length=255,
        blank=True,
        null=True,
        db_index=True
    )
    stripe_payment_intent_id = models.CharField(
        'Stripe Payment Intent ID',
        max_length=255,
        blank=True,
        null=True,
        db_index=True
    )
    confirmation_email_sent = models.BooleanField(
        'Confirmation Email Sent',
        default=False,
        db_index=True
    )
    confirmation_email_sent_at = models.DateTimeField(
        'Confirmation Email Sent At',
        null=True,
        blank=True
    )
    email_delivery_status = models.CharField(
        'Email Delivery Status',
        max_length=50,
        default='PENDING',
        db_index=True
    )
    last_status_email_sent = models.CharField(
        'Last Status Email Sent',
        max_length=50,
        blank=True,
        default=''
    )
    inventory_restored = models.BooleanField(
        'Inventory Restored',
        default=False,
        db_index=True,
        help_text='Indicates whether reserved stock was restored upon cancellation or expiration.'
    )
    inventory_restored_at = models.DateTimeField(
        'Inventory Restored At',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField('Created At', auto_now_add=True)
    updated_at = models.DateTimeField('Updated At', auto_now=True)

    objects = models.Manager()

    if TYPE_CHECKING:
        items: models.Manager

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.order_reference} ({self.get_order_status_display()})"


class DeliveryMethod(models.Model):
    """
    Configurable delivery methods and shipping fee rules.
    Allows store administrators to manage active delivery methods, base fees,
    optional free-delivery thresholds, and transit time estimates.
    """
    name = models.CharField('Method Name', max_length=100, default='Standard UK Delivery')
    code = models.SlugField('Method Code', max_length=50, unique=True, default='standard')
    description = models.CharField('Description', max_length=255, blank=True, default='Delivered in 2-3 business days')
    base_fee = models.DecimalField('Base Delivery Fee (£)', max_digits=6, decimal_places=2, default=Decimal('3.99'))
    free_delivery_threshold = models.DecimalField(
        'Free Delivery Threshold (£)',
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Order subtotal at which delivery becomes free. Leave blank if no free delivery applies.'
    )
    estimated_days = models.CharField('Estimated Transit Time', max_length=100, default='2-3 business days')
    is_active = models.BooleanField('Is Active', default=True, db_index=True)
    is_default = models.BooleanField('Is Default Method', default=True)
    display_order = models.PositiveIntegerField('Display Order', default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'id']
        verbose_name = 'Delivery Method'
        verbose_name_plural = 'Delivery Methods'

    def __str__(self):
        threshold_str = f" (Free over £{self.free_delivery_threshold})" if self.free_delivery_threshold else ""
        return f"{self.name} - £{self.base_fee}{threshold_str}"

    def calculate_fee(self, subtotal: Decimal) -> Decimal:
        """Calculate authoritative delivery fee for a given subtotal."""
        if self.free_delivery_threshold is not None and subtotal >= self.free_delivery_threshold:
            return Decimal('0.00')
        return self.base_fee



class OrderItem(models.Model):
    """
    OrderItem model preserving historical product, variant, pricing, and line totals.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Order'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items',
        verbose_name='Product'
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items',
        verbose_name='Product Variant'
    )

    # Snapshot fields
    product_name = models.CharField('Product Name', max_length=255)
    variant_name = models.CharField('Variant Name', max_length=150, blank=True)
    sku = models.CharField('SKU', max_length=100, blank=True)
    unit_price = models.DecimalField('Unit Price (£)', max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField('Quantity')
    line_total = models.DecimalField('Line Total (£)', max_digits=12, decimal_places=2)

    created_at = models.DateTimeField('Created At', auto_now_add=True)

    objects = models.Manager()

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
        ordering = ['id']

    def __str__(self):
        variant_str = f" ({self.variant_name})" if self.variant_name else ""
        return f"{self.quantity}x {self.product_name}{variant_str}"
