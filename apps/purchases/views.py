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

@method_decorator(role_required(allowed_roles=['admin', 'storekeeper']), name='dispatch')
class SupplierListView(LoginRequiredMixin, ListView):
    model = Supplier
    template_name = 'purchases/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 15

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
        return super().get_queryset().select_related('supplier').order_by('-created_at')

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

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.created_by = self.request.user
            self.object.save()
            
            # Handle Items (Dynamic Rows)
            products = self.request.POST.getlist('product[]')
            quantities = self.request.POST.getlist('quantity[]')
            prices = self.request.POST.getlist('price[]')
            
            for pid, qty_str, price_str in zip(products, quantities, prices):
                if not pid: continue
                try:
                    qty = Decimal(qty_str)
                    price = Decimal(price_str)
                    if qty <= 0 or price < 0: continue
                    
                    PurchaseInvoiceItem.objects.create(
                        invoice=self.object,
                        product_id=pid,
                        quantity=qty,
                        unit_price=price
                    )
                except (ValueError, Decimal.InvalidOperation):
                    continue
            
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
        if self.object.status != 'draft':
            messages.error(self.request, "لا يمكن تعديل فاتورة معتمدة أو ملغاة.")
            return redirect('invoice_detail', invoice_id=self.object.invoice_id)
            
        with transaction.atomic():
            self.object = form.save()
            self.object.items.all().delete()
            
            products = self.request.POST.getlist('product[]')
            quantities = self.request.POST.getlist('quantity[]')
            prices = self.request.POST.getlist('price[]')
            
            for pid, qty_str, price_str in zip(products, quantities, prices):
                if not pid: continue
                try:
                    qty = Decimal(qty_str)
                    price = Decimal(price_str)
                    if qty <= 0 or price < 0: continue
                    
                    PurchaseInvoiceItem.objects.create(
                        invoice=self.object,
                        product_id=pid,
                        quantity=qty,
                        unit_price=price
                    )
                except (ValueError, Decimal.InvalidOperation):
                    continue
            
            ActivityLog.objects.create(
                user=self.request.user,
                action="update",
                action_description=f"تم تعديل فاتورة مشتريات مسودة #{self.object.invoice_id}",
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
