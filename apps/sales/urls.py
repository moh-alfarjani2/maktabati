from django.urls import path
from . import views # Changed import style to use 'views' module

urlpatterns = [
    path('pos/', views.POSView.as_view(), name='pos'),
    path('pos/finalize/', views.POSFinalizeView.as_view(), name='pos_finalize'),
    path('invoices/', views.InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/<str:invoice_id>/pdf/', views.export_invoice_pdf, name='invoice_pdf'),
    path('invoices/<str:invoice_id>/cancel/', views.InvoiceCancelView.as_view(), name='invoice_cancel'),
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/add/', views.CustomerCreateView.as_view(), name='customer_add'),
    path('pos/recommend/<int:product_id>/', views.POSRecommendView.as_view(), name='pos_recommend'),
    path('pos/search/', views.search_product, name='pos_search'),
    path('pos/add-customer/', views.add_customer_ajax, name='pos_add_customer'),
]
