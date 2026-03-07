from django.db import models, transaction
from django.conf import settings
from apps.core.models import SystemSequence

def generate_invoice_id():
    """توليد رقم فاتورة مشتريات تصاعدي آمن"""
    from .models import PurchaseInvoice
    return str(SystemSequence.get_next_value('purchase_invoice', PurchaseInvoice, 'invoice_id'))

def generate_supplier_payment_id():
    """توليد رقم دفعة مورد تصاعدي آمن"""
    from .models import SupplierPayment
    return str(SystemSequence.get_next_value('supplier_payment', SupplierPayment, 'payment_id'))


class Supplier(models.Model):
    name = models.CharField(max_length=200, verbose_name="اسم المورد")
    contact_person = models.CharField(max_length=100, blank=True, verbose_name="الشخص المسؤول")
    phone = models.CharField(max_length=20, blank=True, verbose_name="رقم الجوال")
    email = models.EmailField(blank=True, verbose_name="البريد الإلكتروني")
    address = models.TextField(blank=True, verbose_name="العنوان")
    balance_due = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="الرصيد المستحق (ديون)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "مورد"
        verbose_name_plural = "الموردون"


class PurchaseInvoice(models.Model):
    PAYMENT_CHOICES = [
        ('cash', 'نقداً'),
        ('card', 'بطاقة'),
        ('credit', 'آجل'),
        ('transfer', 'تحويل بنكي'),
    ]
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('approved', 'معتمدة'),
        ('cancelled', 'ملغاة'),
    ]

    invoice_id = models.CharField(
        max_length=20, unique=True, editable=False, verbose_name="رقم الفاتورة"
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, verbose_name="المورد"
    )
    invoice_date = models.DateField(verbose_name="تاريخ الفاتورة")
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_CHOICES, default='cash', verbose_name="طريقة الدفع"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='approved', verbose_name="الحالة"
    )

    # المبالغ
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="المجموع الفرعي")
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="تكلفة الشحن")
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="الضريبة")
    extra_discount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="خصم إضافي")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="الإجمالي")
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="المدفوع")
    amount_due = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="المتبقي (دين)")

    notes = models.TextField(blank=True, verbose_name="ملاحظات")

    # التتبع
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='purchase_invoices_created', verbose_name="أُنشئ بواسطة"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='purchase_invoices_approved', verbose_name="اعتمدها"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='purchase_invoices_updated', verbose_name="عُدّل بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخر تعديل")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الاعتماد")

    class Meta:
        verbose_name = "فاتورة مشتريات"
        verbose_name_plural = "فواتير المشتريات"
        ordering = ['-created_at']

    def __str__(self):
        return f"فاتورة {self.invoice_id} - {self.supplier.name}"

    def save(self, *args, **kwargs):
        if not self.invoice_id:
            self.invoice_id = generate_invoice_id()
        self.calculate_totals()
        super().save(*args, **kwargs)

    def calculate_totals(self):
        items = self.items.all() if self.pk else []
        self.subtotal = sum(item.total_price for item in items)
        self.total_amount = self.subtotal + self.shipping_cost + self.tax_amount - self.extra_discount
        self.amount_due = self.total_amount - self.amount_paid

    @transaction.atomic
    def approve(self, user):
        """اعتماد الفاتورة: زيادة المخزون + تحديث متوسط التكلفة مع ميزة القفل (Locking)"""
        # قفل سجل الفاتورة
        invoice = PurchaseInvoice.objects.select_for_update().get(pk=self.pk)
        
        # إذا تم الغاؤها مسبقاً، لا يمكن اعتمادها
        if invoice.status == 'cancelled':
            raise ValueError("لا يمكن اعتماد فاتورة ملغاة")

        from apps.inventory.models import InventoryMovement
        from apps.books.models import Product

        for item in self.items.all():
            product = Product.objects.select_for_update().get(id=item.product_id)
            
            # تحديث متوسط التكلفة
            product.update_avg_cost(item.quantity, item.unit_price)
            product.last_purchase_price = item.unit_price
            product.current_stock += item.quantity
            product.save()

            InventoryMovement.objects.create(
                product=product,
                movement_type='purchase',
                quantity_change=float(item.quantity),
                quantity_after=float(product.current_stock),
                reference=self.invoice_id,
                user=user
            )

        # تحديث ديون المورد إذا آجل
        if self.payment_method == 'credit':
            self.supplier.balance_due += self.amount_due
            self.supplier.save()

        from django.utils import timezone
        self.status = 'approved'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()

    @transaction.atomic
    def revert_stock(self, user):
        """عكس الحركات المخزنية والمالية للفاتورة قبل التعديل أو عند الإلغاء"""
        invoice = PurchaseInvoice.objects.select_for_update().get(pk=self.pk)
        if invoice.status != 'approved':
            return # لا حاجة للعكس إذا لم يتم الاعتماد

        from apps.inventory.models import InventoryMovement
        from apps.books.models import Product

        for item in self.items.all():
            product = Product.objects.select_for_update().get(id=item.product_id)
            # عكس المخزون
            product.current_stock -= item.quantity
            if product.current_stock < 0:
                product.current_stock = 0
            product.save()

            InventoryMovement.objects.create(
                product=product,
                movement_type='adjustment',
                quantity_change=-float(item.quantity),
                quantity_after=float(product.current_stock),
                reference=f"تعديل/عكس فاتورة {self.invoice_id}",
                user=user
            )

        # عكس الديون إذا كانت آجل
        if self.payment_method == 'credit':
            self.supplier.balance_due -= self.amount_due
            self.supplier.save()
        
        # إعادة الحالة للمسودة مؤقتاً أثناء التعديل أو الاحتفاظ بها كمعتمدة حسب الحاجة
        # هنا سنتركها "مرجوعة" مخزنياً حتى يتم استدعاء approve مجدداً

    @transaction.atomic
    def cancel(self, user):
        """إلغاء الفاتورة: Rollback كامل مع قفل السجلات"""
        if self.status != 'approved':
            raise ValueError("يمكن إلغاء الفواتير المعتمدة فقط")

        from apps.inventory.models import InventoryMovement
        from apps.books.models import Product

        for item in self.items.all():
            product = Product.objects.select_for_update().get(id=item.product_id)
            # عكس المخزون
            product.current_stock -= item.quantity
            if product.current_stock < 0:
                product.current_stock = 0
            product.save()

            InventoryMovement.objects.create(
                product=product,
                movement_type='adjustment',
                quantity_change=-float(item.quantity),
                quantity_after=float(product.current_stock),
                reference=f"إلغاء فاتورة {self.invoice_id}",
                user=user
            )

        # عكس الديون إذا كانت آجل
        if self.payment_method == 'credit':
            self.supplier.balance_due -= self.amount_due
            self.supplier.save()

        self.status = 'cancelled'
        self.updated_by = user
        self.save()


class PurchaseInvoiceItem(models.Model):
    invoice = models.ForeignKey(
        PurchaseInvoice, on_delete=models.CASCADE,
        related_name='items', verbose_name="الفاتورة"
    )
    product = models.ForeignKey(
        'books.Product', on_delete=models.PROTECT, verbose_name="المنتج"
    )
    is_package = models.BooleanField(default=False, verbose_name="شراء بالعبوة")
    package_qty = models.DecimalField(
        max_digits=12, decimal_places=3, default=0, verbose_name="عدد العبوات"
    )
    pieces_per_package = models.DecimalField(
        max_digits=12, decimal_places=3, default=1, verbose_name="قطع/عبوة"
    )
    package_purchase_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="سعر شراء العبوة"
    )
    package_selling_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="سعر بيع العبوة"
    )
    
    quantity = models.DecimalField(
        max_digits=12, decimal_places=3, verbose_name="الكمية (بالقطع)"
    )
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="سعر شراء القطعة"
    )
    suggested_selling_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="سعر بيع القطعة"
    )
    discount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="الخصم"
    )
    tax = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, verbose_name="الضريبة %"
    )
    total_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="الإجمالي"
    )

    class Meta:
        verbose_name = "بند فاتورة مشتريات"
        verbose_name_plural = "بنود فواتير المشتريات"

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"

    def save(self, *args, **kwargs):
        from decimal import Decimal
        
        # إذا كان شراء بالعبوة، احسب الكمية الإجمالية وسعر القطعة
        if self.is_package:
            # الكمية الإجمالية = عدد العبوات × قطع/عبوة
            self.quantity = self.package_qty * self.pieces_per_package
            # سعر القطعة = سعر العبوة / قطع/عبوة
            if self.pieces_per_package > 0:
                self.unit_price = self.package_purchase_price / self.pieces_per_package
                self.suggested_selling_price = self.package_selling_price / self.pieces_per_package
            else:
                self.unit_price = self.package_purchase_price
                self.suggested_selling_price = self.package_selling_price

        subtotal = (self.unit_price * self.quantity) - self.discount
        tax_val = subtotal * (self.tax / Decimal('100'))
        self.total_price = subtotal + tax_val
        super().save(*args, **kwargs)

    @property
    def profit_margin(self):
        if self.unit_price > 0 and self.suggested_selling_price > 0:
            return round(((self.suggested_selling_price - self.unit_price) / self.unit_price) * 100, 2)
        return 0


class SupplierPayment(models.Model):
    PAYMENT_CHOICES = [
        ('cash', 'نقداً'),
        ('card', 'بطاقة'),
        ('transfer', 'تحويل بنكي'),
    ]
    payment_id = models.CharField(
        max_length=20, unique=True, editable=False, verbose_name="رقم الدفعة"
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE,
        related_name='payments', verbose_name="المورد"
    )
    invoice = models.ForeignKey(
        PurchaseInvoice, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='payments', verbose_name="الفاتورة المرتبطة"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="المبلغ")
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_CHOICES, default='cash', verbose_name="طريقة الدفع"
    )
    payment_date = models.DateField(verbose_name="التاريخ")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name="بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "دفعة مورد"
        verbose_name_plural = "دفعات الموردين"
        ordering = ['-payment_date']

    def __str__(self):
        return f"دفعة {self.payment_id} للمورد {self.supplier.name}"

    def save(self, *args, **kwargs):
        if not self.payment_id:
            self.payment_id = generate_supplier_payment_id()
        super().save(*args, **kwargs)
