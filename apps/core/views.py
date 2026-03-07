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
        now = timezone.now()
        today = now.date()

        # --- Date Range Filtering ---
        date_from_str = self.request.GET.get('date_from', '')
        date_to_str = self.request.GET.get('date_to', '')

        try:
            if date_from_str:
                from django.utils.dateparse import parse_datetime
                dt_from = parse_datetime(date_from_str)
                if not dt_from:
                    from datetime import datetime
                    dt_from = datetime.strptime(date_from_str, '%Y-%m-%dT%H:%M')
                dt_from = timezone.make_aware(dt_from) if timezone.is_naive(dt_from) else dt_from
            else:
                # Default: start of today
                dt_from = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
        except Exception:
            dt_from = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))

        try:
            if date_to_str:
                from django.utils.dateparse import parse_datetime
                dt_to = parse_datetime(date_to_str)
                if not dt_to:
                    from datetime import datetime
                    dt_to = datetime.strptime(date_to_str, '%Y-%m-%dT%H:%M')
                dt_to = timezone.make_aware(dt_to) if timezone.is_naive(dt_to) else dt_to
            else:
                # Default: now
                dt_to = now
        except Exception:
            dt_to = now

        context['today_date'] = today
        if dt_from > dt_to:
            dt_from, dt_to = dt_to, dt_from

        context['date_from'] = dt_from.strftime('%Y-%m-%dT%H:%M')
        context['date_to'] = dt_to.strftime('%Y-%m-%dT%H:%M')
        context['date_from_display'] = dt_from.strftime('%Y/%m/%d %H:%M')
        context['date_to_display'] = dt_to.strftime('%Y/%m/%d %H:%M')

        # --- Core Stats (filtered by date range) ---
        completed_sales = SaleInvoice.objects.filter(
            created_at__gte=dt_from, created_at__lte=dt_to, status='completed'
        )
        context['today_sales'] = completed_sales.aggregate(total=Sum('total_amount'))['total'] or 0
        context['today_profit'] = completed_sales.aggregate(total=Sum('profit_amount'))['total'] or 0
        context['invoice_count'] = completed_sales.count()

        # --- Inventory Stats (not time-filtered, always current) ---
        context['low_stock_count'] = Product.objects.filter(current_stock__lte=F('min_stock_level')).count()
        context['total_products'] = Product.objects.count()
        from django.db.models import Case, When, DecimalField
        raw_val = Product.objects.aggregate(
            total=Sum(
                F('current_stock') * Case(
                    When(avg_cost__gt=0, then=F('avg_cost')),
                    default=F('purchase_price'),
                    output_field=DecimalField()
                ),
                output_field=DecimalField()
            )
        )['total'] or 0
        context['inventory_value'] = round(float(raw_val), 2)

        # --- Chart Data: Dynamic grouping based on range ---
        from django.db.models.functions import TruncDate, TruncMonth
        from datetime import timedelta
        import calendar

        delta_days = (dt_to.date() - dt_from.date()).days
        labels = []
        values = []

        if delta_days > 31:
            # Group by month
            sales_data = SaleInvoice.objects.filter(
                created_at__gte=dt_from,
                created_at__lte=dt_to,
                status='completed'
            ).annotate(period=TruncMonth('created_at')).values('period').annotate(
                total=Sum('total_amount')
            ).order_by('period')
            
            curr = dt_from.date().replace(day=1)
            end = dt_to.date().replace(day=1)
            while curr <= end:
                month_str = curr.strftime('%Y-%m')
                labels.append(month_str)
                month_sale = next((item['total'] for item in sales_data if item['period'].strftime('%Y-%m') == month_str), 0)
                values.append(float(month_sale))
                days_in_month = calendar.monthrange(curr.year, curr.month)[1]
                curr += timedelta(days=days_in_month)
        else:
            # Group by day
            daily_sales = SaleInvoice.objects.filter(
                created_at__gte=dt_from,
                created_at__lte=dt_to,
                status='completed'
            ).annotate(period=TruncDate('created_at')).values('period').annotate(
                total=Sum('total_amount')
            ).order_by('period')

            delta = delta_days + 1
            for i in range(delta):
                d = dt_from.date() + timedelta(days=i)
                labels.append(d.strftime('%Y-%m-%d'))
                day_sale = next((item['total'] for item in daily_sales if item['period'] == d), 0)
                values.append(float(day_sale))

        context['labels'] = json.dumps(labels)
        context['values'] = json.dumps(values)

        # --- Top Selling Products (filtered) ---
        from apps.sales.models import InvoiceItem
        top_products = InvoiceItem.objects.filter(
            invoice__status='completed',
            invoice__created_at__gte=dt_from,
            invoice__created_at__lte=dt_to,
        ).values('product__name').annotate(
            total_qty=Sum('quantity')
        ).order_by('-total_qty')[:5]

        context['top_products_labels'] = json.dumps([p['product__name'] for p in top_products])
        context['top_products_values'] = json.dumps([float(p['total_qty']) for p in top_products])

        # Recent Items (always latest 5)
        context['recent_invoices'] = SaleInvoice.objects.select_related('customer').filter(
            created_at__gte=dt_from, created_at__lte=dt_to
        ).order_by('-created_at')[:5]
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
