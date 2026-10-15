from rest_framework import serializers
from ..products.models import Product, ProductVariant
from .models import Cart, CartItem


class CartItemProductSerializer(serializers.ModelSerializer):
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'slug',
            'sku',
            'primary_image',
            'price',
            'has_variants',
            'is_active',
            'is_in_stock',
            'stock_quantity',
        ]

    def get_primary_image(self, obj):
        img = obj.primary_image
        if img and img.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(img.image.url)
            return img.image.url
        return None


class CartItemVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = [
            'id',
            'name',
            'sku',
            'price',
            'is_active',
            'is_in_stock',
            'stock_quantity',
        ]


class CartItemSerializer(serializers.ModelSerializer):
    product = CartItemProductSerializer(read_only=True)
    variant = CartItemVariantSerializer(read_only=True)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = [
            'id',
            'product',
            'variant',
            'quantity',
            'unit_price',
            'line_total',
            'created_at',
            'updated_at',
        ]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_quantity = serializers.IntegerField(read_only=True)
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = [
            'id',
            'items',
            'subtotal',
            'total_quantity',
            'item_count',
            'created_at',
            'updated_at',
        ]


class AddCartItemSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    variant = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.all(),
        required=False,
        allow_null=True,
        default=None
    )
    quantity = serializers.IntegerField(default=1)

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value

    def validate(self, attrs):
        product = attrs.get('product')
        variant = attrs.get('variant')
        quantity = attrs.get('quantity', 1)
        cart = self.context.get('cart')

        if not product.is_active:
            raise serializers.ValidationError({"product": "Sorry, this product is currently unavailable."})

        if product.has_variants:
            if not variant:
                raise serializers.ValidationError({"variant": "Please select a product variant before adding to cart."})
            if variant.product_id != product.id:
                raise serializers.ValidationError({"variant": "The selected variant does not belong to this product."})
            if not variant.is_active:
                raise serializers.ValidationError({"variant": "Selected variant is currently unavailable."})
            stock = variant.stock_quantity
        else:
            if variant:
                raise serializers.ValidationError({"variant": "Variants are not available for this simple product."})
            stock = product.stock_quantity

        if stock <= 0:
            raise serializers.ValidationError({"quantity": "Sorry, this item is currently out of stock."})

        # Calculate current quantity already in cart if adding to an existing line
        existing_quantity = 0
        if cart:
            existing_item = CartItem.objects.filter(cart=cart, product=product, variant=variant).first()
            if existing_item:
                existing_quantity = existing_item.quantity

        total_requested = existing_quantity + quantity
        if total_requested > stock:
            raise serializers.ValidationError({
                "quantity": f"Only {stock} available in stock. You already have {existing_quantity} in your cart."
                if existing_quantity > 0 else f"Only {stock} available."
            })

        return attrs


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField()

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value

    def validate(self, attrs):
        quantity = attrs.get('quantity')
        cart_item = self.context.get('cart_item')

        if cart_item:
            product = cart_item.product
            variant = cart_item.variant

            if not product.is_active or (variant and not variant.is_active):
                raise serializers.ValidationError({"detail": "This item is no longer available."})

            stock = variant.stock_quantity if variant else product.stock_quantity

            if stock <= 0:
                raise serializers.ValidationError({"quantity": "This item is currently out of stock."})

            if quantity > stock:
                raise serializers.ValidationError({"quantity": f"Only {stock} available in stock."})

        return attrs
