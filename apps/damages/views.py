from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import DamageReport, DamageItem
from apps.books.models import Product
from apps.accounts.decorators import role_required
from apps.accounts.models import ActivityLog
from apps.core.models import SystemSettings
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO


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


@role_required(allowed_roles=['admin', 'storekeeper'])
def export_damage_pdf(request, loss_id):
    report = get_object_or_404(DamageReport, loss_id=loss_id)
    template_path = 'damages/damage_pdf.html'
    context = {
        'report': report,
        'settings': SystemSettings.objects.first(),
        'user': request.user,
        'now': timezone.now()
    }
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="damage_report_{report.loss_id}.pdf"'
    
    template = get_template(template_path)
    html = template.render(context)
    
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return HttpResponse('خطأ في توليد ملف PDF', status=400)
