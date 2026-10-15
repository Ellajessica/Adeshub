from django.contrib import admin
from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ('product', 'variant', 'quantity', 'unit_price', 'line_total')
    readonly_fields = ('unit_price', 'line_total')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session_key', 'total_quantity', 'subtotal', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('session_key', 'user__email', 'user__username')
    readonly_fields = ('subtotal', 'total_quantity', 'item_count', 'created_at', 'updated_at')
    inlines = [CartItemInline]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart', 'product', 'variant', 'quantity', 'unit_price', 'line_total', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('product__name', 'variant__name', 'cart__session_key')
    readonly_fields = ('unit_price', 'line_total', 'created_at', 'updated_at')
