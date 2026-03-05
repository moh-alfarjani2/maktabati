from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count, F
from django.utils import timezone
from datetime import timedelta
from apps.sales.models import SaleInvoice, InvoiceItem
from apps.books.models import Product
from apps.inventory.models import InventoryMovement
from apps.accounts.decorators import role_required
from django.utils.decorators import method_decorator

@method_decorator(role_required(allowed_roles=['admin']), name='dispatch')
class reportsDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        last_30_days = today - timedelta(days=30)

        # 1. Sales Statistics (Excluding cancelled)
        sales_active = SaleInvoice.objects.filter(created_at__date__gte=last_30_days).exclude(status='cancelled')
        context['total_sales_30'] = sales_active.aggregate(total=Sum('total_amount'))['total'] or 0
        context['total_invoices_30'] = sales_active.count()

        # Profit Calculation for last 30 days
        context['total_profit_30'] = sales_active.aggregate(total=Sum('profit_amount'))['total'] or 0

        # 2. Top Selling Books (Excluding cancelled)
        top_books = InvoiceItem.objects.exclude(invoice__status='cancelled') \
            .values('product__name') \
            .annotate(total_qty=Sum('quantity'), total_revenue=Sum('subtotal')) \
            .order_by('-total_qty')[:5]
        context['top_books'] = top_books

        # 3. Inventory Health
        context['low_stock_count'] = Product.objects.filter(current_stock__lte=F('min_stock_level')).count()
        context['out_of_stock_count'] = Product.objects.filter(current_stock__lte=0).count()

        # 4. Chart Data (Sales per day for last 7 days)
        last_7_days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
        chart_labels = [d.strftime('%m-%d') for d in last_7_days]
        chart_values = []
        for day in last_7_days:
            val = SaleInvoice.objects.filter(created_at__date=day).exclude(status='cancelled').aggregate(total=Sum('total_amount'))['total'] or 0
            chart_values.append(float(val))
        
        context['chart_labels'] = chart_labels
        context['chart_values'] = chart_values

        return context

@method_decorator(role_required(allowed_roles=['admin']), name='dispatch')
class SalesReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/sales.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.sales.models import SaleInvoice
        from django.db.models import Sum
        import datetime

        qs = SaleInvoice.objects.select_related('customer', 'cashier').order_by('-created_at')

        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        payment_method = self.request.GET.get('payment_method')

        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        if payment_method:
            qs = qs.filter(payment_method=payment_method)

        qs = qs.exclude(status='cancelled')

        context['invoices'] = qs
        agg = qs.aggregate(
            total_sales=Sum('total_amount'),
            total_tax=Sum('tax_amount'),
        )
        context['total_sales'] = agg['total_sales'] or 0
        context['total_tax'] = agg['total_tax'] or 0
        context['invoice_count'] = qs.count()
        return context
