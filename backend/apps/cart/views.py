from django.db import transaction
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from .models import Cart, CartItem
from .serializers import (
    CartSerializer,
    CartItemSerializer,
    AddCartItemSerializer,
    UpdateCartItemSerializer
)


def get_cart_session_key(request) -> str:
    """
    Get or create a consistent session key for guest cart tracking.
    Checks X-Cart-Session header first, then Django session key.
    """
    session_key = request.headers.get('X-Cart-Session')
    if not session_key or not str(session_key).strip():
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
    return str(session_key).strip()


def get_or_create_cart(request) -> Cart:
    """
    Retrieve or initialize the active Cart for an authenticated user or guest session.
    Automatically handles guest cart migration when user logs in.
    """
    session_key = get_cart_session_key(request)

    if request.user.is_authenticated:
        # Check if user already has an active cart
        cart = Cart.objects.filter(user=request.user).first()
        if not cart:
            # Check if there is a guest session cart to associate
            guest_cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first() if session_key else None
            if guest_cart:
                guest_cart.user = request.user
                guest_cart.save()
                cart = guest_cart
            else:
                cart = Cart.objects.create(user=request.user, session_key=session_key)
        return cart

    # Guest user - strictly match guest carts
    cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first() if session_key else None
    if not cart:
        cart = Cart.objects.create(session_key=session_key)

    return cart


class CartDetailView(APIView):
    """
    GET /api/cart/ - Retrieve current cart.
    DELETE /api/cart/ - Clear all items from cart.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        cart = get_or_create_cart(request)
        serializer = CartSerializer(cart, context={'request': request})
        response = Response(serializer.data, status=status.HTTP_200_OK)
        session_key = get_cart_session_key(request)
        if session_key:
            response['X-Cart-Session'] = session_key
        return response

    def delete(self, request):
        cart = get_or_create_cart(request)
        cart.items.all().delete()
        serializer = CartSerializer(cart, context={'request': request})
        response = Response(serializer.data, status=status.HTTP_200_OK)
        session_key = get_cart_session_key(request)
        if session_key:
            response['X-Cart-Session'] = session_key
        return response


class CartItemAddView(APIView):
    """
    POST /api/cart/items/ - Add product or variant to cart.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        cart = get_or_create_cart(request)
        serializer = AddCartItemSerializer(data=request.data, context={'cart': cart, 'request': request})

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        product = serializer.validated_data['product']
        variant = serializer.validated_data.get('variant')
        quantity = serializer.validated_data.get('quantity', 1)

        with transaction.atomic():
            cart_item, created = CartItem.objects.select_for_update().get_or_create(
                cart=cart,
                product=product,
                variant=variant,
                defaults={'quantity': quantity}
            )

            if not created:
                cart_item.quantity += quantity
                cart_item.save()

        cart.refresh_from_db()
        cart_serializer = CartSerializer(cart, context={'request': request})
        response = Response(cart_serializer.data, status=status.HTTP_201_CREATED)
        session_key = get_cart_session_key(request)
        if session_key:
            response['X-Cart-Session'] = session_key
        return response


class CartItemDetailView(APIView):
    """
    PATCH /api/cart/items/<id>/ - Update cart item quantity.
    DELETE /api/cart/items/<id>/ - Remove item from cart.
    """
    permission_classes = [AllowAny]

    def patch(self, request, pk):
        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, pk=pk, cart=cart)

        serializer = UpdateCartItemSerializer(
            data=request.data,
            context={'cart_item': cart_item, 'cart': cart, 'request': request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            cart_item.quantity = serializer.validated_data['quantity']
            cart_item.save()

        cart.refresh_from_db()
        cart_serializer = CartSerializer(cart, context={'request': request})
        response = Response(cart_serializer.data, status=status.HTTP_200_OK)
        session_key = get_cart_session_key(request)
        if session_key:
            response['X-Cart-Session'] = session_key
        return response

    def put(self, request, pk):
        return self.patch(request, pk)

    def delete(self, request, pk):
        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, pk=pk, cart=cart)
        with transaction.atomic():
            cart_item.delete()

        cart.refresh_from_db()
        cart_serializer = CartSerializer(cart, context={'request': request})
        response = Response(cart_serializer.data, status=status.HTTP_200_OK)
        session_key = get_cart_session_key(request)
        if session_key:
            response['X-Cart-Session'] = session_key
        return response

