import random
import string
from django.db import models
from django.conf import settings
from django.core import validators


def generate_product_id(prefix='prd'):
    """توليد رقم منتج فريد (بادئة + 12 رقم عشوائي)"""
    while True:
        uid = f"{prefix.upper()}" + ''.join(random.choices(string.digits, k=12))
        if not Product.objects.filter(product_id=uid).exists():
            return uid


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="اسم التصنيف")

    class Meta:
        verbose_name = "تصنيف"
        verbose_name_plural = "التصنيفات"

    def __str__(self):
        return self.name


class Product(models.Model):
    # المعرّف الفريد
    product_id = models.CharField(
        max_length=20, unique=True, verbose_name="رقم المنتج",
        editable=False
    )

    # نوع المنتج (كتاب أو عام)
    PRODUCT_TYPES = [
        ('book', 'كتاب'),
        ('general', 'منتج عادي'),
    ]
    product_type = models.CharField(
        max_length=20, choices=PRODUCT_TYPES, default='book',
        verbose_name="نوع المنتج"
    )

    # معلومات أساسية
    name = models.CharField(max_length=255, verbose_name="اسم المنتج/الكتاب")
    description = models.TextField(blank=True, null=True, verbose_name="الوصف")

    # معلومات الكتاب (تستخدم فقط إذا كان النوع كتاب)
    author = models.CharField(max_length=255, blank=True, null=True, verbose_name="المؤلف")
    page_count = models.PositiveIntegerField(blank=True, null=True, verbose_name="عدد الصفحات")
    
    LANGUAGES = [
        ('ar', 'العربية'),
        ('en', 'الإنجليزية'),
        ('fr', 'الفرنسية'),
        ('es', 'الإسبانية'),
        ('tr', 'التركية'),
        ('other', 'أخرى'),
    ]
    language = models.CharField(
        max_length=10, choices=LANGUAGES, default='ar',
        blank=True, null=True, verbose_name="اللغة"
    )

    categories = models.ManyToManyField(
        Category, blank=True, related_name='products_m2m',
        verbose_name="التصنيفات"
    )

    image = models.ImageField(
        upload_to='products/', blank=True, null=True, verbose_name="الصورة"
    )

    # الوحدة الأساسية
    base_unit = models.CharField(
        max_length=50, default="قطعة", verbose_name="الوحدة الأساسية"
    )

    # إعدادات العبوة
    has_package = models.BooleanField(
        default=False, verbose_name="يحتوي عبوة"
    )
    package_type = models.CharField(
        max_length=50, blank=True, default="", verbose_name="نوع العبوة"
    )
    package_qty = models.DecimalField(
        max_digits=10, decimal_places=3, default=1,
        validators=[validators.MinValueValidator(0.001)],
        verbose_name="عدد القطع داخل العبوة"
    )

    # ضريبة وتخفيض القطعة
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[validators.MinValueValidator(0), validators.MaxValueValidator(100)],
        verbose_name="ضريبة القطعة %"
    )
    discount_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[validators.MinValueValidator(0), validators.MaxValueValidator(100)],
        verbose_name="تخفيض القطعة %"
    )

    # ضريبة وتخفيض العبوة
    package_tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[validators.MinValueValidator(0), validators.MaxValueValidator(100)],
        verbose_name="ضريبة العبوة %"
    )
    package_discount_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[validators.MinValueValidator(0), validators.MaxValueValidator(100)],
        verbose_name="تخفيض العبوة %"
    )

    # الأسعار
    purchase_price = models.DecimalField(
        max_digits=12, decimal_places=4, default=0, verbose_name="سعر الشراء"
    )
    selling_price = models.DecimalField(
        max_digits=12, decimal_places=4, default=0, verbose_name="سعر البيع"
    )
    package_purchase_price = models.DecimalField(
        max_digits=12, decimal_places=4, default=0, null=True, blank=True,
        verbose_name="سعر شراء العبوة"
    )
    package_selling_price = models.DecimalField(
        max_digits=12, decimal_places=4, default=0, null=True, blank=True,
        verbose_name="سعر بيع العبوة"
    )
    min_price = models.DecimalField(
        max_digits=12, decimal_places=4, default=0,
        validators=[validators.MinValueValidator(0)],
        verbose_name="أقل سعر مسموح"
    )
    profit_margin = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        verbose_name="هامش الربح %"
    )

    # المخزون
    current_stock = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
        verbose_name="الكمية الحالية"
    )
    min_stock_level = models.DecimalField(
        max_digits=12, decimal_places=3, default=5,
        verbose_name="حد التنبيه"
    )
    last_purchase_price = models.DecimalField(
        max_digits=12, decimal_places=4, default=0,
        validators=[validators.MinValueValidator(0)],
        verbose_name="آخر سعر شراء"
    )
    avg_cost = models.DecimalField(
        max_digits=12, decimal_places=4, default=0,
        verbose_name="متوسط التكلفة"
    )

    # المورد الافتراضي
    default_supplier = models.ForeignKey(
        'purchases.Supplier', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="المورد الافتراضي"
    )

    # الحالة
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    # التتبع
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='products_created',
        verbose_name="أُنشئ بواسطة"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='products_updated',
        verbose_name="عُدّل بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإضافة")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخر تعديل")

    class Meta:
        verbose_name = "منتج"
        verbose_name_plural = "المنتجات"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.product_id:
            # استخراج أول 3 أحرف من الاسم وتطهيرها لتكون بادئة
            import re
            name_prefix = re.sub(r'[^\w]', '', self.name)[:3].lower()
            if not name_prefix:
                name_prefix = 'prd'
            self.product_id = generate_product_id(name_prefix)
            
        # حساب هامش الربح تلقائيًا
        if self.purchase_price and self.selling_price and self.purchase_price > 0:
            self.profit_margin = round(
                ((self.selling_price - self.purchase_price) / self.purchase_price) * 100, 2
            )
        super().save(*args, **kwargs)

    def update_avg_cost(self, new_qty, new_price):
        """تحديث متوسط التكلفة (Weighted Average) باستخدام Decimal للدقة العالية"""
        from decimal import Decimal
        current_qty = Decimal(str(self.current_stock))
        current_avg = Decimal(str(self.avg_cost))
        new_qty = Decimal(str(new_qty))
        new_price = Decimal(str(new_price))
        
        total_qty = current_qty + new_qty
        if total_qty <= 0:
            # في حال أصبح المخزون صفراً أو سالباً، يظل متوسط التكلفة كما هو أو يُصفر
            if total_qty == 0 and new_qty > 0:
                self.avg_cost = new_price
            return

        total_cost = (current_qty * current_avg) + (new_qty * new_price)
        self.avg_cost = (total_cost / total_qty).quantize(Decimal('0.0001'))

    @property
    def is_low_stock(self):
        return self.current_stock <= self.min_stock_level

    @property
    def profit_amount(self):
        return self.selling_price - self.avg_cost if self.avg_cost else self.selling_price - self.purchase_price

    def has_invoices(self):
        """تحقق هل للمنتج فواتير مبيعات أو مشتريات"""
        from apps.sales.models import InvoiceItem
        from apps.purchases.models import PurchaseInvoiceItem
        return (
            InvoiceItem.objects.filter(product=self).exists() or
            PurchaseInvoiceItem.objects.filter(product=self).exists()
        )


class ProductBarcode(models.Model):
    """باركودات متعددة لنفس المنتج"""
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name='barcodes', verbose_name="المنتج"
    )
    barcode = models.CharField(
        max_length=100, unique=True, verbose_name="الباركود"
    )
    is_primary = models.BooleanField(default=False, verbose_name="أساسي")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "باركود"
        verbose_name_plural = "الباركودات"

    def __str__(self):
        return f"{self.barcode} → {self.product.name}"

    def save(self, *args, **kwargs):
        # إذا كان أساسي، اجعل باقي الباركودات غير أساسية
        if self.is_primary:
            ProductBarcode.objects.filter(
                product=self.product, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class ProductUnit(models.Model):
    """وحدات متعددة لنفس المنتج (عبوة، كرتون، باك...)"""
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name='units', verbose_name="المنتج"
    )
    name = models.CharField(max_length=50, verbose_name="اسم الوحدة")  # كرتون، عبوة، باك
    conversion_factor = models.DecimalField(
        max_digits=10, decimal_places=3, default=1,
        verbose_name="عدد القطع داخل الوحدة"
    )
    purchase_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="سعر الشراء"
    )
    selling_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="سعر البيع"
    )
    barcode = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name="باركود الوحدة"
    )

    class Meta:
        verbose_name = "وحدة"
        verbose_name_plural = "الوحدات"
        unique_together = [('product', 'name')]

    def __str__(self):
        return f"{self.product.name} - {self.name} ({self.conversion_factor} {self.product.base_unit})"
