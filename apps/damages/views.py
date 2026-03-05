from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import DamageReport, DamageItem
from apps.books.models import Product
from apps.accounts.decorators import role_required


@role_required(allowed_roles=['admin', 'storekeeper'])
def damage_list(request):
    reports = DamageReport.objects.select_related('created_by', 'approved_by').all()
    return render(request, 'damages/damage_list.html', {'reports': reports})


@role_required(allowed_roles=['admin', 'storekeeper'])
def damage_create(request):
    products = Product.objects.filter(is_active=True).order_by('name')
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        damage_date = request.POST.get('damage_date')
        notes = request.POST.get('notes', '')

        report = DamageReport.objects.create(
            reason=reason,
            damage_date=damage_date,
            notes=notes,
            created_by=request.user
        )

        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')
        unit_costs = request.POST.getlist('unit_cost[]')

        for pid, qty, cost in zip(product_ids, quantities, unit_costs):
            if pid and qty and cost:
                DamageItem.objects.create(
                    report=report,
                    product_id=pid,
                    quantity=qty,
                    unit_cost=cost
                )

        ActivityLog.objects.create(
            user=request.user,
            action="create",
            action_description=f"تم إنشاء تقرير تالف جديد #{report.loss_id}",
            object_type="DamageReport",
            object_id=report.loss_id
        )
        messages.success(request, f'تم إنشاء تقرير التالف {report.loss_id}')
        return redirect('damages:detail', loss_id=report.loss_id)

    return render(request, 'damages/damage_form.html', {'products': products})


@role_required(allowed_roles=['admin', 'storekeeper'])
def damage_detail(request, loss_id):
    report = get_object_or_404(DamageReport, loss_id=loss_id)
    return render(request, 'damages/damage_detail.html', {'report': report})


@role_required(allowed_roles=['admin', 'storekeeper'])
def damage_approve(request, loss_id):
    report = get_object_or_404(DamageReport, loss_id=loss_id)
    if request.method == 'POST':
        try:
            report.approve(request.user)
            from apps.accounts.models import ActivityLog
            ActivityLog.objects.create(
                user=request.user,
                action="approve",
                action_description=f"تم اعتماد تقرير التالف #{report.loss_id} وخصم المخزون",
                object_type="DamageReport",
                object_id=report.loss_id
            )
            messages.success(request, f'تم اعتماد تقرير التالف {report.loss_id} وخصم المخزون')
        except ValueError as e:
            messages.error(request, str(e))
    return redirect('damages:detail', loss_id=report.loss_id)
