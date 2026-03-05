from django.db import models, transaction
from django.conf import settings
from apps.core.models import SystemSequence

def generate_loss_id():
    """توليد رقم تقرير تالف تصاعدي آمن"""
    from .models import DamageReport
    return str(SystemSequence.get_next_value('damage_report', DamageReport, 'loss_id'))


class DamageReport(models.Model):
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('approved', 'معتمد'),
        ('cancelled', 'ملغى'),
    ]

    loss_id = models.CharField(
        max_length=20, unique=True, editable=False, verbose_name="رقم التقرير"
    )
    reason = models.TextField(verbose_name="السبب")
    damage_date = models.DateField(verbose_name="تاريخ التلف")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="الحالة"
    )
    total_loss = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="إجمالي الخسارة"
    )
    notes = models.TextField(blank=True, verbose_name="ملاحظات")

    # التتبع
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='damage_reports_created', verbose_name="بواسطة"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='damage_reports_approved', verbose_name="اعتمدها"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تقرير تالف"
        verbose_name_plural = "تقارير التالف"
        ordering = ['-damage_date']

    def __str__(self):
        return f"تقرير تالف {self.loss_id}"

    def save(self, *args, **kwargs):
        if not self.loss_id:
            self.loss_id = generate_loss_id()
        self.total_loss = sum(item.total_loss for item in self.items.all()) if self.pk else 0
        super().save(*args, **kwargs)

    @transaction.atomic
    def approve(self, user):
        """اعتماد تقرير التلف وخصم الكميات من المخزون مع حماية من التكرار والتزامن"""
        # قفل سجل التقرير نفسه لمنع الاعتماد المزدوج
        report = DamageReport.objects.select_for_update().get(pk=self.pk)
        if report.status != 'draft':
            return False, "التقرير معتمد مسبقاً أو ملغى"

        from apps.inventory.models import InventoryMovement

        for item in self.items.all():
            # قفل السجل لمنع Race Condition عند خصم المخزون
            product = Product.objects.select_for_update().get(id=item.product_id)
            if item.quantity > product.current_stock:
                raise ValueError(f"الكمية المتلفة ({item.quantity}) تتجاوز المخزون المتوفر ({product.current_stock}) للمنتج: {product.name}")

            product.current_stock -= item.quantity
            product.save()

            InventoryMovement.objects.create(
                product=product,
                movement_type='damage',
                quantity_change=-float(item.quantity),
                quantity_after=float(product.current_stock),
                reference=f"تلف {self.loss_id}",
                user=user
            )

        self.status = 'approved'
        self.approved_by = user
        self.total_loss = sum(item.total_loss for item in self.items.all())
        self.save()


class DamageItem(models.Model):
    report = models.ForeignKey(
        DamageReport, on_delete=models.CASCADE,
        related_name='items', verbose_name="التقرير"
    )
    product = models.ForeignKey(
        'books.Product', on_delete=models.PROTECT, verbose_name="المنتج"
    )
    quantity = models.DecimalField(
        max_digits=12, decimal_places=3, verbose_name="الكمية المتلفة"
    )
    unit_cost = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="تكلفة الوحدة"
    )
    total_loss = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="إجمالي الخسارة"
    )
    notes = models.CharField(max_length=255, blank=True, verbose_name="ملاحظة")

    class Meta:
        verbose_name = "بند تلف"
        verbose_name_plural = "بنود التلف"

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"

    def save(self, *args, **kwargs):
        self.total_loss = self.unit_cost * self.quantity
        if not self.unit_cost and self.product_id:
            self.unit_cost = self.product.avg_cost or self.product.purchase_price
            self.total_loss = self.unit_cost * self.quantity
        super().save(*args, **kwargs)
