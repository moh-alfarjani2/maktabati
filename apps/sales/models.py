from django.db import models, transaction
from django.conf import settings
from apps.core.models import SystemSequence

def generate_sale_id():
    """توليد رقم فاتورة مبيعات تصاعدي آمن"""
    from .models import SaleInvoice
    return str(SystemSequence.get_next_value('sale_invoice', SaleInvoice, 'invoice_id'))

def generate_return_id():
    """توليد رقم مرتجع مبيعات تصاعدي آمن"""
    from .models import SalesReturn
    return str(SystemSequence.get_next_value('sale_return', SalesReturn, 'return_id'))


class Customer(models.Model):
    name = models.CharField(max_length=255, verbose_name="اسم العميل")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="رقم الهاتف")
    email = models.EmailField(blank=True, null=True, verbose_name="البريد الإلكتروني")
    address = models.TextField(blank=True, null=True, verbose_name="العنوان")
    balance_due = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="الرصيد المستحق"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "عميل"
        verbose_name_plural = "العملاء"

    def __str__(self):
        return self.name


class SaleInvoice(models.Model):
    PAYMENT_CHOICES = [
        ('cash', 'نقداً'),
        ('card', 'بطاقة'),
        ('credit', 'آجل'),
        ('transfer', 'تحويل بنكي'),
        ('mixed', 'مختلط'),
    ]
    STATUS_CHOICES = [
        ('completed', 'مكتملة'),
        ('held', 'معلقة'),
        ('cancelled', 'ملغاة'),
        ('returned', 'مرتجعة'),
    ]

    invoice_id = models.CharField(
        max_length=20, unique=True, editable=False, verbose_name="رقم الفاتورة"
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="العميل"
    )
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name="الكاشير"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='completed', verbose_name="الحالة"
    )
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_CHOICES, default='cash', verbose_name="طريقة الدفع"
    )

    # المبالغ
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="المجموع الفرعي")
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="مبلغ الخصم")
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="نسبة الخصم %")
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="الضريبة")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="الإجمالي")
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="المدفوع")
    amount_due = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="الباقي")
    change_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="الفكة")

    # الربح
    profit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="الربح")
    cost_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="التكلفة")

    # الدفع المختلط
    cash_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="نقداً")
    card_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="بطاقة")

    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="التاريخ")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "فاتورة مبيعات"
        verbose_name_plural = "فواتير المبيعات"
        ordering = ['-created_at']

    def __str__(self):
        return f"فاتورة {self.invoice_id}"

    def save(self, *args, **kwargs):
        if not self.invoice_id:
            self.invoice_id = generate_sale_id()
        super().save(*args, **kwargs)

    def calculate_profit(self):
        total_cost = sum(
            item.cost_price * item.quantity
            for item in self.items.all()
        )
        self.cost_amount = total_cost
        self.profit_amount = self.total_amount - total_cost
        return self.profit_amount


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        SaleInvoice, on_delete=models.CASCADE,
        related_name='items', verbose_name="الفاتورة"
    )
    product = models.ForeignKey(
        'books.Product', on_delete=models.PROTECT, verbose_name="المنتج"
    )
    unit_name = models.CharField(max_length=50, default="قطعة", verbose_name="الوحدة")
    unit_factor = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, verbose_name="الكمية")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="سعر البيع")
    cost_price = models.DecimalField(
        max_digits=12, decimal_places=4, default=0, verbose_name="سعر التكلفة"
    )
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="الخصم")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="الإجمالي")

    class Meta:
        verbose_name = "بند فاتورة"
        verbose_name_plural = "بنود الفواتير"

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"

    def save(self, *args, **kwargs):
        self.subtotal = (self.unit_price * self.quantity) - self.discount
        if not self.cost_price and self.product_id:
            self.cost_price = self.product.avg_cost or self.product.purchase_price
        super().save(*args, **kwargs)

    @property
    def profit(self):
        return self.subtotal - (self.cost_price * self.quantity)


class SalesReturn(models.Model):
    return_id = models.CharField(
        max_length=20, unique=True, editable=False, verbose_name="رقم المرتجع"
    )
    original_invoice = models.ForeignKey(
        SaleInvoice, on_delete=models.PROTECT,
        related_name='returns', verbose_name="الفاتورة الأصلية"
    )
    reason = models.TextField(verbose_name="السبب")
    total_refund = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="المبلغ المسترجع"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name="بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "مرتجع"
        verbose_name_plural = "المرتجعات"

    def save(self, *args, **kwargs):
        if not self.return_id:
            self.return_id = generate_return_id()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"مرتجع {self.return_id}"


class SalesReturnItem(models.Model):
    sales_return = models.ForeignKey(
        SalesReturn, on_delete=models.CASCADE,
        related_name='items', verbose_name="المرتجع"
    )
    product = models.ForeignKey(
        'books.Product', on_delete=models.PROTECT, verbose_name="المنتج"
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3, verbose_name="الكمية")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="السعر")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.subtotal = self.unit_price * self.quantity
        super().save(*args, **kwargs)
