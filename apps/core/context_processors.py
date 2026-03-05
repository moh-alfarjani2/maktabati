import json
from .models import SystemSettings

def navbar_settings(request):
    """
    Context processor to provide navbar items and configuration.
    """
    # Default navbar items with icons and URLs
    default_items = [
        {'name': 'الرئيسية', 'url': 'dashboard', 'icon': 'fas fa-home', 'priority': 10},
        {'name': 'نقطة البيع', 'url': 'pos', 'icon': 'fas fa-cash-register', 'priority': 9},
        {'name': 'الكتب', 'url': 'product_list', 'icon': 'fas fa-book', 'priority': 8},
        {'name': 'المخزون', 'url': 'inventory_list', 'icon': 'fas fa-warehouse', 'priority': 7},
        {'name': 'المشتريات', 'url': 'invoice_purchase_list', 'icon': 'fas fa-truck', 'priority': 6},
        {'name': 'المبيعات', 'url': 'invoice_list', 'icon': 'fas fa-file-invoice-dollar', 'priority': 5},
        {'name': 'العملاء', 'url': 'customer_list', 'icon': 'fas fa-users', 'priority': 4},
        {'name': 'الموردون', 'url': 'supplier_list', 'icon': 'fas fa-truck-loading', 'priority': 3},
        {'name': 'التقارير', 'url': 'reports_dashboard', 'icon': 'fas fa-chart-line', 'priority': 2},
        {'name': 'الموظفين', 'url': 'user_list', 'icon': 'fas fa-users-cog', 'priority': 1},
        {'name': 'الإعدادات', 'url': 'settings', 'icon': 'fas fa-cog', 'priority': 0},
    ]

    try:
        config_setting = SystemSettings.objects.get(key='navbar_config')
        custom_config = json.loads(config_setting.value)
        # Merge or override defaults based on custom_config
        # For now, let's just use the order if provided
        # custom_config expected format: {'order': ['dashboard', 'pos', ...], 'visibility': {...}}
        if 'order' in custom_config:
            items_dict = {item['url']: item for item in default_items}
            ordered_items = []
            for url_name in custom_config['order']:
                if url_name in items_dict:
                    ordered_items.append(items_dict[url_name])
            
            # Add any missing items at the end
            for item in default_items:
                if item not in ordered_items:
                    ordered_items.append(item)
            
            # Assign priority based on reverse index (first item = highest priority)
            total = len(ordered_items)
            for i, item in enumerate(ordered_items):
                item['priority'] = total - i
            
            items = ordered_items
        else:
            items = default_items
    except (SystemSettings.DoesNotExist, json.JSONDecodeError, KeyError):
        items = default_items

    return {
        'navbar_items': items
    }
