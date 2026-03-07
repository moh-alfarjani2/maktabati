from django.views.generic import ListView, CreateView, DetailView, UpdateView
from django.db import models
from apps.books.models import Product
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from .models import Supplier, PurchaseInvoice, PurchaseInvoiceItem, SupplierPayment
from apps.inventory.models import InventoryMovement
from apps.accounts.decorators import role_required
from apps.accounts.models import ActivityLog
from decimal import Decimal
import json
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from apps.core.models import SystemSettings

@method_decorator(role_required(allowed_roles=['admin', 'storekeeper']), name='dispatch')
class SupplierListView(LoginRequiredMixin, ListView):
    model = Supplier
    template_name = 'purchases/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q')
        sort = self.request.GET.get('sort')
        direction = self.request.GET.get('dir', 'asc')

        if q:
            queryset = queryset.filter(models.Q(name__icontains=q) | models.Q(phone__icontains=q))

        if sort:
            valid_sorts = ['name', 'phone', 'email', 'balance_due', 'created_at']
            if sort in valid_sorts:
                if direction == 'desc':
                    sort = f"-{sort}"
                queryset = queryset.order_by(sort)
        else:
            queryset = queryset.order_by('name')

        return queryset

@method_decorator(role_required(allowed_roles=['admin', 'storekeeper']), name='dispatch')
class SupplierCreateView(LoginRequiredMixin, CreateView):
    model = Supplier
    template_name = 'purchases/supplier_form.html'
    fields = ['name', 'contact_person', 'phone', 'email', 'address']
    success_url = reverse_lazy('supplier_list')

@method_decorator(role_required(allowed_roles=['admin', 'storekeeper']), name='dispatch')
class PurchaseInvoiceListView(LoginRequiredMixin, ListView):
    model = PurchaseInvoice
    template_name = 'purchases/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset().select_related('supplier')
        sort = self.request.GET.get('sort')
        direction = self.request.GET.get('dir', 'desc')

        if sort:
            valid_sorts = ['invoice_id', 'supplier__name', 'created_at', 'payment_method', 'total_amount', 'status']
            if sort in valid_sorts:
                if direction == 'desc':
                    sort = f"-{sort}"
                queryset = queryset.order_by(sort)
        else:
            queryset = queryset.order_by('-created_at')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_invoices = self.get_queryset()
        context['approved_total'] = all_invoices.filter(status='approved').aggregate(
            total=models.Sum('total_amount')
        )['total'] or 0
        context['approved_total'] = all_invoices.filter(status='approved').aggregate(
            total=models.Sum('total_amount')
        )['total'] or 0
        return context

@method_decorator(role_required(allowed_roles=['admin', 'storekeeper']), name='dispatch')
class PurchaseInvoiceCreateView(LoginRequiredMixin, CreateView):
    model = PurchaseInvoice
    template_name = 'purchases/invoice_form.html'
    fields = ['supplier', 'invoice_date', 'payment_method', 'notes']
    success_url = reverse_lazy('invoice_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.filter(is_active=True).order_by('name')
        return context

    def get_initial(self):
        initial = super().get_initial()
        initial['invoice_date'] = timezone.now().date()
        return initial

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.created_by = self.request.user
            self.object.save()
            
            # Handle Items (Dynamic Rows)
            products = self.request.POST.getlist('product[]')
            is_packages = self.request.POST.getlist('is_package[]')
            package_qtys = self.request.POST.getlist('package_qty[]')
            pcs_per_pkgs = self.request.POST.getlist('pcs_per_pkg[]')
            package_prices = self.request.POST.getlist('package_price[]')
            package_sell_prices = self.request.POST.getlist('package_sell_price[]')
            
            # Piece-based fields (backwards compatibility or manual entry)
            quantities = self.request.POST.getlist('quantity[]')
            prices = self.request.POST.getlist('price[]')
            sell_prices = self.request.POST.getlist('sell_price[]')
            taxes = self.request.POST.getlist('tax[]')
            
            for i in range(len(products)):
                pid = products[i]
                if not pid: continue
                
                try:
                    is_pkg = is_packages[i] == 'true'
                    pkg_qty = Decimal(package_qtys[i] or '0')
                    pcs_pkg = Decimal(pcs_per_pkgs[i] or '1')
                    pkg_price = Decimal(package_prices[i] or '0')
                    pkg_sell = Decimal(package_sell_prices[i] or '0')
                    
                    qty = Decimal(quantities[i] or '0')
                    price = Decimal(prices[i] or '0')
                    sell = Decimal(sell_prices[i] or '0')
                    tax_val = Decimal(taxes[i] or '0')
                    
                    if not is_pkg and (qty <= 0 or price < 0): continue
                    if is_pkg and (pkg_qty <= 0 or pkg_price < 0): continue
                    
                    PurchaseInvoiceItem.objects.create(
                        invoice=self.object,
                        product_id=pid,
                        is_package=is_pkg,
                        package_qty=pkg_qty,
                        pieces_per_package=pcs_pkg,
                        package_purchase_price=pkg_price,
                        package_selling_price=pkg_sell,
                        quantity=qty,
                        unit_price=price,
                        suggested_selling_price=sell,
                        tax=tax_val
                    )
                except (ValueError, Decimal.InvalidOperation, IndexError):
                    continue
            
            # Recalculate invoice totals after items are added
            self.object.calculate_totals()
            self.object.save()
            
            # Automate Approval
            self.object.approve(self.request.user)
            
            ActivityLog.objects.create(
                user=self.request.user,
                action="create",
                action_description=f"تم إنشاء فاتورة مشتريات جديدة #{self.object.invoice_id}",
                object_type="PurchaseInvoice",
                object_id=self.object.invoice_id
            )
            messages.success(self.request, f"تم إنشاء الفاتورة {self.object.invoice_id} بنجاح.")
            return redirect('invoice_detail', invoice_id=self.object.invoice_id)

@method_decorator(role_required(allowed_roles=['admin', 'storekeeper']), name='dispatch')
class PurchaseInvoiceUpdateView(LoginRequiredMixin, UpdateView):
    model = PurchaseInvoice
    template_name = 'purchases/invoice_form.html'
    fields = ['supplier', 'invoice_date', 'payment_method', 'notes']
    success_url = reverse_lazy('invoice_list')

    def get_object(self, queryset=None):
        return get_object_or_404(PurchaseInvoice, invoice_id=self.kwargs.get('invoice_id'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.filter(is_active=True).order_by('name')
        return context

    def form_valid(self, form):
        with transaction.atomic():
            # Revert old stock impact before updating
            self.object.revert_stock(self.request.user)
            
            self.object = form.save()
            self.object.items.all().delete()
            
            products = self.request.POST.getlist('product[]')
            is_packages = self.request.POST.getlist('is_package[]')
            package_qtys = self.request.POST.getlist('package_qty[]')
            pcs_per_pkgs = self.request.POST.getlist('pcs_per_pkg[]')
            package_prices = self.request.POST.getlist('package_price[]')
            package_sell_prices = self.request.POST.getlist('package_sell_price[]')
            
            quantities = self.request.POST.getlist('quantity[]')
            prices = self.request.POST.getlist('price[]')
            sell_prices = self.request.POST.getlist('sell_price[]')
            taxes = self.request.POST.getlist('tax[]')
            
            for i in range(len(products)):
                pid = products[i]
                if not pid: continue
                
                try:
                    is_pkg = is_packages[i] == 'true'
                    pkg_qty = Decimal(package_qtys[i] or '0')
                    pcs_pkg = Decimal(pcs_per_pkgs[i] or '1')
                    pkg_price = Decimal(package_prices[i] or '0')
                    pkg_sell = Decimal(package_sell_prices[i] or '0')
                    
                    qty = Decimal(quantities[i] or '0')
                    price = Decimal(prices[i] or '0')
                    sell = Decimal(sell_prices[i] or '0')
                    tax_val = Decimal(taxes[i] or '0')
                    
                    if not is_pkg and (qty <= 0 or price < 0): continue
                    if is_pkg and (pkg_qty <= 0 or pkg_price < 0): continue
                    
                    PurchaseInvoiceItem.objects.create(
                        invoice=self.object,
                        product_id=pid,
                        is_package=is_pkg,
                        package_qty=pkg_qty,
                        pieces_per_package=pcs_pkg,
                        package_purchase_price=pkg_price,
                        package_selling_price=pkg_sell,
                        quantity=qty,
                        unit_price=price,
                        suggested_selling_price=sell,
                        tax=tax_val
                    )
                except (ValueError, Decimal.InvalidOperation, IndexError):
                    continue
            
            # Recalculate invoice totals after items are updated
            self.object.calculate_totals()
            self.object.save()
            
            # Re-approve to apply new stock impact
            self.object.approve(self.request.user)
            
            ActivityLog.objects.create(
                user=self.request.user,
                action="update",
                action_description=f"تم تعديل فاتورة مشتريات #{self.object.invoice_id}",
                object_type="PurchaseInvoice",
                object_id=self.object.invoice_id
            )
            return redirect('invoice_detail', invoice_id=self.object.invoice_id)

@method_decorator(role_required(allowed_roles=['admin', 'storekeeper']), name='dispatch')
class PurchaseInvoiceDetailView(LoginRequiredMixin, DetailView):
    template_name = 'purchases/invoice_detail.html'
    context_object_name = 'invoice'

    def get_object(self, queryset=None):
        return get_object_or_404(PurchaseInvoice, invoice_id=self.kwargs.get('invoice_id'))

@role_required(allowed_roles=['admin', 'storekeeper'])
def approve_invoice(request, invoice_id):
    invoice = get_object_or_404(PurchaseInvoice, invoice_id=invoice_id)
    if invoice.status == 'draft':
        try:
            invoice.approve(request.user)
            ActivityLog.objects.create(
                user=request.user,
                action="approve",
                action_description=f"تم اعتماد فاتورة المشتريات {invoice.invoice_id} وتحديث المخزون.",
                object_type="PurchaseInvoice",
                object_id=invoice.invoice_id
            )
            messages.success(request, f"تم اعتماد الفاتورة {invoice.invoice_id} بنجاح.")
        except Exception as e:
            messages.error(request, f"خطأ في الاعتماد: {str(e)}")
    return redirect('invoice_detail', invoice_id=invoice_id)


@role_required(allowed_roles=['admin', 'storekeeper'])
def export_purchase_pdf(request, invoice_id):
    invoice = get_object_or_404(PurchaseInvoice, invoice_id=invoice_id)
    template_path = 'purchases/invoice_pdf.html'
    context = {
        'invoice': invoice,
        'settings': SystemSettings.objects.first(),
        'user': request.user,
        'now': timezone.now()
    }
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="purchase_invoice_{invoice.invoice_id}.pdf"'
    
    template = get_template(template_path)
    html = template.render(context)
    
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return HttpResponse('خطأ في توليد ملف PDF', status=400)
