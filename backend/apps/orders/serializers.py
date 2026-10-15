from decimal import Decimal
from rest_framework import serializers
from apps.accounts.serializers import AddressSerializer
from .models import Order, OrderItem, DeliveryMethod


class DeliveryMethodSerializer(serializers.ModelSerializer):
    """
    Serializer for configurable store delivery methods.
    """
    class Meta:
        model = DeliveryMethod
        fields = (
            'id',
            'name',
            'code',
            'description',
            'base_fee',
            'free_delivery_threshold',
            'estimated_days',
            'is_active',
            'is_default',
            'display_order',
        )


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for OrderItem line items representation.
    """
    class Meta:
        model = OrderItem
        fields = (
            'id',
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


class OrderSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for detailed Order representation.
    Includes delivery snapshot, courier & shipment tracking, and financial breakdown.
    """
    items = OrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            'id',
            'order_reference',
            'customer_name',
            'customer_email',
            'recipient_name',
            'phone_number',
            'address_line1',
            'address_line2',
            'city',
            'county_region',
            'postal_code',
            'country',
            'subtotal',
            'delivery_fee',
            'total_amount',
            'order_status',
            'payment_status',
            'delivery_method_name',
            'courier_name',
            'shipment_reference',
            'tracking_number',
            'tracking_url',
            'dispatched_at',
            'delivered_at',
            'stripe_checkout_session_id',
            'stripe_payment_intent_id',
            'confirmation_email_sent',
            'confirmation_email_sent_at',
            'email_delivery_status',
            'inventory_restored',
            'inventory_restored_at',
            'notes',
            'items',
            'created_at',
            'updated_at',
        )

    def get_customer_name(self, obj):
        if obj.user:
            return obj.user.get_full_name()
        return obj.recipient_name

    def get_customer_email(self, obj):
        if obj.user:
            return obj.user.email
        return obj.guest_email


class CreateOrderSerializer(serializers.Serializer):
    """
    Serializer for creating an order from the active cart.
    Accepts address selection (address_id) or direct address input,
    and optional delivery method code.
    """
    address_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    delivery_method_code = serializers.CharField(max_length=50, required=False, default='standard')

    recipient_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    phone_number = serializers.CharField(max_length=30, required=False, allow_blank=True)
    address_line1 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    address_line2 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    county_region = serializers.CharField(max_length=100, required=False, allow_blank=True)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100, default='United Kingdom', required=False)

    guest_email = serializers.EmailField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        address_id = attrs.get('address_id')
        request = self.context.get('request')

        # If user is authenticated and address_id is provided, address fields are loaded from Address object
        if address_id:
            from apps.accounts.models import Address
            user = request.user if request and request.user.is_authenticated else None
            if not user:
                raise serializers.ValidationError({'address_id': 'Must be logged in to select saved address.'})
            address = Address.objects.filter(pk=address_id, user=user).first()
            if not address:
                raise serializers.ValidationError({'address_id': 'Selected address was not found in your saved addresses.'})
            attrs['address_obj'] = address
        else:
            # Validate direct address fields
            required_fields = ['recipient_name', 'phone_number', 'address_line1', 'city', 'postal_code']
            missing = [field for field in required_fields if not attrs.get(field) or not str(attrs.get(field)).strip()]
            if missing:
                errors = {field: ['This field is required for delivery.'] for field in missing}
                raise serializers.ValidationError(errors)

        return attrs

