import logging
from typing import Any, cast
from decimal import Decimal
import stripe
from django.conf import settings
from django.db import transaction
from .models import Order, OrderItem

logger = logging.getLogger(__name__)


def get_stripe_secret_key() -> str:
    """Return the configured Stripe secret key from Django settings."""
    return getattr(settings, 'STRIPE_SECRET_KEY', '').strip()


def get_stripe_webhook_secret() -> str:
    """Return the configured Stripe webhook signing secret from Django settings."""
    return getattr(settings, 'STRIPE_WEBHOOK_SECRET', '').strip()


def is_stripe_configured() -> bool:
    """Check if Stripe secret key is configured."""
    return bool(get_stripe_secret_key())


def create_stripe_checkout_session(order: Order, request=None) -> stripe.checkout.Session:
    """
    Create a Stripe Checkout Session for an eligible unpaid order.
    Calculates authoritative GBP amounts from the backend database.
    
    Raises:
        RuntimeError: If Stripe is not configured.
        ValueError: If order is already paid, cancelled, or has an invalid amount.
        stripe.error.StripeError: On Stripe API communication failure.
    """
    if order.payment_status == Order.PaymentStatus.PAID:
        raise ValueError(f"Order #{order.order_reference} is already paid.")

    if order.order_status == Order.OrderStatus.CANCELLED:
        raise ValueError(f"Cannot initiate payment for cancelled Order #{order.order_reference}.")

    secret_key = get_stripe_secret_key()
    if not secret_key:
        raise RuntimeError("Stripe secret key is not configured in environment (STRIPE_SECRET_KEY).")

    stripe.api_key = secret_key

    # Check if order already has an active, open Stripe Checkout Session (idempotent retry)
    if order.stripe_checkout_session_id:
        try:
            existing_session = stripe.checkout.Session.retrieve(order.stripe_checkout_session_id)
            session_url = getattr(existing_session, 'url', None) or ''
            if (
                existing_session
                and getattr(existing_session, 'status', None) == 'open'
                and session_url.startswith('https://checkout.stripe.com/')
            ):
                logger.info(
                    "Reusing open Stripe Checkout Session %s for order %s",
                    existing_session.id,
                    order.order_reference
                )
                return existing_session
        except Exception as retrieve_err:
            logger.warning(
                "Could not reuse existing session %s for order %s (%s). Creating new session.",
                order.stripe_checkout_session_id,
                order.order_reference,
                retrieve_err
            )

    currency = getattr(settings, 'STRIPE_CURRENCY', 'gbp').lower()
    total_amount_dec = Decimal(str(order.total_amount))
    total_pence = round(total_amount_dec * 100)

    if total_pence <= 0:
        raise ValueError("Order total amount must be greater than zero.")

    # Build line items authoritatively from OrderItem snapshot
    line_items = []
    items = list(OrderItem.objects.filter(order=order))

    if items:
        for item in items:
            item_name = item.product_name
            if item.variant_name:
                item_name = f"{item_name} ({item.variant_name})"
            item_price_dec = Decimal(str(item.unit_price))
            item_pence = round(item_price_dec * 100)
            line_items.append({
                'price_data': {
                    'currency': currency,
                    'product_data': {
                        'name': item_name,
                    },
                    'unit_amount': item_pence,
                },
                'quantity': item.quantity,
            })

        delivery_fee_dec = Decimal(str(order.delivery_fee or '0.00'))
        if delivery_fee_dec > Decimal('0.00'):
            delivery_pence = round(delivery_fee_dec * 100)
            line_items.append({
                'price_data': {
                    'currency': currency,
                    'product_data': {
                        'name': 'UK Delivery Fee',
                    },
                    'unit_amount': delivery_pence,
                },
                'quantity': 1,
            })

    # Validate sum of line items matches total_pence; if mismatch, fallback to consolidated line item
    line_items_sum = sum(li['price_data']['unit_amount'] * li['quantity'] for li in line_items)
    if not line_items or line_items_sum != total_pence:
        line_items = [{
            'price_data': {
                'currency': currency,
                'product_data': {
                    'name': f"AdesHub Order #{order.order_reference}",
                    'description': f"{len(items)} grocery item(s)",
                },
                'unit_amount': total_pence,
            },
            'quantity': 1,
        }]

    frontend_base = getattr(settings, 'FRONTEND_URL', 'https://adeshubafricanstore.com').rstrip('/')
    success_url = f"{frontend_base}/orders/confirmation/{order.order_reference}?session_id={{CHECKOUT_SESSION_ID}}&payment_status=success"
    cancel_url = f"{frontend_base}/orders/confirmation/{order.order_reference}?payment_status=cancelled"

    customer_email = order.user.email if order.user else (order.guest_email or None)

    metadata = {
        'order_reference': order.order_reference,
        'order_id': str(order.pk),
        'expected_amount_pence': str(total_pence),
        'currency': currency,
    }

    session_params: dict[str, Any] = {
        'mode': 'payment',
        'line_items': cast(Any, line_items),
        'client_reference_id': order.order_reference,
        'metadata': metadata,
        'payment_intent_data': {
            'metadata': metadata,
        },
        'success_url': success_url,
        'cancel_url': cancel_url,
    }

    if customer_email:
        session_params['customer_email'] = customer_email

    session = stripe.checkout.Session.create(**cast(Any, session_params))

    # Persist the session ID on the order record
    order.stripe_checkout_session_id = session.id
    order.save(update_fields=['stripe_checkout_session_id'])

    logger.info(
        "Created Stripe Checkout Session %s for order %s (amount: %s %s)",
        session.id,
        order.order_reference,
        order.total_amount,
        currency.upper()
    )

    session_url = getattr(session, 'url', None) or ''
    if not session_url or not session_url.startswith('https://checkout.stripe.com/'):
        raise ValueError("Invalid Stripe Checkout Session URL returned from payment gateway.")

    return session


def verify_and_process_webhook(payload: bytes, sig_header: str) -> dict:
    """
    Verify Stripe webhook signature, validate order metadata, amount, and currency,
    and update order payment status idempotently.

    Handles events from all Stripe subscriptions:
    - checkout.session.completed (primary checkout payment confirmation)
    - checkout.session.expired (unpaid checkout session expiration)
    - payment_intent.succeeded (fallback/direct payment confirmation)
    - payment_intent.payment_failed (declined/failed payment)
    - charge.refunded (admin or dispute refund)
    - Any other event: gracefully acknowledged with HTTP 200 (ignored status)

    Raises:
        RuntimeError: If webhook secret is not configured.
        ValueError: If payload or signature is invalid.
        stripe.error.SignatureVerificationError: If signature fails validation.
    """
    webhook_secret = get_stripe_webhook_secret()
    if not webhook_secret:
        raise RuntimeError("Stripe webhook signing secret is not configured in environment (STRIPE_WEBHOOK_SECRET).")

    event = stripe.Webhook.construct_event(
        payload=payload,
        sig_header=sig_header,
        secret=webhook_secret
    )

    event_dict = event.to_dict() if hasattr(event, 'to_dict') else dict(event)
    event_type = event_dict.get('type')
    event_id = event_dict.get('id', 'unknown')
    data_object = event_dict.get('data', {}).get('object', {})
    if hasattr(data_object, 'to_dict'):
        data_object = data_object.to_dict()

    logger.info("Processing Stripe webhook event %s (id: %s)", event_type, event_id)

    if event_type == 'checkout.session.completed':
        return _handle_checkout_session_completed(data_object, event_id)

    elif event_type == 'checkout.session.expired':
        return _handle_checkout_session_expired(data_object, event_id)

    elif event_type == 'payment_intent.succeeded':
        return _handle_payment_intent_succeeded(data_object, event_id)

    elif event_type == 'payment_intent.payment_failed':
        return _handle_payment_intent_failed(data_object, event_id)

    elif event_type == 'charge.refunded':
        return _handle_charge_refunded(data_object, event_id)

    return {
        'status': 'ignored',
        'event_type': event_type,
        'event_id': event_id,
        'message': f"Event type '{event_type}' acknowledged (no action required)."
    }


def _handle_checkout_session_completed(session: dict, event_id: str) -> dict:
    order_ref = (
        session.get('client_reference_id') or
        session.get('metadata', {}).get('order_reference')
    )

    if not order_ref:
        logger.warning("Checkout session completed without order reference. Session ID: %s", session.get('id'))
        return {
            'status': 'ignored',
            'reason': 'missing_order_reference',
            'session_id': session.get('id')
        }

    with transaction.atomic():
        order = Order.objects.select_for_update().filter(order_reference=order_ref).first()
        if not order:
            logger.warning("Order not found for checkout session. Reference: %s", order_ref)
            return {
                'status': 'error',
                'reason': 'order_not_found',
                'order_reference': order_ref
            }

        # Idempotency check: Already paid?
        if order.payment_status == Order.PaymentStatus.PAID:
            logger.info("Order %s already marked as PAID. Skipping duplicate processing for event %s.", order_ref, event_id)
            return {
                'status': 'already_processed',
                'order_reference': order_ref,
                'payment_status': order.payment_status
            }

        # Currency validation
        expected_currency = getattr(settings, 'STRIPE_CURRENCY', 'gbp').lower()
        event_currency = session.get('currency', '').lower()
        if event_currency != expected_currency:
            logger.error(
                "Currency mismatch for order %s: expected %s, got %s",
                order_ref,
                expected_currency,
                event_currency
            )
            return {
                'status': 'error',
                'reason': 'currency_mismatch',
                'expected_currency': expected_currency,
                'received_currency': event_currency,
                'order_reference': order_ref
            }

        # Amount validation
        amount_total = session.get('amount_total')
        expected_pence = round(order.total_amount * 100)
        if amount_total != expected_pence:
            logger.error(
                "Amount mismatch for order %s: expected %s pence, got %s pence",
                order_ref,
                expected_pence,
                amount_total
            )
            return {
                'status': 'error',
                'reason': 'amount_mismatch',
                'expected_amount_pence': expected_pence,
                'received_amount_pence': amount_total,
                'order_reference': order_ref
            }

        # Payment status check
        payment_status = session.get('payment_status')
        if payment_status == 'paid':
            payment_intent_id = session.get('payment_intent')
            order.payment_status = Order.PaymentStatus.PAID
            if payment_intent_id:
                order.stripe_payment_intent_id = str(payment_intent_id)

            # Ensure guest email is populated from Stripe customer details if not present on order
            customer_email = session.get('customer_details', {}).get('email') or session.get('customer_email')
            if customer_email and not order.user and not order.guest_email:
                order.guest_email = customer_email.strip().lower()

            if order.order_status == Order.OrderStatus.PENDING:
                order.order_status = Order.OrderStatus.CONFIRMED

            order.save(update_fields=['payment_status', 'stripe_payment_intent_id', 'order_status', 'guest_email', 'updated_at'])

            logger.info(
                "Successfully marked order %s as PAID (Payment Intent: %s)",
                order_ref,
                order.stripe_payment_intent_id
            )

    if payment_status == 'paid':
        # Trigger automated order confirmation email asynchronously
        try:
            from .email_service import send_order_confirmation_email_async
            send_order_confirmation_email_async(order.id)
        except Exception as email_err:
            logger.error("Failed to trigger confirmation email for order %s: %s", order_ref, email_err)

        return {
            'status': 'payment_confirmed',
            'order_reference': order_ref,
            'payment_status': order.payment_status,
            'payment_intent_id': order.stripe_payment_intent_id
        }

    return {
        'status': 'unconfirmed',
        'order_reference': order_ref,
        'session_payment_status': payment_status
    }


def _handle_checkout_session_expired(session: dict, event_id: str) -> dict:
    order_ref = (
        session.get('client_reference_id') or
        session.get('metadata', {}).get('order_reference')
    )
    if not order_ref:
        return {'status': 'ignored', 'reason': 'missing_order_reference'}

    order = Order.objects.filter(order_reference=order_ref).first()
    if not order:
        return {'status': 'error', 'reason': 'order_not_found', 'order_reference': order_ref}

    # Safety: A successfully paid order must NEVER have its payment or inventory undone by late expiration
    if order.payment_status == Order.PaymentStatus.PAID:
        logger.info(
            "Order %s is already PAID. Ignoring late checkout.session.expired event (event_id: %s).",
            order_ref,
            event_id
        )
        return {
            'status': 'already_processed',
            'order_reference': order_ref,
            'payment_status': order.payment_status
        }

    # If inventory already restored, ensure order reflects FAILED/CANCELLED idempotently
    if order.inventory_restored:
        logger.info("Order %s inventory already restored. Skipping duplicate restoration for event %s.", order_ref, event_id)
        if order.payment_status != Order.PaymentStatus.FAILED:
            order.payment_status = Order.PaymentStatus.FAILED
            order.save(update_fields=['payment_status', 'updated_at'])
        return {
            'status': 'session_expired',
            'order_reference': order_ref,
            'payment_status': order.payment_status
        }

    from .inventory_service import restore_order_inventory
    restore_result = restore_order_inventory(
        order=order,
        reason=f"Stripe checkout session expired (event: {event_id})",
        target_order_status=Order.OrderStatus.CANCELLED,
        target_payment_status=Order.PaymentStatus.FAILED
    )
    order.refresh_from_db()
    logger.info(
        "Order %s marked as CANCELLED/FAILED and inventory restored (%s items) due to expired Stripe session.",
        order_ref,
        len(restore_result.get('items_restored', []))
    )
    return {
        'status': 'session_expired',
        'order_reference': order_ref,
        'payment_status': order.payment_status
    }


def _handle_payment_intent_failed(intent: dict, event_id: str) -> dict:
    order_ref = intent.get('metadata', {}).get('order_reference')
    if not order_ref:
        return {'status': 'ignored', 'reason': 'missing_order_reference'}

    order = Order.objects.filter(order_reference=order_ref).first()
    if not order:
        return {'status': 'error', 'reason': 'order_not_found', 'order_reference': order_ref}

    # A paid order must never be downgraded by a failure event
    if order.payment_status == Order.PaymentStatus.PAID:
        logger.info(
            "Order %s is already PAID. Ignoring payment_intent.payment_failed event (event_id: %s).",
            order_ref,
            event_id
        )
        return {
            'status': 'already_processed',
            'order_reference': order_ref,
            'payment_status': order.payment_status
        }

    # Update payment intent reference and payment status if currently PENDING
    # Note: Stock is NOT released here because the customer may still retry payment
    # using another card on the active Checkout Session. Stock will be released when
    # the Checkout Session expires or the abandoned order cleanup executes.
    if order.payment_status == Order.PaymentStatus.PENDING:
        order.payment_status = Order.PaymentStatus.FAILED
        if intent.get('id'):
            order.stripe_payment_intent_id = str(intent.get('id'))
        order.save(update_fields=['payment_status', 'stripe_payment_intent_id', 'updated_at'])
        logger.info("Order %s marked as FAILED due to failed payment intent attempt.", order_ref)
        return {
            'status': 'payment_failed',
            'order_reference': order_ref,
            'payment_status': order.payment_status
        }

    return {
        'status': 'already_processed',
        'order_reference': order_ref,
        'payment_status': order.payment_status
    }


def _handle_payment_intent_succeeded(intent: dict, event_id: str) -> dict:
    order_ref = intent.get('metadata', {}).get('order_reference')
    payment_intent_id = intent.get('id')

    with transaction.atomic():
        order = None
        if order_ref:
            order = Order.objects.select_for_update().filter(order_reference=order_ref).first()
        if not order and payment_intent_id:
            order = Order.objects.select_for_update().filter(stripe_payment_intent_id=payment_intent_id).first()

        if not order:
            logger.warning("Order not found for succeeded payment intent %s (ref: %s)", payment_intent_id, order_ref)
            return {'status': 'ignored', 'reason': 'order_not_found', 'payment_intent_id': payment_intent_id}

        if order.payment_status == Order.PaymentStatus.PAID:
            logger.info("Order %s already marked as PAID. Skipping duplicate processing for event %s.", order.order_reference, event_id)
            return {
                'status': 'already_processed',
                'order_reference': order.order_reference,
                'payment_status': order.payment_status
            }

        # Currency validation
        expected_currency = getattr(settings, 'STRIPE_CURRENCY', 'gbp').lower()
        event_currency = intent.get('currency', '').lower()
        if event_currency != expected_currency:
            logger.error("Currency mismatch on payment intent for order %s: expected %s, got %s", order.order_reference, expected_currency, event_currency)
            return {
                'status': 'error',
                'reason': 'currency_mismatch',
                'expected_currency': expected_currency,
                'received_currency': event_currency,
                'order_reference': order.order_reference
            }

        # Amount validation
        amount_received = intent.get('amount_received') or intent.get('amount')
        expected_pence = round(order.total_amount * 100)
        if amount_received != expected_pence:
            logger.error("Amount mismatch on payment intent for order %s: expected %s pence, got %s pence", order.order_reference, expected_pence, amount_received)
            return {
                'status': 'error',
                'reason': 'amount_mismatch',
                'expected_amount_pence': expected_pence,
                'received_amount_pence': amount_received,
                'order_reference': order.order_reference
            }

        order.payment_status = Order.PaymentStatus.PAID
        if payment_intent_id:
            order.stripe_payment_intent_id = str(payment_intent_id)

        if order.order_status == Order.OrderStatus.PENDING:
            order.order_status = Order.OrderStatus.CONFIRMED

        order.save(update_fields=['payment_status', 'stripe_payment_intent_id', 'order_status', 'updated_at'])

    logger.info("Successfully marked order %s as PAID via payment_intent.succeeded (%s)", order.order_reference, order.stripe_payment_intent_id)

    try:
        from .email_service import send_order_confirmation_email_async
        send_order_confirmation_email_async(order.id)
    except Exception as email_err:
        logger.error("Failed to trigger confirmation email for order %s: %s", order.order_reference, email_err)

    return {
        'status': 'payment_confirmed',
        'order_reference': order.order_reference,
        'payment_status': order.payment_status,
        'payment_intent_id': order.stripe_payment_intent_id
    }


def _handle_charge_refunded(charge: dict, event_id: str) -> dict:
    order_ref = charge.get('metadata', {}).get('order_reference')
    payment_intent_id = charge.get('payment_intent')
    order = None

    if order_ref:
        order = Order.objects.filter(order_reference=order_ref).first()
    if not order and payment_intent_id:
        order = Order.objects.filter(stripe_payment_intent_id=payment_intent_id).first()

    if not order:
        logger.info("Order not found for charge refunded %s (ref: %s)", charge.get('id'), order_ref)
        return {'status': 'ignored', 'reason': 'order_not_found', 'charge_id': charge.get('id')}

    if order.payment_status != Order.PaymentStatus.REFUNDED:
        order.payment_status = Order.PaymentStatus.REFUNDED
        order.save(update_fields=['payment_status', 'updated_at'])
        logger.info("Order %s successfully updated to REFUNDED status for charge %s", order.order_reference, charge.get('id'))
        return {
            'status': 'order_refunded',
            'order_reference': order.order_reference,
            'payment_status': order.payment_status,
        }

    return {
        'status': 'already_processed',
        'order_reference': order.order_reference,
        'payment_status': order.payment_status
    }
