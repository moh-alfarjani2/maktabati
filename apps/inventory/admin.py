from django.contrib import admin
from .models import InventoryMovement, StockTaking, StockTakingItem

@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'movement_type', 'quantity_change', 'quantity_after', 'created_at', 'user')
    list_filter = ('movement_type', 'created_at')
    search_fields = ('product__name', 'reference')
    readonly_fields = ('quantity_after', 'created_at')

class StockTakingItemInline(admin.TabularInline):
    model = StockTakingItem
    extra = 1

@admin.register(StockTaking)
class StockTakingAdmin(admin.ModelAdmin):
    list_display = ('session_name', 'conducted_by', 'started_at', 'completed_at')
    inlines = [StockTakingItemInline]
