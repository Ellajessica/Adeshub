import logging
from typing import Optional, Any
from django.db import transaction
from django.utils import timezone
from apps.products.models import Product, ProductVariant
from .models import Order

logger = logging.getLogger(__name__)


def restore_order_inventory(
    order: Order,
    reason: str = "",
    target_order_status: Optional[str] = Order.OrderStatus.CANCELLED,
    target_payment_status: Optional[str] = None
) -> dict[str, Any]:
    """
    Restore reserved inventory for an eligible unpaid order exactly once.
    Concurrency-safe and idempotent.

    Safety rules enforced:
    1. Wrapped in database atomic transaction.
    2. Uses select_for_update() row lock on Order to prevent concurrent restorations.
    3. Never restores stock twice (checks order.inventory_restored).
    4. Never restores stock for an order that has completed payment (payment_status == PAID).
    5. Never restores stock if order is already fulfilled/dispatched/delivered.
    6. Uses select_for_update() on ProductVariant and Product, ordered by ID to prevent deadlocks.
    7. Atomically records inventory_restored=True and inventory_restored_at timestamp.
    8. Any failure rolls back the entire transaction without leaving partially restored inventory.
    """
    with transaction.atomic():
        # Lock the order row to serialize concurrent webhook or admin operations
        locked_order = Order.objects.select_for_update().get(pk=order.pk)

        # Rule 1: Idempotency check - already restored?
        if locked_order.inventory_restored:
            logger.info(
                "Order %s inventory has already been restored at %s. Skipping duplicate restoration. Reason: %s",
                locked_order.order_reference,
                locked_order.inventory_restored_at,
                reason or "unspecified"
            )
            return {
                'restored': False,
                'status': 'already_restored',
                'order_reference': locked_order.order_reference,
                'message': 'Inventory for this order has already been restored.'
            }

        # Rule 2: Payment safety - never restore stock for paid orders!
        if locked_order.payment_status == Order.PaymentStatus.PAID:
            logger.warning(
                "Refusing inventory restoration for paid order %s (payment_status=PAID). Reason: %s",
                locked_order.order_reference,
                reason or "unspecified"
            )
            return {
                'restored': False,
                'status': 'payment_already_paid',
                'order_reference': locked_order.order_reference,
                'message': 'Cannot restore inventory for an order that has completed payment.'
            }

        # Rule 3: Fulfillment check - do not restock if dispatched or delivered
        if locked_order.order_status in (Order.OrderStatus.SHIPPED, Order.OrderStatus.DELIVERED):
            logger.warning(
                "Refusing inventory restoration for order %s because it is already %s.",
                locked_order.order_reference,
                locked_order.order_status
            )
            return {
                'restored': False,
                'status': 'order_already_fulfilled',
                'order_reference': locked_order.order_reference,
                'message': f'Cannot restore inventory for an order that is {locked_order.order_status}.'
            }

        # Rule 4: Restore stock for all items
        # Sort items deterministically by ID to prevent database deadlocks under concurrency
        items = list(locked_order.items.select_related('product', 'variant').order_by('id'))
        restored_items_summary: list[str] = []

        for item in items:
            qty = item.quantity
            if qty <= 0:
                continue

            if item.variant_id:
                variant = ProductVariant.objects.select_for_update().filter(pk=item.variant_id).first()
                if variant:
                    variant.stock_quantity += qty
                    variant.save(update_fields=['stock_quantity', 'updated_at'])
                    restored_items_summary.append(
                        f"{qty}x {variant.name} (SKU: {variant.sku})"
                    )
                elif item.product_id:
                    # Fallback if variant row was removed but parent product remains
                    product = Product.objects.select_for_update().filter(pk=item.product_id).first()
                    if product:
                        product.stock_quantity += qty
                        product.save(update_fields=['stock_quantity', 'updated_at'])
                        restored_items_summary.append(
                            f"{qty}x {product.name} (SKU: {product.sku})"
                        )
            elif item.product_id:
                product = Product.objects.select_for_update().filter(pk=item.product_id).first()
                if product:
                    product.stock_quantity += qty
                    product.save(update_fields=['stock_quantity', 'updated_at'])
                    restored_items_summary.append(
                        f"{qty}x {product.name} (SKU: {product.sku})"
                    )

        # Rule 5: Mark order as restored and update status
        now = timezone.now()
        locked_order.inventory_restored = True
        locked_order.inventory_restored_at = now
        update_fields = ['inventory_restored', 'inventory_restored_at', 'updated_at']

        if target_order_status is not None:
            locked_order.order_status = target_order_status
            update_fields.append('order_status')

        if target_payment_status is not None:
            locked_order.payment_status = target_payment_status
            update_fields.append('payment_status')

        locked_order.save(update_fields=list(set(update_fields)))

        logger.info(
            "Successfully restored inventory for order %s (%d items restored). Reason: %s",
            locked_order.order_reference,
            len(restored_items_summary),
            reason or "unspecified"
        )

        return {
            'restored': True,
            'status': 'success',
            'order_reference': locked_order.order_reference,
            'items_restored': restored_items_summary,
            'order_status': locked_order.order_status,
            'payment_status': locked_order.payment_status,
            'inventory_restored_at': now.isoformat(),
        }
