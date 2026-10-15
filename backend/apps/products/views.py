from typing import Any
from rest_framework import generics, status, filters
from rest_framework.response import Response
from django.db.models import Q
from django.shortcuts import get_object_or_404
from .models import Category, Product, ProductVariant, ProductImage
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductVariantSerializer,
    ProductImageSerializer
)
from .permissions import IsAdminOrReadOnly


class CategoryListCreateView(generics.ListCreateAPIView):
    """
    API View to list categories (Public) and create categories (Staff/Admin).
    """
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'
    pagination_class = None

    def get_queryset(self):
        queryset = Category.objects.all()
        # Non-staff users see only active categories
        if not (self.request.user and getattr(self.request.user, 'is_staff', False)):
            queryset = queryset.filter(is_active=True)
        return queryset.order_by('name')


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API View to retrieve, update, or delete a category by slug.
    """
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'

    def get_queryset(self):
        queryset = Category.objects.all()
        if not (self.request.user and getattr(self.request.user, 'is_staff', False)):
            queryset = queryset.filter(is_active=True)
        return queryset


class ProductListCreateView(generics.ListCreateAPIView):
    """
    API View to list products with search and filtering (Public) and create products (Staff/Admin).
    """
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductDetailSerializer
        return ProductListSerializer

    def get_queryset(self):
        queryset = Product.objects.select_related('category').prefetch_related('images', 'variants').all()

        # Non-staff users see active products only
        if not (self.request.user and getattr(self.request.user, 'is_staff', False)):
            queryset = queryset.filter(is_active=True)

        request: Any = self.request

        # Filtering by Category slug
        category_slug = request.query_params.get('category', None)
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        # Filtering by Featured flag
        featured = request.query_params.get('featured', None)
        if featured is not None:
            is_featured = str(featured).lower() in ('true', '1', 'yes')
            queryset = queryset.filter(is_featured=is_featured)

        # Filtering by In Stock status
        in_stock = request.query_params.get('in_stock', None)
        if in_stock is not None:
            is_in_stock = str(in_stock).lower() in ('true', '1', 'yes')
            if is_in_stock:
                queryset = queryset.filter(
                    Q(has_variants=False, stock_quantity__gt=0) |
                    Q(has_variants=True, variants__is_active=True, variants__stock_quantity__gt=0)
                ).distinct()

        # Search functionality (by name, description, SKU)
        search_query = request.query_params.get('search', None)
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(sku__icontains=search_query)
            )

        return queryset.order_by('-created_at')


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API View to retrieve, update, or delete a product by slug.
    """
    serializer_class = ProductDetailSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'

    def get_queryset(self):
        queryset = Product.objects.select_related('category').prefetch_related('images', 'variants').all()
        if not (self.request.user and getattr(self.request.user, 'is_staff', False)):
            queryset = queryset.filter(is_active=True)
        return queryset


class ProductVariantListCreateView(generics.ListCreateAPIView):
    """
    API View to list or create variants for a specific product.
    """
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        product_slug = self.kwargs.get('product_slug')
        product = get_object_or_404(Product, slug=product_slug)
        queryset = ProductVariant.objects.filter(product=product)
        if not (self.request.user and getattr(self.request.user, 'is_staff', False)):
            queryset = queryset.filter(is_active=True)
        return queryset

    def perform_create(self, serializer):
        product_slug = self.kwargs.get('product_slug')
        product = get_object_or_404(Product, slug=product_slug)
        serializer.save(product=product)
        # Enable has_variants flag on product automatically
        if not product.has_variants:
            product.has_variants = True
            product.save(update_fields=['has_variants'])


class ProductImageListCreateView(generics.ListCreateAPIView):
    """
    API View to list or create images for a specific product.
    """
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        product_slug = self.kwargs.get('product_slug')
        product = get_object_or_404(Product, slug=product_slug)
        return ProductImage.objects.filter(product=product)

    def perform_create(self, serializer):
        product_slug = self.kwargs.get('product_slug')
        product = get_object_or_404(Product, slug=product_slug)
        serializer.save(product=product)


class ProductVariantDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API View to retrieve, update, or delete a specific variant of a product.
    """
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'pk'

    def get_queryset(self):
        product_slug = self.kwargs.get('product_slug')
        product = get_object_or_404(Product, slug=product_slug)
        return ProductVariant.objects.filter(product=product)

    def perform_destroy(self, instance):
        product = instance.product
        instance.delete()
        if not product.variants.filter(is_active=True).exists():
            product.has_variants = False
            product.save(update_fields=['has_variants'])


class ProductImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API View to retrieve, update, or delete a specific image of a product.
    """
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'pk'

    def get_queryset(self):
        product_slug = self.kwargs.get('product_slug')
        product = get_object_or_404(Product, slug=product_slug)
        return ProductImage.objects.filter(product=product)

    def perform_destroy(self, instance):
        product = instance.product
        was_primary = instance.is_primary
        instance.delete()
        if was_primary:
            next_img = product.images.first()
            if next_img:
                next_img.is_primary = True
                next_img.save(update_fields=['is_primary'])

