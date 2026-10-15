from datetime import timedelta
import logging
from typing import Any
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
import stripe

from apps.orders.models import Order
from apps.orders.inventory_service import restore_order_inventory
from apps.orders.stripe_service import (
    is_stripe_configured,
    get_stripe_secret_key,
    _handle_checkout_session_completed,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Find stale unpaid orders, safely verify their Stripe payment status, "
        "and restore reserved inventory exactly once."
    )

    def add_arguments(self, parser):
        default_timeout = getattr(settings, 'ABANDONED_ORDER_TIMEOUT_MINUTES', 60)
        parser.add_argument(
            '--timeout-minutes',
            type=int,
            default=default_timeout,
            help=f"Age in minutes after which unpaid pending orders are considered abandoned (default: {default_timeout}).",
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help="Simulate cleanup without updating database or restoring inventory.",
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help="Maximum number of abandoned orders to process in one execution (default: 100).",
        )
        parser.add_argument(
            '--skip-stripe-check',
            action='store_true',
            default=False,
            help="Skip remote Stripe API verification of checkout session status.",
        )

    def handle(self, *args, **options: Any):
        timeout_minutes = options['timeout_minutes']
        dry_run = options['dry_run']
        limit = options['limit']
        skip_stripe_check = options['skip_stripe_check']

        if timeout_minutes < 1:
            self.stderr.write(self.style.ERROR("Timeout minutes must be at least 1."))
            return

        now = timezone.now()
        cutoff_time = now - timedelta(minutes=timeout_minutes)

        self.stdout.write(
            f"Scanning for abandoned unpaid orders created before {cutoff_time.strftime('%Y-%m-%d %H:%M:%S UTC')} "
            f"(threshold: {timeout_minutes} minutes)..."
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE: No database changes will be committed."))

        # 1. Query candidate orders:
        # Strictly select only UNPAID (PENDING), non-terminal orders with unrestored inventory
        eligible_orders_qs = Order.objects.filter(
            payment_status=Order.PaymentStatus.PENDING,
            order_status__in=[Order.OrderStatus.PENDING, Order.OrderStatus.CONFIRMED],
            inventory_restored=False,
            created_at__lte=cutoff_time,
        ).order_by('created_at')[:limit]

        eligible_orders = list(eligible_orders_qs)
        total_found = len(eligible_orders)

        if total_found == 0:
            self.stdout.write(self.style.SUCCESS("No stale abandoned orders found. Inventory is healthy."))
            return

        self.stdout.write(f"Found {total_found} candidate order(s) eligible for abandoned cleanup.")

        restored_count = 0
        reconciled_count = 0
        skipped_count = 0

        for order in eligible_orders:
            ref = order.order_reference
            created_str = order.created_at.strftime('%Y-%m-%d %H:%M:%S')

            if dry_run:
                self.stdout.write(f"[DRY-RUN] Would cancel order #{ref} (created: {created_str}) and restore stock.")
                restored_count += 1
                continue

            # 2. Check Stripe status if session exists and verification enabled
            if (
                order.stripe_checkout_session_id
                and not skip_stripe_check
                and is_stripe_configured()
            ):
                try:
                    stripe.api_key = get_stripe_secret_key()
                    session = stripe.checkout.Session.retrieve(order.stripe_checkout_session_id)
                    session_dict = session.to_dict() if hasattr(session, 'to_dict') else dict(session)

                    # If customer completed payment on Stripe right around the timeout, reconcile as PAID!
                    if session_dict.get('payment_status') == 'paid':
                        logger.info(
                            "Order %s was paid on Stripe. Reconciling payment instead of cancelling.",
                            ref
                        )
                        _handle_checkout_session_completed(session_dict, event_id="cleanup_reconciliation")
                        self.stdout.write(
                            self.style.SUCCESS(f"Reconciled order #{ref} as PAID from verified Stripe session.")
                        )
                        reconciled_count += 1
                        continue

                    # If session is still open, expire it in Stripe to prevent late payments after restock
                    if session_dict.get('status') == 'open':
                        try:
                            stripe.checkout.Session.expire(order.stripe_checkout_session_id)
                            logger.info("Expired open Stripe session for abandoned order %s", ref)
                        except Exception as exp_err:
                            logger.warning(
                                "Could not expire Stripe session %s for order %s: %s",
                                order.stripe_checkout_session_id,
                                ref,
                                exp_err
                            )

                except Exception as stripe_err:
                    # In case of temporary Stripe network error, skip this order to prevent premature release
                    logger.warning(
                        "Stripe API check failed for order %s: %s. Skipping this run to prevent premature stock release.",
                        ref,
                        stripe_err
                    )
                    self.stdout.write(
                        self.style.WARNING(f"Skipped order #{ref} due to temporary Stripe communication error.")
                    )
                    skipped_count += 1
                    continue

            # 3. Restore inventory and transition order state atomically
            result = restore_order_inventory(
                order=order,
                reason=f"Abandoned checkout cleanup (timeout: {timeout_minutes}m)",
                target_order_status=Order.OrderStatus.CANCELLED,
                target_payment_status=Order.PaymentStatus.FAILED,
            )

            if result.get('restored'):
                restored_count += 1
                items_info = ", ".join(result.get('items_restored', [])) or "items"
                self.stdout.write(
                    self.style.SUCCESS(f"Cancelled order #{ref} and restored stock: {items_info}.")
                )
            else:
                skipped_count += 1
                self.stdout.write(
                    f"Order #{ref} was not restored: {result.get('message', result.get('status'))}"
                )

        summary_msg = (
            f"Cleanup complete. Processed {total_found} orders: "
            f"{restored_count} restored & cancelled, "
            f"{reconciled_count} reconciled as paid, "
            f"{skipped_count} skipped."
        )
        self.stdout.write(self.style.SUCCESS(summary_msg))
