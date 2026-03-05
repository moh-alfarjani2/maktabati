from django.contrib import admin
from .models import Customer, SaleInvoice, InvoiceItem, SalesReturn


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'balance_due')
    search_fields = ('name', 'phone')


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    readonly_fields = ('subtotal',)


@admin.register(SaleInvoice)
class SaleInvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_id', 'customer', 'cashier', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('invoice_id', 'customer__name')
    inlines = [InvoiceItemInline]
    readonly_fields = ('invoice_id', 'subtotal', 'tax_amount', 'total_amount', 'amount_due', 'profit_amount')


@admin.register(SalesReturn)
class SalesReturnAdmin(admin.ModelAdmin):
    list_display = ('return_id', 'original_invoice', 'total_refund', 'created_at')
    readonly_fields = ('return_id',)
