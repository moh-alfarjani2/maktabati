from django.urls import path
from . import views

app_name = 'damages'

urlpatterns = [
    path('', views.damage_list, name='list'),
    path('new/', views.damage_create, name='create'),
    path('<str:loss_id>/', views.damage_detail, name='detail'),
    path('<str:loss_id>/approve/', views.damage_approve, name='approve'),
    path('<str:loss_id>/pdf/', views.export_damage_pdf, name='pdf'),
]
