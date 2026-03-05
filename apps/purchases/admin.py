from django.contrib import admin
from .models import Supplier, PurchaseInvoice, PurchaseInvoiceItem, SupplierPayment


class PurchaseInvoiceItemInline(admin.TabularInline):
    model = PurchaseInvoiceItem
    extra = 1
    readonly_fields = ('total_price',)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'contact_person', 'balance_due')
    search_fields = ('name', 'phone')


@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_id', 'supplier', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('invoice_id', 'supplier__name')
    inlines = [PurchaseInvoiceItemInline]
    readonly_fields = ('invoice_id', 'subtotal', 'total_amount', 'amount_due')


@admin.register(SupplierPayment)
class SupplierPaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'supplier', 'amount', 'payment_method', 'payment_date')
    readonly_fields = ('payment_id',)
