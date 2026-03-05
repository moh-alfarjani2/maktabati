from django.db import models

class SystemSettings(models.Model):
    key = models.CharField(max_length=100, unique=True, verbose_name="المفتاح")
    value = models.TextField(verbose_name="القيمة")
    value_type = models.CharField(max_length=50, default='text', verbose_name="نوع القيمة")
    description = models.TextField(blank=True, verbose_name="الوصف")

    class Meta:
        verbose_name = "إعدادات النظام"
        verbose_name_plural = "إعدادات النظام"

class SystemSequence(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="اسم التسلسل")
    last_value = models.BigIntegerField(default=0, verbose_name="آخر قيمة")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تسلسل النظام"
        verbose_name_plural = "تسلسلات النظام"

    def __str__(self):
        return f"{self.name}: {self.last_value}"

    @classmethod
    def get_next_value(cls, name, model_class=None, field_name=None):
        """الحصول على الرقم التالي بشكل آمن وذري مع تهيئة تلقائية من البيانات الموجودة"""
        from django.db import transaction
        with transaction.atomic():
            sequence, created = cls.objects.select_for_update().get_or_create(name=name)
            
            if created and model_class and field_name:
                # تهيئة من أكبر رقم موجود حالياً
                from django.db.models import Max
                # جلب كل القيم وتحليلها عددياً (لأنها CharField)
                ids = model_class.objects.values_list(field_name, flat=True)
                numeric_ids = [int(v) for v in ids if str(v).isdigit()]
                max_val = max(numeric_ids) if numeric_ids else 0
                sequence.last_value = max_val
            
            sequence.last_value += 1
            sequence.save()
            return sequence.last_value
