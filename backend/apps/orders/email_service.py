import logging
import sys
import threading
import time
import urllib.parse
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.utils.html import escape
from .models import Order
from apps.core.email_service import send_transactional_email, mask_email

logger = logging.getLogger(__name__)


def _mask_email(email: str) -> str:
    """Safely mask an email address for logging without exposing full PII."""
    return mask_email(email)


def get_order_frontend_url(order: Order) -> str:
    """Generate the authoritative order details link for the customer."""
    frontend_base = getattr(settings, 'FRONTEND_URL', 'https://adeshubafricanstore.com').rstrip('/')
    customer_email = order.user.email if order.user else (order.guest_email or '')
    
    if not order.user and customer_email:
        # Include guest verification email parameter
        encoded_email = urllib.parse.quote(customer_email)
        return f"{frontend_base}/orders/{order.order_reference}?email={encoded_email}"
    return f"{frontend_base}/orders/{order.order_reference}"


def build_confirmation_email_content(order: Order) -> tuple[str, str, str]:
    """
    Construct subject, plain text body, and responsive HTML body
    for an authoritative order confirmation email matching AdesHub branding.
    Confirms order has been received and is being processed (does not claim shipped).
    """
    subject = f"AdesHub Order #{order.order_reference} – Payment Confirmation & Order Received"
    customer_name = order.recipient_name or (order.user.get_full_name() if order.user else "Valued Customer")
    order_url = get_order_frontend_url(order)
    support_email = getattr(settings, 'SUPPORT_EMAIL', 'Info@adeshub.co.uk')
    support_phone = getattr(settings, 'SUPPORT_PHONE', '+44 (0) 20 1234 5678')
    order_date_str = (
        order.created_at.strftime('%d %B %Y, %H:%M')
        if order.created_at
        else timezone.now().strftime('%d %B %Y, %H:%M')
    )

    items = list(order.items.all())

    # Delivery address lines
    address_parts = [
        order.recipient_name,
        order.address_line1,
    ]
    if order.address_line2:
        address_parts.append(order.address_line2)
    address_parts.append(f"{order.city}, {order.postal_code}")
    if order.county_region:
        address_parts.append(order.county_region)
    address_parts.append(order.country)
    if order.phone_number:
        address_parts.append(f"Phone: {order.phone_number}")

    address_text = "\n".join(address_parts)
    address_html = "<br>".join(address_parts)

    # Text summary of items (ASCII-safe for all email clients)
    items_text_lines = []
    for item in items:
        v_str = f" ({item.variant_name})" if item.variant_name else ""
        items_text_lines.append(
            f"- {item.quantity}x {item.product_name}{v_str} @ GBP {Decimal(str(item.unit_price)):.2f} each = GBP {Decimal(str(item.line_total)):.2f}"
        )
    items_text = "\n".join(items_text_lines)

    delivery_fee_str = (
        "Free UK Standard"
        if Decimal(str(order.delivery_fee or '0.00')) == Decimal('0.00')
        else f"GBP {Decimal(str(order.delivery_fee)):.2f}"
    )
    delivery_fee_html = (
        "Free UK Standard"
        if Decimal(str(order.delivery_fee or '0.00')) == Decimal('0.00')
        else f"&pound;{Decimal(str(order.delivery_fee)):.2f}"
    )

    # 1. Plain Text Version (Universal ASCII-compatible)
    text_content = f"""Hello {customer_name},

Thank you for shopping with AdesHub!
Your payment has been successfully confirmed. Your order has been received and is now being carefully prepared and processed.

Order Reference: {order.order_reference}
Order Date: {order_date_str}

You can view your order details and track its fulfillment progress using the link below:
{order_url}

ORDER SUMMARY
--------------------------------------------------
{items_text}

Subtotal: GBP {Decimal(str(order.subtotal)):.2f}
Delivery Fee: {delivery_fee_str}
Total Paid: GBP {Decimal(str(order.total_amount)):.2f}

DELIVERY ADDRESS
--------------------------------------------------
{address_text}

ESTIMATED DELIVERY
--------------------------------------------------
Standard UK Delivery: Estimated within 2-3 business days. You will receive another notification once your package has been dispatched.

If you have any questions or need assistance with your order, please reply directly to this email or contact our customer support team at {support_email} or call {support_phone}.

Thank you for choosing AdesHub. We appreciate your business!

Warm regards,
The AdesHub Team
https://adeshubafricanstore.com
"""

    # 2. HTML Version (Responsive, inline CSS, AdesHub emerald theme)
    items_html_rows = []
    for item in items:
        v_tag = f"<span style=\"color:#64748b;font-size:12px;\">Variant: {item.variant_name}</span>" if item.variant_name else ""
        items_html_rows.append(f"""
        <tr>
            <td style="padding:12px 16px;border-bottom:1px solid #f1f5f9;font-size:14px;color:#1e293b;">
                <strong>{escape(item.product_name)}</strong><br>{v_tag}
            </td>
            <td style="padding:12px 16px;border-bottom:1px solid #f1f5f9;font-size:14px;color:#1e293b;text-align:center;">
                {item.quantity}
            </td>
            <td style="padding:12px 16px;border-bottom:1px solid #f1f5f9;font-size:14px;color:#1e293b;text-align:right;">
                &pound;{Decimal(str(item.unit_price)):.2f}
            </td>
            <td style="padding:12px 16px;border-bottom:1px solid #f1f5f9;font-size:14px;color:#0f172a;font-weight:600;text-align:right;">
                &pound;{Decimal(str(item.line_total)):.2f}
            </td>
        </tr>
        """)
    items_html_table = "".join(items_html_rows)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AdesHub Order Confirmation</title>
</head>
<body style="margin:0;padding:0;background-color:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#1e293b;line-height:1.5;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#f8fafc;padding:32px 16px;">
        <tr>
            <td align="center">
                <!-- Main Card -->
                <table role="presentation" width="100%" style="max-width:600px;background-color:#ffffff;border-radius:12px;box-shadow:0 4px 6px -1px rgba(0,0,0,0.05),0 2px 4px -2px rgba(0,0,0,0.05);overflow:hidden;border:1px solid #e2e8f0;">
                    
                    <!-- Header Banner -->
                    <tr>
                        <td style="background:linear-gradient(135deg, #065f46 0%, #059669 100%);padding:36px 32px;text-align:center;">
                            <div style="display:inline-block;background-color:#10b981;width:48px;height:48px;border-radius:50%;text-align:center;line-height:48px;margin-bottom:16px;">
                                <span style="color:#ffffff;font-size:24px;font-weight:bold;">&#10003;</span>
                            </div>
                            <h1 style="margin:0 0 8px;color:#ffffff;font-size:24px;font-weight:700;letter-spacing:-0.5px;">AdesHub</h1>
                            <p style="margin:0;color:#d1fae5;font-size:15px;font-weight:500;">Payment Confirmed &bull; Order Received</p>
                        </td>
                    </tr>

                    <!-- Body Content -->
                    <tr>
                        <td style="padding:32px 32px 24px;">
                            <h2 style="margin:0 0 12px;font-size:18px;color:#0f172a;font-weight:600;">Hello {customer_name},</h2>
                            <p style="margin:0 0 16px;color:#475569;font-size:15px;">
                                Thank you for shopping with <strong>AdesHub</strong>! Your payment has been confirmed, and your order has been received and is now being processed for delivery.
                            </p>

                            <!-- Order Reference & Date Box -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;margin-bottom:28px;">
                                <tr>
                                    <td style="padding:14px 18px;">
                                        <span style="font-size:12px;color:#166534;text-transform:uppercase;font-weight:700;letter-spacing:0.5px;display:block;margin-bottom:2px;">Your Order Reference</span>
                                        <span style="font-size:18px;color:#14532d;font-weight:700;font-family:monospace;">{order.order_reference}</span>
                                    </td>
                                    <td style="padding:14px 18px;text-align:right;">
                                        <span style="font-size:12px;color:#166534;text-transform:uppercase;font-weight:700;letter-spacing:0.5px;display:block;margin-bottom:2px;">Order Date</span>
                                        <span style="font-size:14px;color:#14532d;font-weight:600;">{order_date_str}</span>
                                    </td>
                                </tr>
                            </table>

                            <!-- CTA Button -->
                            <div style="text-align:center;margin-bottom:32px;">
                                <a href="{order_url}" style="display:inline-block;background-color:#059669;color:#ffffff;text-decoration:none;padding:14px 28px;border-radius:8px;font-weight:600;font-size:15px;box-shadow:0 2px 4px rgba(5,150,105,0.25);">
                                    View Your Order Details &rarr;
                                </a>
                            </div>

                            <!-- Ordered Items Table -->
                            <h3 style="margin:0 0 12px;font-size:15px;color:#0f172a;text-transform:uppercase;letter-spacing:0.5px;font-weight:700;">Order Summary</h3>
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;margin-bottom:24px;border:1px solid #f1f5f9;border-radius:6px;overflow:hidden;">
                                <thead>
                                    <tr style="background-color:#f8fafc;">
                                        <th style="padding:10px 16px;font-size:12px;color:#64748b;text-align:left;border-bottom:1px solid #e2e8f0;">ITEM</th>
                                        <th style="padding:10px 16px;font-size:12px;color:#64748b;text-align:center;border-bottom:1px solid #e2e8f0;">QTY</th>
                                        <th style="padding:10px 16px;font-size:12px;color:#64748b;text-align:right;border-bottom:1px solid #e2e8f0;">PRICE</th>
                                        <th style="padding:10px 16px;font-size:12px;color:#64748b;text-align:right;border-bottom:1px solid #e2e8f0;">TOTAL</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {items_html_table}
                                </tbody>
                            </table>

                            <!-- Financial Breakdown -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom:28px;">
                                <tr>
                                    <td style="padding:6px 0;font-size:14px;color:#64748b;">Subtotal</td>
                                    <td style="padding:6px 0;font-size:14px;color:#1e293b;text-align:right;font-weight:500;">&pound;{Decimal(str(order.subtotal)):.2f}</td>
                                </tr>
                                <tr>
                                    <td style="padding:6px 0;font-size:14px;color:#64748b;">Delivery Fee</td>
                                    <td style="padding:6px 0;font-size:14px;color:#1e293b;text-align:right;font-weight:500;">{delivery_fee_html}</td>
                                </tr>
                                <tr>
                                    <td style="padding:12px 0 0;font-size:16px;color:#0f172a;font-weight:700;border-top:1px solid #e2e8f0;">Total Amount Paid</td>
                                    <td style="padding:12px 0 0;font-size:18px;color:#059669;text-align:right;font-weight:700;border-top:1px solid #e2e8f0;">&pound;{Decimal(str(order.total_amount)):.2f} GBP</td>
                                </tr>
                            </table>

                            <!-- Delivery Address & Timeframe Card -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#f8fafc;border-radius:8px;border:1px solid #e2e8f0;margin-bottom:24px;">
                                <tr>
                                    <td style="padding:16px 20px;">
                                        <h4 style="margin:0 0 8px;font-size:13px;color:#0f172a;text-transform:uppercase;letter-spacing:0.5px;">Delivery Address</h4>
                                        <div style="font-size:14px;color:#475569;line-height:1.6;">
                                             {address_html}
                                        </div>
                                        <div style="margin-top:12px;padding-top:10px;border-top:1px dashed #cbd5e1;font-size:13px;color:#0369a1;">
                                             <strong>Estimated Delivery:</strong> Standard UK Delivery (2-3 business days). You'll receive a dispatch notification once shipped.
                                        </div>
                                    </td>
                                </tr>
                            </table>

                            <!-- Support Help Note -->
                            <p style="margin:0;font-size:13px;color:#64748b;line-height:1.6;">
                                Need help with your order? Reply directly to this email or reach our support team at <a href="mailto:{support_email}" style="color:#059669;text-decoration:none;">{support_email}</a> or call {support_phone}.
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color:#f8fafc;padding:24px 32px;text-align:center;border-top:1px solid #e2e8f0;font-size:12px;color:#94a3b8;">
                            <p style="margin:0 0 6px;">Thank you for choosing AdesHub African Store. We appreciate your business!</p>
                            <p style="margin:0;">&copy; {timezone.now().year} AdesHub African Store. All rights reserved.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
    return subject, text_content, html_content


def send_order_confirmation_email(order: Order, max_retries: int = 2) -> dict:
    """
    Send an authoritative order confirmation email for a verified paid order.
    Idempotent: prevents duplicate emails if already sent.
    An email delivery failure never invalidates an otherwise successful payment.
    """
    if order.confirmation_email_sent:
        logger.info("Order %s confirmation email already sent. Skipping duplicate.", order.order_reference)
        return {
            'status': 'already_sent',
            'order_reference': order.order_reference,
            'email_delivery_status': order.email_delivery_status,
        }

    recipient_email = order.user.email if order.user else (order.guest_email or '')
    if not recipient_email:
        logger.warning("Order %s has no recipient email address. Skipping email.", order.order_reference)
        order.email_delivery_status = 'NO_RECIPIENT'
        order.save(update_fields=['email_delivery_status', 'updated_at'])
        return {'status': 'no_recipient', 'order_reference': order.order_reference}

    # Atomic DB claim to prevent race conditions if multiple webhooks arrive simultaneously
    claimed = Order.objects.filter(
        pk=order.pk,
        confirmation_email_sent=False
    ).exclude(email_delivery_status='CLAIMED').update(email_delivery_status='CLAIMED')

    if claimed == 0:
        logger.info("Order %s confirmation email is already claimed or sent. Skipping.", order.order_reference)
        return {'status': 'already_processing', 'order_reference': order.order_reference}

    subject, text_content, html_content = build_confirmation_email_content(order)
    reply_to = getattr(settings, 'EMAIL_REPLY_TO', 'Info@adeshub.co.uk')

    logger.info("Sending order confirmation email for order %s to %s", order.order_reference, mask_email(recipient_email))

    result = send_transactional_email(
        to_email=recipient_email,
        subject=subject,
        text_content=text_content,
        html_content=html_content,
        reply_to=reply_to,
        max_retries=max_retries,
    )

    if result.get('success'):
        now = timezone.now()
        order.confirmation_email_sent = True
        order.confirmation_email_sent_at = now
        order.email_delivery_status = 'ACCEPTED'
        order.save(update_fields=['confirmation_email_sent', 'confirmation_email_sent_at', 'email_delivery_status', 'updated_at'])
        logger.info("Confirmation email successfully accepted/sent for order %s via %s", order.order_reference, result.get('provider'))
        return {
            'status': 'sent',
            'order_reference': order.order_reference,
            'email_delivery_status': 'ACCEPTED',
            'message_id': result.get('message_id'),
        }
    else:
        order.email_delivery_status = 'FAILED'
        order.confirmation_email_sent = False
        order.save(update_fields=['email_delivery_status', 'confirmation_email_sent', 'updated_at'])
        logger.error(
            "Failed sending confirmation email for order %s: %s",
            order.order_reference,
            result.get('error', 'Unknown error')
        )
        return {
            'status': 'failed',
            'order_reference': order.order_reference,
            'error': result.get('error', 'Delivery failed'),
        }


def send_order_confirmation_email_async(order_id: int):
    """
    Dispatch order confirmation email in a background daemon thread.
    Does not block the HTTP request or webhook response.
    Closes database connections before and after execution to prevent connection leaks.
    In testing environment, runs synchronously for deterministic test execution.
    """
    if 'test' in sys.argv:
        order = Order.objects.filter(pk=order_id).first()
        if order:
            send_order_confirmation_email(order)
        return

    def _run():
        from django.db import connections, OperationalError, DatabaseError
        connections.close_all()
        order = None
        for attempt in range(5):
            try:
                order = Order.objects.filter(pk=order_id).first()
                if order:
                    break
            except (OperationalError, DatabaseError):
                time.sleep(0.25 * (attempt + 1))
                connections.close_all()

        try:
            if order:
                send_order_confirmation_email(order)
        except Exception as err:
            logger.error("Async confirmation email execution failed for order id %s: %s", order_id, str(err))
        finally:
            connections.close_all()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


def send_order_status_update_email(order: Order, new_status: str, max_retries: int = 1) -> dict:
    """
    Send order status update notifications (e.g. SHIPPED, DELIVERED, CANCELLED).
    Idempotent: prevents duplicate emails for the same status.
    """
    if order.last_status_email_sent == new_status:
        return {'status': 'already_sent', 'order_reference': order.order_reference}

    recipient_email = order.user.email if order.user else (order.guest_email or '')
    if not recipient_email:
        return {'status': 'no_recipient', 'order_reference': order.order_reference}

    customer_name = order.recipient_name or (order.user.get_full_name() if order.user else "Valued Customer")
    order_url = get_order_frontend_url(order)
    support_email = getattr(settings, 'SUPPORT_EMAIL', 'Info@adeshub.co.uk')
    reply_to = getattr(settings, 'EMAIL_REPLY_TO', 'Info@adeshub.co.uk')

    status_titles = {
        Order.OrderStatus.SHIPPED: ("AdesHub Order Dispatched", "Your Order Has Been Dispatched!", "has been dispatched and is on its way to your delivery address."),
        Order.OrderStatus.DELIVERED: ("AdesHub Order Delivered", "Your Order Has Arrived!", "has been delivered to your destination. We hope you enjoy your items!"),
        Order.OrderStatus.CANCELLED: ("AdesHub Order Cancelled", "Order Cancelled", "has been cancelled. If a refund is due, it will be processed according to our store policy."),
    }

    if new_status not in status_titles:
        return {'status': 'unsupported_status'}

    subject_prefix, heading, body_desc = status_titles[new_status]
    subject = f"{subject_prefix} -- Order #{order.order_reference}"

    # Optional shipment tracking section for dispatch notifications
    tracking_text = ""
    tracking_html = ""
    if new_status == Order.OrderStatus.SHIPPED and (order.courier_name or order.tracking_number or order.tracking_url):
        tracking_text = "\nShipment Details:\n"
        if order.courier_name:
            tracking_text += f"- Delivery Provider: {order.courier_name}\n"
        if order.tracking_number:
            tracking_text += f"- Tracking Number: {order.tracking_number}\n"
        if order.tracking_url and (order.tracking_url.startswith('https://') or order.tracking_url.startswith('http://')):
            tracking_text += f"- Tracking URL: {order.tracking_url}\n"

        courier_row = f"<p style='margin:4px 0;color:#334155;'><strong>Delivery Provider:</strong> {escape(order.courier_name)}</p>" if order.courier_name else ""
        tracking_row = f"<p style='margin:4px 0;color:#334155;'><strong>Tracking Reference:</strong> <span style='font-family:monospace;background:#f1f5f9;padding:2px 6px;border-radius:4px;'>{escape(order.tracking_number)}</span></p>" if order.tracking_number else ""
        tracking_link_row = ""
        if order.tracking_url and (order.tracking_url.startswith('https://') or order.tracking_url.startswith('http://')):
            tracking_link_row = (
                f"<div style='margin-top:12px;'>"
                f"<a href='{escape(order.tracking_url)}' target='_blank' rel='noopener noreferrer' style='display:inline-block;background:#0f172a;color:#ffffff;padding:8px 16px;border-radius:6px;text-decoration:none;font-size:13px;font-weight:600;'>"
                f"Track with Courier &rarr;"
                f"</a>"
                f"</div>"
            )

        tracking_html = f"""
        <div style="margin:20px 0;padding:16px;background-color:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;font-size:14px;">
            <h4 style="margin:0 0 10px;font-size:14px;color:#0f172a;text-transform:uppercase;letter-spacing:0.5px;">Shipment Tracking Information</h4>
            {courier_row}
            {tracking_row}
            {tracking_link_row}
        </div>
        """

    text_content = f"""Hello {customer_name},

{heading}
Your AdesHub order #{order.order_reference} {body_desc}
{tracking_text}
You can track your order status and details here:
{order_url}

Thank you for shopping with AdesHub!
The AdesHub Team
https://adeshubafricanstore.com
"""

    html_content = f"""<!DOCTYPE html>
<html>
<body style="font-family:sans-serif;color:#1e293b;background:#f8fafc;padding:32px 16px;">
    <div style="max-width:550px;margin:0 auto;background:#fff;border-radius:12px;padding:32px;border:1px solid #e2e8f0;">
        <h2 style="color:#059669;margin-top:0;">{heading}</h2>
        <p>Hello <strong>{customer_name}</strong>,</p>
        <p>Your AdesHub order <strong>#{order.order_reference}</strong> {body_desc}</p>
        {tracking_html}
        <div style="text-align:center;margin:28px 0;">
            <a href="{order_url}" style="background:#059669;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;">
                View Order Details &rarr;
            </a>
        </div>
        <p style="font-size:13px;color:#64748b;">Questions? Email us at {support_email}.</p>
    </div>
</body>
</html>
"""

    result = send_transactional_email(
        to_email=recipient_email,
        subject=subject,
        text_content=text_content,
        html_content=html_content,
        reply_to=reply_to,
        max_retries=max_retries,
    )

    if result.get('success'):
        order.last_status_email_sent = new_status
        order.save(update_fields=['last_status_email_sent', 'updated_at'])
        return {'status': 'sent', 'new_status': new_status, 'message_id': result.get('message_id')}

    return {'status': 'failed', 'new_status': new_status, 'error': result.get('error')}


def send_order_status_update_email_async(order_id: int, new_status: str):
    """Dispatch status update notification asynchronously."""
    if 'test' in sys.argv:
        order = Order.objects.filter(pk=order_id).first()
        if order:
            send_order_status_update_email(order, new_status)
        return

    def _run():
        from django.db import connections
        connections.close_all()
        try:
            order = Order.objects.filter(pk=order_id).first()
            if order:
                send_order_status_update_email(order, new_status)
        except Exception as err:
            logger.error("Async status email failed for order %s: %s", order_id, str(err))
        finally:
            connections.close_all()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
