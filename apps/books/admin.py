from django.contrib import admin
from .models import Category, Product, ProductBarcode, ProductUnit


class ProductBarcodeInline(admin.TabularInline):
    model = ProductBarcode
    extra = 1


class ProductUnitInline(admin.TabularInline):
    model = ProductUnit
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_id', 'selling_price', 'current_stock', 'avg_cost', 'is_active')
    list_filter = ('categories', 'is_active')
    search_fields = ('name', 'product_id')
    readonly_fields = ('product_id', 'avg_cost', 'last_purchase_price', 'profit_margin')
    inlines = [ProductBarcodeInline, ProductUnitInline]
