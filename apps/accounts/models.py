from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.Model):
    ADMIN = 'admin'
    CASHIER = 'cashier'
    STOREKEEPER = 'storekeeper'

    ROLE_CHOICES = [
        (ADMIN, 'مدير النظام'),
        (CASHIER, 'كاشير'),
        (STOREKEEPER, 'أمين مخزن'),
    ]

    name = models.CharField(max_length=50, choices=ROLE_CHOICES, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.get_name_display()

    class Meta:
        verbose_name = "دور"
        verbose_name_plural = "الأدوار"


class CustomUser(AbstractUser):
    full_name = models.CharField(max_length=255, verbose_name="الاسم الكامل")
    role = models.ForeignKey(
        Role, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="الدور"
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name="رقم الهاتف")
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمون"

    def __str__(self):
        return self.full_name or self.username

    @property
    def is_admin(self):
        return self.role and self.role.name == Role.ADMIN

    @property
    def is_cashier(self):
        return self.role and self.role.name == Role.CASHIER

    @property
    def is_storekeeper(self):
        return self.role and self.role.name == Role.STOREKEEPER


class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'إنشاء'),
        ('update', 'تعديل'),
        ('delete', 'حذف'),
        ('approve', 'اعتماد'),
        ('cancel', 'إلغاء'),
        ('login', 'تسجيل دخول'),
        ('logout', 'تسجيل خروج'),
        ('other', 'أخرى'),
    ]

    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, verbose_name="المستخدم"
    )
    action = models.CharField(
        max_length=20, choices=ACTION_CHOICES, default='other', verbose_name="الإجراء"
    )
    action_description = models.CharField(max_length=500, verbose_name="وصف الإجراء")
    object_type = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="نوع الكيان"
    )
    object_id = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="معرّف الكيان"
    )
    old_value = models.JSONField(blank=True, null=True, verbose_name="القيمة القديمة")
    new_value = models.JSONField(blank=True, null=True, verbose_name="القيمة الجديدة")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="الوقت")
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="عنوان IP")

    class Meta:
        verbose_name = "سجل نشاط"
        verbose_name_plural = "سجلات الأنشطة"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} | {self.get_action_display()} | {self.action_description[:50]}"
