from django.db import migrations


def forwards_func(apps, schema_editor):
    Product = apps.get_model("books", "Product")
    for product in Product.objects.all():
        if product.category:
            product.categories.add(product.category)


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0003_add_categories_m2m'),
    ]

    operations = [
        migrations.RunPython(forwards_func),
    ]
