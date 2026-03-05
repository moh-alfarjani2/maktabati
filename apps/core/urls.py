from django.urls import path
from .views import DashboardView, SettingsView, BackupView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('settings/', SettingsView.as_view(), name='settings'),
    path('backup/', BackupView.as_view(), name='backup'),
]
