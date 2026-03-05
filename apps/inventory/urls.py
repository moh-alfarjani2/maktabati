from django.urls import path
from . import views

urlpatterns = [
    path('stock/', views.InventoryListView.as_view(), name='inventory_list'),
    path('movements/', views.MovementLogView.as_view(), name='movement_log'),
    path('stocktaking/', views.StockTakingListView.as_view(), name='stocktaking_list'),
    path('stocktaking/add/', views.StockTakingCreateView.as_view(), name='stocktaking_add'),
    path('stocktaking/<int:pk>/', views.StockTakingDetailView.as_view(), name='stocktaking_detail'),
]
