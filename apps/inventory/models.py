from django.db import models
from django.conf import settings


class InventoryMovement(models.Model):
    TYPE_CHOICES = [
        ('sale', 'بيع'),
        ('purchase', 'شراء'),
        ('return_sale', 'مرتجع بيع'),
        ('return_purchase', 'مرتجع شراء'),
        ('adjustment', 'تعديل يدوي'),
        ('stocktake', 'جرد مخزني'),
        ('damage', 'تالف/هالك'),
    ]

    product = models.ForeignKey(
        'books.Product', on_delete=models.CASCADE,
        related_name='movements', verbose_name="المنتج"
    )
    movement_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, verbose_name="نوع الحركة"
    )
    quantity_change = models.DecimalField(
        max_digits=12, decimal_places=3, verbose_name="تغيير الكمية"
    )
    quantity_after = models.DecimalField(
        max_digits=12, decimal_places=3, verbose_name="الكمية بعد الحركة"
    )
    reference = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="المرجع"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name="المستخدم"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="التاريخ")

    class Meta:
        verbose_name = "حركة مخزنية"
        verbose_name_plural = "حركات المخزن"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name} | {self.get_movement_type_display()} | {self.quantity_change:+}"


class StockTaking(models.Model):
    session_name = models.CharField(max_length=100, verbose_name="اسم جلسة الجرد")
    conducted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name="المسؤول"
    )
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ البدء")
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الانتهاء")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")

    class Meta:
        verbose_name = "جرد مخزني"
        verbose_name_plural = "عمليات الجرد"

    def __str__(self):
        return self.session_name


class StockTakingItem(models.Model):
    stocktaking = models.ForeignKey(
        StockTaking, on_delete=models.CASCADE,
        related_name='items', verbose_name="جلسة الجرد"
    )
    product = models.ForeignKey(
        'books.Product', on_delete=models.CASCADE, verbose_name="المنتج"
    )
    system_qty = models.DecimalField(
        max_digits=12, decimal_places=3, verbose_name="كمية النظام"
    )
    actual_qty = models.DecimalField(
        max_digits=12, decimal_places=3, verbose_name="الكمية الفعلية"
    )
    difference = models.DecimalField(
        max_digits=12, decimal_places=3, default=0, verbose_name="الفرق"
    )

    def save(self, *args, **kwargs):
        self.difference = self.actual_qty - self.system_qty
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "عنصر جرد"
        verbose_name_plural = "عناصر الجرد"
