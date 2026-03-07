from django.views.generic import ListView, DetailView, TemplateView, CreateView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template
from django.db import transaction, models
from django.db.models import Q
from decimal import Decimal
import json

from apps.books.models import Product, Category
from .models import Customer, SaleInvoice, InvoiceItem, SalesReturn
from apps.inventory.models import InventoryMovement
from apps.core.models import SystemSettings
from apps.accounts.models import ActivityLog
from apps.accounts.decorators import role_required
from django.utils.decorators import method_decorator
from django.utils.decorators import method_decorator
from xhtml2pdf import pisa
from io import BytesIO

@method_decorator(role_required(allowed_roles=['admin', 'cashier']), name='dispatch')
class POSView(LoginRequiredMixin, TemplateView):
    template_name = 'sales/pos.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['products'] = Product.objects.filter(is_active=True)
        context['customers'] = Customer.objects.all()
        # Pass tax rate from settings to template
        tax_setting = SystemSettings.objects.filter(key='tax_rate').first()
        context['system_tax_rate'] = float(tax_setting.value) if tax_setting else 15
        return context

@method_decorator(role_required(allowed_roles=['admin', 'cashier']), name='dispatch')
class POSFinalizeView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            items = data.get('items', [])
            customer_id = data.get('customer_id')
            payment_method = data.get('payment_method', 'cash')
            
            if not items:
                return JsonResponse({'success': False, 'error': 'Cart is empty'}, status=400)

            with transaction.atomic():
                invoice = SaleInvoice(
                    cashier=request.user,
                    payment_method=payment_method,
                    status='completed'
                )
                if customer_id:
                    invoice.customer = Customer.objects.get(id=customer_id)
                
                invoice.save()

                subtotal = 0
                for item in items:
                    product = Product.objects.select_for_update().get(id=item['product_id'])
                    qty = Decimal(str(item['quantity']))
                    
                    if product.current_stock < qty:
                        raise ValueError(f"المخزون غير كافٍ لكتاب: {product.name}")

                    item_subtotal = product.selling_price * qty
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        product=product,
                        quantity=qty,
                        unit_price=product.selling_price,
                        subtotal=item_subtotal
                    )
                    subtotal += item_subtotal

                    product.current_stock -= qty
                    product.save()

                    InventoryMovement.objects.create(
                        product=product,
                        user=request.user,
                        movement_type='sale',
                        quantity_change=-qty,
                        quantity_after=product.current_stock,
                        reference=f"فاتورة #{invoice.invoice_id}"
                    )

                # Dynamic Tax Calculation
                tax_setting = SystemSettings.objects.filter(key='tax_rate').first()
                tax_rate = Decimal(tax_setting.value) / Decimal('100') if tax_setting else Decimal('0.15')
                
                invoice.subtotal = subtotal
                invoice.tax_amount = subtotal * tax_rate
                invoice.total_amount = subtotal + invoice.tax_amount
                
                if payment_method == 'credit' and invoice.customer:
                    invoice.amount_paid = 0
                    invoice.amount_due = invoice.total_amount
                    # Atomic update for customer balance
                    Customer.objects.filter(id=invoice.customer.id).update(
                        balance_due=models.F('balance_due') + invoice.total_amount
                    )
                else:
                    invoice.amount_paid = invoice.total_amount
                    invoice.amount_due = 0
                
                invoice.save()
                # Calculate Profit and Save
                invoice.calculate_profit()
                invoice.save()

                # Global Activity Log
                ActivityLog.objects.create(
                    user=request.user,
                    action="create",
                    action_description=f"تم إصدار الفاتورة #{invoice.invoice_id} بمبلغ {invoice.total_amount} SAR",
                    object_type="SaleInvoice",
                    object_id=invoice.invoice_id
                )

            return JsonResponse({
                'success': True, 
                'invoice_id': invoice.id, 
                'invoice_number': invoice.invoice_id
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

@method_decorator(role_required(allowed_roles=['admin', 'cashier']), name='dispatch')
class InvoiceListView(LoginRequiredMixin, ListView):
    model = SaleInvoice
    template_name = 'sales/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset().select_related('customer', 'cashier')
        sort = self.request.GET.get('sort')
        direction = self.request.GET.get('dir', 'desc')
        
        if sort:
            valid_sorts = ['invoice_id', 'customer__name', 'created_at', 'payment_method', 'total_amount', 'status']
            if sort in valid_sorts:
                if direction == 'desc':
                    sort = f"-{sort}"
                queryset = queryset.order_by(sort)
        else:
            queryset = queryset.order_by('-created_at')

        return queryset

@method_decorator(role_required(allowed_roles=['admin', 'cashier']), name='dispatch')
class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'sales/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q')
        sort = self.request.GET.get('sort')
        direction = self.request.GET.get('dir', 'asc')

        if q:
            queryset = queryset.filter(Q(name__icontains=q) | Q(phone__icontains=q))

        if sort:
            valid_sorts = ['name', 'phone', 'email', 'balance_due', 'created_at']
            if sort in valid_sorts:
                if direction == 'desc':
                    sort = f"-{sort}"
                queryset = queryset.order_by(sort)
        else:
            queryset = queryset.order_by('name')

        return queryset

@method_decorator(role_required(allowed_roles=['admin', 'cashier']), name='dispatch')
class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    template_name = 'sales/customer_form.html'
    fields = ['name', 'phone', 'email', 'address']
    success_url = reverse_lazy('customer_list')

@method_decorator(role_required(allowed_roles=['admin']), name='dispatch')
class InvoiceCancelView(LoginRequiredMixin, View):
    def post(self, request, invoice_id, *args, **kwargs):
        try:
            with transaction.atomic():
                # Lock invoice record
                invoice = get_object_or_404(SaleInvoice.objects.select_for_update(), invoice_id=invoice_id)
                
                if invoice.status == 'cancelled':
                    return JsonResponse({'success': False, 'error': 'الفاتورة ملغاة بالفعل.'}, status=400)
                
                # Restore stock for each item with locking
                from apps.inventory.models import InventoryMovement
                for item in invoice.items.all():
                    product = Product.objects.select_for_update().get(id=item.product.id)
                    product.current_stock += item.quantity
                    product.save()
                    
                    InventoryMovement.objects.create(
                        product=product,
                        user=request.user,
                        movement_type='return',
                        quantity_change=float(item.quantity),
                        quantity_after=float(product.current_stock),
                        reference=f"إلغاء فاتورة {invoice.invoice_id}",
                    )
                
                # Restore customer balance if credit
                if invoice.payment_method == 'credit' and invoice.customer:
                    Customer.objects.filter(id=invoice.customer.id).update(
                        balance_due=models.F('balance_due') - invoice.total_amount
                    )

                invoice.status = 'cancelled'
                invoice.save()
                
                ActivityLog.objects.create(
                    user=request.user,
                    action="cancel",
                    action_description=f"تم إلغاء الفاتورة #{invoice.invoice_id} وإرجاع المخزون.",
                    object_type="SaleInvoice",
                    object_id=invoice.invoice_id
                )
                
                return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

@role_required(allowed_roles=['admin', 'cashier'])
def export_invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(SaleInvoice, invoice_id=invoice_id)
    template_path = 'sales/invoice_pdf.html'
    context = {'invoice': invoice, 'settings': SystemSettings.objects.first()}
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="invoice_{invoice.invoice_id}.pdf"'
    
    template = get_template(template_path)
    html = template.render(context)
    
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return HttpResponse('خطأ في توليد ملف PDF', status=400)

class POSRecommendView(LoginRequiredMixin, View):
    def get(self, request, product_id):
        try:
            current_product = Product.objects.get(id=product_id)
            # Find 2 books from the same categories, excluding current
            first_category = current_product.categories.first()
            if first_category:
                recs = Product.objects.filter(
                    categories=first_category
                ).exclude(id=product_id).order_by('?')[:2]
            else:
                recs = []
            
            data = [{
                'id': p.id,
                'name': p.name,
                'price': float(p.selling_price),
                'stock': p.current_stock
            } for p in recs]
            
            return JsonResponse({'recommended': data})
        except Exception:
            return JsonResponse({'recommended': []})

@role_required(allowed_roles=['admin', 'cashier'])
def add_customer_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name')
            phone = data.get('phone', '')
            if not name:
                return JsonResponse({'success': False, 'error': 'الاسم مطلوب'}, status=400)
            customer = Customer.objects.create(name=name, phone=phone)
            return JsonResponse({'success': True, 'customer': {'id': customer.id, 'name': customer.name}})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=405)
@role_required(allowed_roles=['admin', 'cashier'])
def search_product(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'products': []})
    
    # Search by primary barcode, product ID, or name
    # Also search in ProductBarcode table
    from apps.books.models import ProductBarcode
    
    products = Product.objects.filter(
        Q(name__icontains=query) | 
        Q(product_id=query) | 
        Q(barcode=query) |
        Q(barcodes__barcode=query)
    ).distinct().prefetch_related('barcodes', 'units')[:20]
    
    data = []
    for p in products:
        data.append({
            'id': p.id,
            'product_id': p.product_id,
            'name': p.name,
            'price': float(p.selling_price),
            'stock': p.current_stock,
            'image': p.image.url if p.image else None,
            'barcode': p.barcode,
            'category': ", ".join([c.name for c in p.categories.all()]),
            'units': [{
                'id': u.id,
                'name': u.name,
                'factor': float(u.conversion_factor),
                'price': float(u.selling_price),
                'barcode': u.barcode
            } for u in p.units.all()]
        })
    
    return JsonResponse({'products': data})

def finalize_pos_sale(request):
    # This will replace POSFinalizeView if needed, or I'll just keep using POSFinalizeView
    pass
