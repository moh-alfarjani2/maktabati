from django.urls import path
from .views import (
    SupplierListView, SupplierCreateView, 
    PurchaseInvoiceListView, PurchaseInvoiceCreateView, 
    PurchaseInvoiceDetailView, PurchaseInvoiceUpdateView, 
    approve_invoice
)

urlpatterns = [
    path('suppliers/', SupplierListView.as_view(), name='supplier_list'),
    path('suppliers/add/', SupplierCreateView.as_view(), name='supplier_add'),
    path('invoices/', PurchaseInvoiceListView.as_view(), name='invoice_purchase_list'),
    path('invoices/add/', PurchaseInvoiceCreateView.as_view(), name='invoice_add'),
    path('invoices/<str:invoice_id>/', PurchaseInvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/<str:invoice_id>/edit/', PurchaseInvoiceUpdateView.as_view(), name='invoice_edit'),
    path('invoices/<str:invoice_id>/approve/', approve_invoice, name='approve_invoice'),
]
