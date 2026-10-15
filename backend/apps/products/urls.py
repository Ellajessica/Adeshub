from django.urls import path
from .views import (
    CategoryListCreateView,
    CategoryDetailView,
    ProductListCreateView,
    ProductDetailView,
    ProductVariantListCreateView,
    ProductVariantDetailView,
    ProductImageListCreateView,
    ProductImageDetailView,
)

app_name = 'products'

urlpatterns = [
    # Categories Endpoints
    path('categories/', CategoryListCreateView.as_view(), name='category-list'),
    path('categories/<slug:slug>/', CategoryDetailView.as_view(), name='category-detail'),

    # Products Endpoints
    path('products/', ProductListCreateView.as_view(), name='product-list'),
    path('products/<slug:slug>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/<slug:product_slug>/variants/', ProductVariantListCreateView.as_view(), name='product-variant-list'),
    path('products/<slug:product_slug>/variants/<int:pk>/', ProductVariantDetailView.as_view(), name='product-variant-detail'),
    path('products/<slug:product_slug>/images/', ProductImageListCreateView.as_view(), name='product-image-list'),
    path('products/<slug:product_slug>/images/<int:pk>/', ProductImageDetailView.as_view(), name='product-image-detail'),
]
