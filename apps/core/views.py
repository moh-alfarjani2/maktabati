import json
from django.views.generic import ListView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.core import serializers
from django.http import HttpResponse
from .models import SystemSettings
from apps.sales.models import SaleInvoice
from apps.books.models import Product
from django.db import models
from django.db.models import Sum, F
from django.utils import timezone
from django.apps import apps
from apps.accounts.decorators import role_required
from apps.accounts.models import ActivityLog
from django.utils.decorators import method_decorator

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        seven_days_ago = today - timezone.timedelta(days=7)
        
        # Core Stats
        completed_sales = SaleInvoice.objects.filter(created_at__date=today, status='completed')
        context['today_sales'] = completed_sales.aggregate(total=Sum('total_amount'))['total'] or 0
        context['today_profit'] = completed_sales.aggregate(total=Sum('profit_amount'))['total'] or 0
        context['invoice_count'] = completed_sales.count()
        
        # Inventory Stats
        context['low_stock_count'] = Product.objects.filter(current_stock__lte=F('min_stock_level')).count()
        context['total_products'] = Product.objects.count()
        context['inventory_value'] = Product.objects.aggregate(
            total=Sum(F('current_stock') * F('avg_cost'), output_field=models.DecimalField())
        )['total'] or 0
        
        # Chart Data: Last 7 Days Sales
        from django.db.models.functions import TruncDate
        daily_sales = SaleInvoice.objects.filter(
            created_at__date__gte=seven_days_ago, 
            status='completed'
        ).annotate(date=TruncDate('created_at')).values('date').annotate(
            total=Sum('total_amount')
        ).order_by('date')
        
        labels = []
        values = []
        for i in range(7):
            d = seven_days_ago + timezone.timedelta(days=i+1)
            labels.append(d.strftime('%Y-%m-%d'))
            day_sale = next((item['total'] for item in daily_sales if item['date'] == d), 0)
            values.append(float(day_sale))
        
        context['labels'] = json.dumps(labels)
        context['values'] = json.dumps(values)
        
        # Top Selling Products
        from apps.sales.models import InvoiceItem
        top_products = InvoiceItem.objects.filter(
            invoice__status='completed',
            invoice__created_at__date__gte=seven_days_ago
        ).values('product__name').annotate(
            total_qty=Sum('quantity')
        ).order_by('-total_qty')[:5]
        
        context['top_products_labels'] = json.dumps([p['product__name'] for p in top_products])
        context['top_products_values'] = json.dumps([float(p['total_qty']) for p in top_products])

        # Recent Items
        context['recent_invoices'] = SaleInvoice.objects.select_related('customer').order_by('-created_at')[:5]
        context['low_stock_items'] = Product.objects.filter(current_stock__lte=F('min_stock_level'))[:6]
        
        return context

@method_decorator(role_required(allowed_roles=['admin']), name='dispatch')
class SettingsView(LoginRequiredMixin, ListView):
    model = SystemSettings
    template_name = 'core/settings.html'
    context_object_name = 'settings_list'

    def post(self, request, *args, **kwargs):
        for key, value in request.POST.items():
            if key != 'csrfmiddlewaretoken':
                # Special handling for JSON fields if needed, 
                # but SystemSettings.value is TextField so it should be fine.
                SystemSettings.objects.filter(key=key).update(value=value)
        
        messages.success(request, "تم تحديث الإعدادات بنجاح")
        ActivityLog.objects.create(
            user=request.user,
            action="تحديث إعدادات النظام",
            details="تم تعديل إعدادات النظام من واجهة الإعدادات"
        )
        return redirect('settings')

@method_decorator(role_required(allowed_roles=['admin']), name='dispatch')
class BackupView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # Comprehensive JSON backup of all app models
        all_models = []
        for app_config in apps.get_app_configs():
            if app_config.name.startswith('apps.'):
                for model in app_config.get_models():
                    all_models.extend(list(model.objects.all()))
        
        data = serializers.serialize("json", all_models)
        
        response = HttpResponse(data, content_type="application/json")
        response['Content-Disposition'] = f'attachment; filename="backup_{timezone.now().strftime("%Y-%m-%d")}.json"'
        return response
