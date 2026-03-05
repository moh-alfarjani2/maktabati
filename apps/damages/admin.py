from django.contrib import admin
from .models import DamageReport, DamageItem


class DamageItemInline(admin.TabularInline):
    model = DamageItem
    extra = 1
    readonly_fields = ('total_loss',)


@admin.register(DamageReport)
class DamageReportAdmin(admin.ModelAdmin):
    list_display = ('loss_id', 'damage_date', 'status', 'total_loss', 'created_by')
    list_filter = ('status', 'damage_date')
    search_fields = ('loss_id', 'reason')
    readonly_fields = ('loss_id', 'total_loss')
    inlines = [DamageItemInline]
