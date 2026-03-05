from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect, get_object_or_404
from django.db import transaction
from apps.books.models import Product
from .models import InventoryMovement, StockTaking, StockTakingItem
from apps.accounts.decorators import role_required
from django.utils.decorators import method_decorator
from django.utils import timezone

@method_decorator(role_required(allowed_roles=['admin', 'storekeeper']), name='dispatch')
class InventoryListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'inventory/product_stock.html'
    context_object_name = 'products'
    paginate_by = 20

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Product.objects.filter(name__icontains=query)
        return Product.objects.all()

@method_decorator(role_required(allowed_roles=['admin', 'storekeeper']), name='dispatch')
class MovementLogView(LoginRequiredMixin, ListView):
    model = InventoryMovement
    template_name = 'inventory/movement_log.html'
    context_object_name = 'movements'
    paginate_by = 20

    def get_queryset(self):
        return super().get_queryset().select_related('product', 'user').order_by('-created_at')

@method_decorator(role_required(allowed_roles=['admin', 'storekeeper']), name='dispatch')
class StockTakingListView(LoginRequiredMixin, ListView):
    model = StockTaking
    template_name = 'inventory/stocktaking_list.html'
    context_object_name = 'audits'

@method_decorator(role_required(allowed_roles=['admin', 'storekeeper']), name='dispatch')
class StockTakingCreateView(LoginRequiredMixin, CreateView):
    model = StockTaking
    template_name = 'inventory/stocktaking_form.html'
    fields = ['session_name', 'notes']
    success_url = reverse_lazy('stocktaking_list')

    def form_valid(self, form):
        with transaction.atomic():
            form.instance.conducted_by = self.request.user
            response = super().form_valid(form)
            # Take snapshot of all products
            products = Product.objects.all()
            for p in products:
                StockTakingItem.objects.create(
                    stocktaking=self.object,
                    product=p,
                    system_qty=p.current_stock,
                    actual_qty=p.current_stock, # Initial guess
                    difference=0
                )
            return response

@method_decorator(role_required(allowed_roles=['admin', 'storekeeper']), name='dispatch')
class StockTakingDetailView(LoginRequiredMixin, DetailView):
    model = StockTaking
    template_name = 'inventory/stocktaking_detail.html'
    context_object_name = 'audit'
