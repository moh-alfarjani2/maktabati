import random
import string
from decimal import Decimal
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model

from apps.books.models import Product, Category
from apps.sales.models import Customer, SaleInvoice, InvoiceItem
from apps.purchases.models import Supplier, PurchaseInvoice, PurchaseInvoiceItem
from apps.inventory.models import InventoryMovement

User = get_user_model()

# --- MOCK DATA ---
CATEGORIES = ['روايات', 'تطوير الذات', 'تاريخ', 'سيرة ذاتية', 'أدب مترجم', 'فلسفة', 'أطفال', 'علوم ودين']

BOOKS = [
    # (Title, Author, Category, Cost, Price, BaseStock)
    ('مقدمة ابن خلدون', 'ابن خلدون', 'تاريخ', 40, 85, 20),
    ('فن اللامبالاة', 'مارك مانسون', 'تطوير الذات', 35, 70, 50),
    ('الخيميائي', 'باولو كويلو', 'أدب مترجم', 25, 50, 40),
    ('قوة العادات', 'تشارلز دويج', 'تطوير الذات', 45, 90, 30),
    ('البؤساء', 'فيكتور هوجو', 'روايات', 60, 120, 15),
    ('عبقرية محمد', 'عباس محمود العقاد', 'سيرة ذاتية', 20, 45, 25),
    ('نظرية الفستق', 'فهد الأحمدي', 'تطوير الذات', 30, 65, 60),
    ('أولاد حارتنا', 'نجيب محفوظ', 'روايات', 35, 75, 20),
    ('قواعد العشق الأربعون', 'إليف شافاق', 'روايات', 40, 80, 45),
    ('كليلة ودمنة', 'ابن المقفع', 'أطفال', 20, 40, 35),
    ('العادات الذرية', 'جيمس كلير', 'تطوير الذات', 50, 95, 80),
    ('شيفره دافنشي', 'دان براون', 'روايات', 45, 90, 30),
    ('عالم صوفي', 'جوستاين غاردر', 'فلسفة', 55, 110, 20),
    ('حي بن يقظان', 'ابن طفيل', 'فلسفة', 25, 55, 15),
    ('لأنك الله', 'علي الفيفي', 'علوم ودين', 25, 50, 50),
    ('الرحيق المختوم', 'صفي الرحمن المباركفوري', 'تاريخ', 40, 90, 40),
    ('أغنى رجل في بابل', 'جورج كلاسون', 'تطوير الذات', 20, 45, 30),
    ('مئة عام من العزلة', 'غابرييل غارثيا ماركيث', 'أدب مترجم', 40, 85, 25),
    ('الجريمة والعقاب', 'فيودور دوستويفسكي', 'أدب مترجم', 50, 100, 20),
    ('مزرعة الحيوان', 'جورج أورويل', 'أدب مترجم', 25, 55, 35),
    ('الأب الغني والأب الفقير', 'روبرت كيوساكي', 'تطوير الذات', 40, 80, 50),
    ('تاريخ الأمم والملوك', 'الطبري', 'تاريخ', 120, 250, 5),
    ('لا تحزن', 'عائض القرني', 'علوم ودين', 35, 70, 40),
    ('أرض زيكولا', 'عمرو عبد الحميد', 'روايات', 30, 65, 70),
]

CUSTOMERS = [
    ('أحمد محمد', '0501234567'), ('خالد عبد الله', '0559876543'), 
    ('سارة العلي', '0541122334'), ('فاطمة سعد', '0567788990'),
    ('عمر الفارس', '0509988776'), ('محمود كمال', '0555544332'),
]

SUPPLIERS = [
    ('مكتبة جرير (جملة)', '0114620000'), ('دار المعارف', '0112233445'),
    ('الدار العربية للعلوم', '0500001111'), ('دار الشروق', '0555552222'),
]

class Command(BaseCommand):
    help = 'Generates realistic mock data (Products, Invoices, Customers) spanning a year'

    def generate_random_id(self, length=8):
        return ''.join(random.choices(string.digits, k=length))

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Starting mock data generation... This may take a moment."))

        # 1. Get or Create Superuser
        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            admin = User.objects.create_superuser('admin_mock', 'admin@example.com', 'admin')
            self.stdout.write(self.style.SUCCESS("Created superuser 'admin_mock'."))

        # 2. Categories
        cat_map = {}
        for c_name in CATEGORIES:
            cat, _ = Category.objects.get_or_create(name=c_name)
            cat_map[c_name] = cat
        self.stdout.write(self.style.SUCCESS(f"Created {len(CATEGORIES)} categories."))

        # 3. Suppliers & Customers
        supplier_objs = []
        for name, phone in SUPPLIERS:
            s, _ = Supplier.objects.get_or_create(name=name, defaults={'phone': phone})
            supplier_objs.append(s)

        customer_objs = []
        for name, phone in CUSTOMERS:
            c, _ = Customer.objects.get_or_create(name=name, defaults={'phone': phone})
            customer_objs.append(c)

        self.stdout.write(self.style.SUCCESS(f"Created {len(supplier_objs)} suppliers and {len(customer_objs)} customers."))

        # 4. Products
        product_objs = []
        for title, author, cat_name, cost, price, base_stock in BOOKS:
            b, created = Product.objects.get_or_create(
                name=title,
                defaults={
                    'author': author,
                    'purchase_price': cost,
                    'selling_price': price,
                    'current_stock': base_stock, # Initial stock, will be updated by purchases
                    'avg_cost': cost,
                    'last_purchase_price': cost,
                    'created_by': admin
                }
            )
            if created:
                b.categories.add(cat_map[cat_name])
            product_objs.append(b)

        self.stdout.write(self.style.SUCCESS(f"Created {len(product_objs)} books."))

        # Delete existing tracking optionally, but we'll just append
        # SaleInvoice.objects.all().delete()
        # PurchaseInvoice.objects.all().delete()

        # 5. Generate Historical Purchase Invoices (to build up stock)
        # 1 invoice per month for 12 months
        now = timezone.now()
        for month_offset in range(12, 0, -1):
            invoice_date = now - timedelta(days=month_offset * 30 + random.randint(1, 15))
            
            pi = PurchaseInvoice.objects.create(
                supplier=random.choice(supplier_objs),
                created_by=admin,
                status='approved',
                payment_method=random.choice(['cash', 'transfer']),
                invoice_date=invoice_date.date()
            )
            # Override created_at to simulate history
            PurchaseInvoice.objects.filter(id=pi.id).update(created_at=invoice_date)

            total_pur = Decimal('0')
            # Select 10 random books to restock
            for p in random.sample(product_objs, 10):
                qty = Decimal(random.randint(10, 30))
                cost = p.purchase_price
                PurchaseInvoiceItem.objects.create(
                    invoice=pi,
                    product=p,
                    quantity=qty,
                    unit_price=cost
                )
                total_pur += (qty * cost)
                
                # Update actual stock
                p.current_stock += qty
                p.save(update_fields=['current_stock'])
                
                # Mock Inventory Movement
                InventoryMovement.objects.create(
                    product=p,
                    user=admin,
                    movement_type='purchase',
                    quantity_change=qty,
                    quantity_after=p.current_stock,
                    reference=f"شراء (موك) #{pi.invoice_id}",
                    notes="Mock generation"
                )
                InventoryMovement.objects.filter(id=InventoryMovement.objects.last().id).update(created_at=invoice_date)
            
            # Simple tax calc
            tax = total_pur * Decimal('0.15')
            pi.subtotal = total_pur
            pi.tax_amount = tax
            pi.total_amount = total_pur + tax
            pi.amount_paid = pi.total_amount
            pi.save()

        self.stdout.write(self.style.SUCCESS("Generated 12 historical purchase invoices (1 per month)."))

        # 6. Generate Historical Sale Invoices
        # ~100 invoices over the last year
        for i in range(150):
            days_ago = random.randint(0, 365)
            invoice_date = now - timedelta(days=days_ago)
            # Add random hours/minutes
            invoice_date = invoice_date.replace(hour=random.randint(9, 21), minute=random.randint(0, 59))

            customer = random.choice(customer_objs) if random.random() > 0.3 else None

            si = SaleInvoice.objects.create(
                customer=customer,
                cashier=admin,
                status='completed',
                payment_method=random.choice(['cash', 'card', 'card', 'cash']) # slight bias to card/cash
            )
            # Update date
            SaleInvoice.objects.filter(id=si.id).update(created_at=invoice_date)

            num_items = random.randint(1, 4)
            subtotal = Decimal('0')
            total_cost = Decimal('0')

            for p in random.sample(product_objs, num_items):
                qty = Decimal(random.randint(1, 3))
                price = p.selling_price
                cost = p.avg_cost or p.purchase_price

                InvoiceItem.objects.create(
                    invoice=si,
                    product=p,
                    quantity=qty,
                    unit_price=price,
                    cost_price=cost,
                    subtotal=qty * price
                )
                subtotal += (qty * price)
                total_cost += (qty * cost)

                # Update actual stock
                p.current_stock -= qty
                p.save(update_fields=['current_stock'])

                # Mock inventory
                InventoryMovement.objects.create(
                    product=p,
                    user=admin,
                    movement_type='sale',
                    quantity_change=-qty,
                    quantity_after=p.current_stock,
                    reference=f"بيع (موك) #{si.invoice_id}"
                )
                InventoryMovement.objects.filter(id=InventoryMovement.objects.last().id).update(created_at=invoice_date)

            tax = subtotal * Decimal('0.15')
            si.subtotal = subtotal
            si.tax_amount = tax
            si.total_amount = subtotal + tax
            si.amount_paid = si.total_amount
            si.cost_amount = total_cost
            si.profit_amount = subtotal - total_cost # Note: disregarding item level discounts for simplicity here
            si.save()

        self.stdout.write(self.style.SUCCESS("Generated 150 historical sale invoices over the last 365 days."))
        self.stdout.write(self.style.SUCCESS("Mock data generation completed successfully!"))
