from decimal import Decimal, InvalidOperation
import logging
from typing import Optional
from django.conf import settings
from .models import DeliveryMethod

logger = logging.getLogger(__name__)


class ShippingConfigurationError(Exception):
    """
    Raised when delivery fee configuration is missing, invalid, or corrupted.
    Ensures the application never silently guesses or invents an unapproved fee.
    """
    pass


def get_active_delivery_methods() -> list[DeliveryMethod]:
    """Retrieve all active delivery methods ordered by display order."""
    return list(DeliveryMethod.objects.filter(is_active=True).order_by('display_order', 'id'))


def calculate_order_delivery_fee(
    subtotal: Decimal,
    method_code: Optional[str] = None
) -> tuple[Decimal, str]:
    """
    Calculate the authoritative delivery fee and method name for a given order subtotal.

    Rules:
    1. Look up active DeliveryMethod by method_code, or default active method.
    2. Fall back to settings.DEFAULT_DELIVERY_FEE if no database method exists.
    3. If no valid delivery fee is configured, raise ShippingConfigurationError clearly.
    4. Apply free-delivery threshold if configured and met.
    5. Never silently invent an unapproved arbitrary fee.
    """
    if subtotal < Decimal('0.00'):
        raise ValueError("Order subtotal cannot be negative.")

    # 1. Database-backed Delivery Methods
    methods = DeliveryMethod.objects.filter(is_active=True)
    target_method: Optional[DeliveryMethod] = None

    if method_code:
        target_method = methods.filter(code=method_code).first()

    if not target_method:
        target_method = methods.filter(is_default=True).first() or methods.first()

    if target_method:
        if target_method.base_fee is None or target_method.base_fee < Decimal('0.00'):
            raise ShippingConfigurationError(
                f"Delivery method '{target_method.name}' has an invalid or negative base fee configured."
            )

        fee = target_method.base_fee
        if (
            target_method.free_delivery_threshold is not None
            and target_method.free_delivery_threshold >= Decimal('0.00')
            and subtotal >= target_method.free_delivery_threshold
        ):
            fee = Decimal('0.00')

        return fee, target_method.name

    # 2. Settings / Environment Fallback
    raw_default_fee = getattr(settings, 'DEFAULT_DELIVERY_FEE', None)
    if raw_default_fee is not None and str(raw_default_fee).strip() != '':
        try:
            parsed_fee = Decimal(str(raw_default_fee).strip())
            if parsed_fee < Decimal('0.00'):
                raise ShippingConfigurationError("Configured DEFAULT_DELIVERY_FEE in settings cannot be negative.")

            raw_threshold = getattr(settings, 'FREE_DELIVERY_THRESHOLD', None)
            if raw_threshold is not None and str(raw_threshold).strip() != '':
                try:
                    parsed_threshold = Decimal(str(raw_threshold).strip())
                    if parsed_threshold >= Decimal('0.00') and subtotal >= parsed_threshold:
                        return Decimal('0.00'), 'Standard UK Delivery'
                except (InvalidOperation, ValueError):
                    logger.warning("Invalid FREE_DELIVERY_THRESHOLD configured: %s", raw_threshold)

            return parsed_fee, 'Standard UK Delivery'
        except (InvalidOperation, ValueError) as err:
            raise ShippingConfigurationError(f"Invalid DEFAULT_DELIVERY_FEE format configured: {raw_default_fee}") from err

    # 3. No valid delivery fee configured
    raise ShippingConfigurationError(
        "No valid delivery fee has been configured for the store. "
        "Please configure delivery charges in store administration before proceeding."
    )


def get_delivery_quote_payload(
    subtotal: Decimal,
    method_code: Optional[str] = None
) -> dict:
    """
    Generate a full delivery quote response for the frontend (Cart and Checkout pages).
    Returns active methods, calculated fees, and financial totals in GBP.
    """
    active_methods = get_active_delivery_methods()
    methods_data = []

    for m in active_methods:
        is_free = m.free_delivery_threshold is not None and subtotal >= m.free_delivery_threshold
        calculated = Decimal('0.00') if is_free else m.base_fee
        methods_data.append({
            'id': m.id,
            'name': m.name,
            'code': m.code,
            'description': m.description,
            'base_fee': f"{m.base_fee:.2f}",
            'free_delivery_threshold': f"{m.free_delivery_threshold:.2f}" if m.free_delivery_threshold else None,
            'estimated_days': m.estimated_days,
            'is_default': m.is_default,
            'calculated_fee': f"{calculated:.2f}",
            'is_free': is_free,
        })

    # Calculate authoritative fee for requested or default method
    fee, method_name = calculate_order_delivery_fee(subtotal, method_code)
    final_total = subtotal + fee

    # Calculate amount needed for free delivery, if applicable
    threshold_decimal: Optional[Decimal] = None
    if active_methods:
        # Default or active method's threshold
        sel = next((m for m in active_methods if (method_code and m.code == method_code) or m.is_default), active_methods[0])
        threshold_decimal = sel.free_delivery_threshold
    else:
        raw_threshold = getattr(settings, 'FREE_DELIVERY_THRESHOLD', None)
        if raw_threshold:
            try:
                threshold_decimal = Decimal(str(raw_threshold))
            except Exception:
                threshold_decimal = None

    amount_needed = None
    if threshold_decimal is not None and subtotal < threshold_decimal:
        amount_needed = f"{(threshold_decimal - subtotal):.2f}"

    return {
        'methods': methods_data,
        'selected_method_name': method_name,
        'subtotal': f"{subtotal:.2f}",
        'delivery_fee': f"{fee:.2f}",
        'final_total': f"{final_total:.2f}",
        'is_free_delivery': fee == Decimal('0.00'),
        'free_delivery_threshold': f"{threshold_decimal:.2f}" if threshold_decimal else None,
        'amount_needed_for_free_delivery': amount_needed,
        'currency': 'GBP',
    }
