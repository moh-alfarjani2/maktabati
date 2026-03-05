from django.urls import path
from .views import (
    ProductListView, ProductCreateView, ProductUpdateView, 
    export_products_excel, import_products_excel,
    product_search_ajax, api_get_product_by_barcode, product_delete,
    api_search_categories, api_create_category, api_package_types,
    api_author_suggestions
)

urlpatterns = [
    path('', ProductListView.as_view(), name='product_list'),
    path('add/', ProductCreateView.as_view(), name='product_add'),
    path('edit/<str:product_id>/', ProductUpdateView.as_view(), name='product_edit'),
    path('export/', export_products_excel, name='product_export'),
    path('import/', import_products_excel, name='product_import'),
    path('search-ajax/', product_search_ajax, name='product_search_ajax'),
    path('api/barcode/', api_get_product_by_barcode, name='api_get_product_by_barcode'),
    path('delete/<str:product_id>/', product_delete, name='product_delete'),
    path('api/categories/search/', api_search_categories, name='api_search_categories'),
    path('api/categories/create/', api_create_category, name='api_create_category'),
    path('api/package-types/', api_package_types, name='api_package_types'),
    path('api/authors/', api_author_suggestions, name='api_author_suggestions'),
]
