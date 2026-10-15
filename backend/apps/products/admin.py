from django.contrib import admin
from .models import Category, Product, ProductVariant, ProductImage


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('name', 'sku', 'price', 'compare_at_price', 'stock_quantity', 'is_active')


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'is_primary', 'display_order')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'product_count', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)

    @admin.display(description='Products')
    def product_count(self, obj):
        return obj.products.count()


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'sku',
        'category',
        'price',
        'compare_at_price',
        'stock_quantity',
        'get_total_stock',
        'has_variants',
        'is_featured',
        'is_active',
        'created_at'
    )
    list_filter = ('category', 'is_active', 'is_featured', 'has_variants', 'created_at')
    search_fields = ('name', 'sku', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductVariantInline, ProductImageInline]
    ordering = ('-created_at',)
    list_editable = ('price', 'is_active', 'is_featured')

    @admin.display(description='Total Stock')
    def get_total_stock(self, obj):
        return obj.total_stock


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'name', 'sku', 'price', 'stock_quantity', 'is_active', 'created_at')
    list_filter = ('is_active', 'product__category')
    search_fields = ('name', 'sku', 'product__name')
    ordering = ('product', 'name')
    list_editable = ('price', 'stock_quantity', 'is_active')


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'is_primary', 'display_order', 'created_at')
    list_filter = ('is_primary', 'created_at')
    search_fields = ('product__name', 'alt_text')
    ordering = ('product', 'display_order')
