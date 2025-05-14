from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Sum, Min, Count
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings

from .forms import CustomUserForm, CustomLoginForm, ProductForm
from .models import Product, Sale, Credit, CreditItem, User
from django.contrib.auth.models import User as AuthUser
from django.contrib.auth import get_user_model

# Test your email settings by adding this temporary view:
from django.core.mail import send_mail
from django.http import HttpResponse

def test_email(request):
    try:
        send_mail(
            'Test Email',
            'This is a test email from Django.',
            settings.DEFAULT_FROM_EMAIL,
            ['recipient@example.com'],  # Change to your email
            fail_silently=False,
        )
        return HttpResponse("Email sent successfully!")
    except Exception as e:
        return HttpResponse(f"Failed to send email: {str(e)}")
# ==============================
# 🔐 Authentication Views
# ==============================

def register(request):
    """Handle new user registration with admin approval workflow."""
    if request.method == 'POST':
        form = CustomUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True
            user.is_approved = False
            user.save()
            
            # Notify admins
            superusers = User.objects.filter(is_superuser=True)
            if superusers.exists():
                superuser_emails = [su.email for su in superusers]
                send_mail(
                    'New Account Registration - Approval Required',
                    f'A new user has registered:\n\nUsername: {user.username}\n'
                    f'Email: {user.email}\nPhone: {user.phone or "Not provided"}',
                    settings.DEFAULT_FROM_EMAIL,
                    superuser_emails,
                    fail_silently=True
                )

            # Notify user
            send_mail(
                'Registration Received',
                'Your account is under review. You will be notified once approved.',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True
            )

            messages.success(request, "Account created! Please wait for admin approval.")
            return redirect('login')
    else:
        form = CustomUserForm()
    
    return render(request, 'inventory/register.html', {'form': form})


def user_login(request):
    """Handle user login with username/email/phone."""
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_approved:
                login(request, user)
                return redirect('dashboard')
            messages.error(request, "Account pending approval. Please contact admin.")
        else:
            messages.error(request, "Invalid credentials.")
    else:
        form = CustomLoginForm()
    
    return render(request, 'inventory/dashboard.html', {'form': form})


# ==============================
# 📊 Dashboard & Reports Views
# ==============================

@login_required
def dashboard(request):
    """Display main dashboard with key metrics."""
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)

    context = {
        'total_products': Product.objects.count(),
        'total_sales': Sale.objects.aggregate(total=Sum('total_price'))['total'] or 0,
        'total_credits': Credit.objects.filter(is_paid=False).aggregate(total=Sum('amount'))['total'] or 0,
        'sales_count': Sale.objects.count(),
        'today_sales': Sale.objects.filter(date_sold__date=today).aggregate(total=Sum('total_price'))['total'] or 0,
        'weekly_sales': Sale.objects.filter(date_sold__date__gte=week_ago).aggregate(total=Sum('total_price'))['total'] or 0,
        'top_debts': Credit.objects.filter(is_paid=False).order_by('-date_issued')[:5],
        'debt_count': Credit.objects.filter(is_paid=False).count(),
    }
    return render(request, 'inventory/dashboard.html', context)


@login_required
def sales_report(request):
    """Generate JSON sales report data."""
    try:
        start_date = (datetime.strptime(request.GET['start_date'], '%Y-%m-%d').date()) \
            if 'start_date' in request.GET else timezone.now().date() - timedelta(days=30)
        end_date = (datetime.strptime(request.GET['end_date'], '%Y-%m-%d').date() 
            if 'end_date' in request.GET else timezone.now().date())
    except ValueError:
        start_date = timezone.now().date() - timedelta(days=30)
        end_date = timezone.now().date()

    # Sales data by date
    sales_data = (Sale.objects
        .filter(date_sold__date__range=(start_date, end_date))
        .annotate(date=timezone.TruncDate('date_sold'))
        .values('date')
        .annotate(total=Sum('total_price'))
        .order_by('date'))
    
    # Generate complete date range with totals
    labels, totals = [], []
    current_date = start_date
    while current_date <= end_date:
        labels.append(current_date.strftime('%Y-%m-%d'))
        sale = next((item for item in sales_data if item['date'] == current_date), None)
        totals.append(float(sale['total']) if sale else 0)
        current_date += timedelta(days=1)

    # Best selling product
    best_product = (Sale.objects
        .filter(date_sold__date__range=(start_date, end_date))
        .values('product__name')
        .annotate(total_quantity=Sum('quantity_sold'))
        .order_by('-total_quantity')
        .first() or {'product__name': None, 'total_quantity': 0})

    return JsonResponse({
        'labels': labels,
        'totals': totals,
        'total_sales': sum(totals),
        'avg_sales': sum(totals) / len(totals) if totals else 0,
        'total_transactions': Sale.objects.filter(date_sold__date__range=(start_date, end_date)).count(),
        'best_product': {
            'name': best_product['product__name'],
            'quantity': best_product['total_quantity']
        },
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d')
    })


@login_required
def report_page(request):
    """Display sales report page."""
    today = timezone.now().date()
    return render(request, 'inventory/report.html', {
        'default_start_date': (today - timedelta(days=30)).strftime('%Y-%m-%d'),
        'default_end_date': today.strftime('%Y-%m-%d')
    })


# ==============================
# 🛒 Product Management Views
# ==============================

@login_required
def product_list(request):
    """List all products."""
    return render(request, 'inventory/product_list.html', {
        'products': Product.objects.all()
    })


@login_required
def add_product(request):
    """Add new product."""
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product added!')
            return redirect('product_list')
    else:
        form = ProductForm()
    
    return render(request, 'inventory/add_product.html', {'form': form})


@login_required
def update_product(request, pk):
    """Edit existing product."""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated!')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'inventory/update_product.html', {
        'form': form,
        'product': product
    })


@login_required
def delete_product(request, pk):
    """Delete product."""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted!')
        return redirect('product_list')
    
    return render(request, 'inventory/delete_product.html', {'product': product})


# ==============================
# 💰 Sales & Credit Views
# ==============================

@login_required
def record_sale(request):
    """Record a new sale."""
    products = Product.objects.all()
    
    if request.method == 'POST':
        product = get_object_or_404(Product, id=request.POST['product'])
        quantity = int(request.POST['quantity'])
        
        if quantity > product.quantity:
            return render(request, 'inventory/record_sale.html', {
                'error': 'Insufficient stock',
                'products': products
            })
        
        Sale.objects.create(
            product=product,
            quantity_sold=quantity,
            total_price=quantity * product.selling_price,
            date_sold=timezone.now()
        )
        
        product.quantity -= quantity
        product.save()
        messages.success(request, 'Sale recorded!')
        return redirect('dashboard')
    
    return render(request, 'inventory/record_sale.html', {'products': products})


@login_required
def credit_list(request):
    """List credit transactions with filtering."""
    credits = Credit.objects.all().prefetch_related('items__product').order_by('-date_issued')
    
    # Apply filters
    if status := request.GET.get('status'):
        credits = credits.filter(is_paid=(status == 'paid'))
    if customer := request.GET.get('customer'):
        credits = credits.filter(customer_name__icontains=customer)
    
    return render(request, 'inventory/credit_list.html', {
        'credits': credits,
        'total_unpaid': Credit.objects.filter(is_paid=False).aggregate(total=Sum('amount'))['total'] or 0
    })


@login_required
def debt_summary(request):
    """Show debt summary by customer."""
    unpaid_credits = Credit.objects.filter(is_paid=False).order_by('date_issued')
    
    customer_debts = unpaid_credits.values('customer_name', 'phone').annotate(
        total_debt=Sum('amount'),
        oldest_debt=Min('date_issued'),
        credit_count=Count('id')
    ).order_by('-total_debt')
    
    return render(request, 'inventory/debt_summary.html', {
        'customer_debts': customer_debts,
        'summary_stats': {
            'total_unpaid': unpaid_credits.aggregate(total=Sum('amount'))['total'] or 0,
            'total_customers': customer_debts.count(),
            'total_credits': unpaid_credits.count()
        },
        'unpaid_credits': unpaid_credits
    })


@login_required
def mark_credit_paid(request, pk):
    """Mark a credit as paid."""
    credit = get_object_or_404(Credit, pk=pk)
    
    if request.method == 'POST' and not credit.is_paid:
        credit.mark_as_paid(approved_by_user=request.user)
        return redirect('credit_list')
    
    return render(request, 'inventory/mark_credit_paid.html', {
        'credit': credit,
        'original_date': credit.date_issued,
        'sale_amount': credit.amount
    })


@login_required
def issue_credit(request):
    """Issue new credit with multiple products."""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Validate required fields
                if not (customer := request.POST.get('customer', '').strip()):
                    raise ValueError("Customer name is required")
                
                # Create credit record
                credit = Credit.objects.create(
                    customer_name=customer,
                    phone=request.POST.get('phone', '').strip() or None,
                    amount=0,
                    is_paid=False,
                    notes=request.POST.get('notes', '').strip() or None,
                    created_by=request.user
                )
                
                # Process products
                total_amount = 0
                product_ids = request.POST.getlist('products[]')
                quantities = request.POST.getlist('quantities[]')
                
                if not product_ids or not quantities:
                    raise ValueError("Please add at least one product")
                
                for product_id, quantity_str in zip(product_ids, quantities):
                    if not product_id or not quantity_str:
                        continue
                    
                    product = Product.objects.get(id=product_id)
                    quantity = int(quantity_str)
                    
                    if quantity <= 0:
                        raise ValueError(f"Invalid quantity for {product.name}")
                    if quantity > product.quantity:
                        raise ValueError(f"Insufficient stock for {product.name}")
                    
                    CreditItem.objects.create(
                        credit=credit,
                        product=product,
                        quantity=quantity,
                        unit_price=product.selling_price
                    )
                    
                    product.quantity -= quantity
                    product.save()
                    total_amount += quantity * product.selling_price
                
                if total_amount == 0:
                    raise ValueError("No valid products added")
                
                credit.amount = total_amount
                credit.save()
                
                messages.success(request, f"Credit issued for KES {total_amount:.2f}")
                return redirect('credit_list')
                
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return render(request, 'inventory/issue_credit.html', {
                'products': Product.objects.filter(quantity__gt=0),
                'preserved_data': {
                    'customer': request.POST.get('customer', ''),
                    'phone': request.POST.get('phone', ''),
                    'notes': request.POST.get('notes', ''),
                    'product_ids': request.POST.getlist('products[]'),
                    'quantities': request.POST.getlist('quantities[]')
                }
            })
    
    return render(request, 'inventory/issue_credit.html', {
        'products': Product.objects.filter(quantity__gt=0),
        'title': 'Issue New Credit'
    })