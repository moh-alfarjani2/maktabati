from django.urls import path
from .views import reportsDashboardView, SalesReportView

urlpatterns = [
    path('', reportsDashboardView.as_view(), name='reports_dashboard'),
    path('sales/', SalesReportView.as_view(), name='reports_sales'),
]
