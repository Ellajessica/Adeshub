from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Order, OrderItem, DeliveryMethod


@admin.register(DeliveryMethod)
class DeliveryMethodAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'code',
        'base_fee',
        'free_delivery_threshold',
        'estimated_days',
        'is_active',
        'is_default',
        'display_order',
    )
    list_editable = ('base_fee', 'free_delivery_threshold', 'is_active', 'is_default')
    search_fields = ('name', 'code', 'description')
    ordering = ('display_order', 'id')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        'product',
        'variant',
        'product_name',
        'variant_name',
        'sku',
        'unit_price',
        'quantity',
        'line_total',
        'created_at',
    )
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display: tuple[str, ...] = (
        'order_reference',
        'get_customer',
        'recipient_name',
        'total_amount',
        'order_status',
        'payment_status',
        'courier_name',
        'tracking_number',
        'created_at',
    )
    list_filter = ('order_status', 'payment_status', 'inventory_restored', 'courier_name', 'created_at', 'country')
    search_fields = (
        'order_reference',
        'user__email',
        'recipient_name',
        'postal_code',
        'phone_number',
        'tracking_number',
        'shipment_reference',
    )
    readonly_fields = (
        'order_reference',
        'subtotal',
        'delivery_fee',
        'total_amount',
        'stripe_checkout_session_id',
        'stripe_payment_intent_id',
        'confirmation_email_sent',
        'confirmation_email_sent_at',
        'email_delivery_status',
        'inventory_restored',
        'inventory_restored_at',
        'created_at',
        'updated_at',
    )
    inlines: tuple[type[admin.TabularInline], ...] = (OrderItemInline,)

    fieldsets = (
        ('Order Reference & Status', {
            'fields': ('order_reference', 'order_status', 'payment_status', 'notes')
        }),
        ('Inventory Lifecycle', {
            'fields': ('inventory_restored', 'inventory_restored_at')
        }),
        ('Courier & Shipment Tracking', {
            'fields': (
                'delivery_method_name',
                'courier_name',
                'shipment_reference',
                'tracking_number',
                'tracking_url',
                'dispatched_at',
                'delivered_at',
            )
        }),
        ('Email Notifications', {
            'fields': ('confirmation_email_sent', 'confirmation_email_sent_at', 'email_delivery_status'),
        }),
        ('Stripe Payment Gateway Details', {
            'fields': ('stripe_checkout_session_id', 'stripe_payment_intent_id'),
            'classes': ('collapse',),
        }),
        ('Customer Info', {
            'fields': ('user', 'guest_email')
        }),
        ('Delivery Address Snapshot', {
            'fields': (
                'recipient_name',
                'phone_number',
                'address_line1',
                'address_line2',
                'city',
                'county_region',
                'postal_code',
                'country',
            )
        }),
        ('Monetary Totals', {
            'fields': ('subtotal', 'delivery_fee', 'total_amount')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    @admin.display(description='Customer')
    def get_customer(self, obj):
        if obj.user:
            return obj.user.email
        return f"{obj.recipient_name} (Guest)"

    def save_model(self, request, obj, form, change):
        old_status = None
        if change and 'order_status' in form.changed_data:
            old_order = Order.objects.filter(pk=obj.pk).values('order_status').first()
            if old_order:
                old_status = old_order['order_status']

        # Guard: Unpaid order cannot be dispatched
        if obj.order_status in (Order.OrderStatus.SHIPPED, Order.OrderStatus.DELIVERED):
            if obj.payment_status != Order.PaymentStatus.PAID:
                raise ValidationError(
                    f"Cannot mark order as {obj.get_order_status_display()} while payment is unpaid ({obj.get_payment_status_display()})."
                )

        now = timezone.now()
        if obj.order_status == Order.OrderStatus.SHIPPED and not obj.dispatched_at:
            obj.dispatched_at = now
        elif obj.order_status == Order.OrderStatus.DELIVERED and not obj.delivered_at:
            obj.delivered_at = now

        super().save_model(request, obj, form, change)

        if change and old_status and obj.order_status != old_status:
            # Restore inventory if an eligible unpaid order was cancelled via Django Admin
            if obj.order_status == Order.OrderStatus.CANCELLED:
                if obj.payment_status != Order.PaymentStatus.PAID and not obj.inventory_restored:
                    from .inventory_service import restore_order_inventory
                    restore_order_inventory(
                        order=obj,
                        reason=f"Django Admin cancellation by {request.user}",
                        target_order_status=None
                    )

            if obj.order_status in (Order.OrderStatus.SHIPPED, Order.OrderStatus.DELIVERED, Order.OrderStatus.CANCELLED):
                from .email_service import send_order_status_update_email_async
                send_order_status_update_email_async(obj.id, obj.order_status)

