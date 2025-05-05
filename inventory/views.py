from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Sum, Min, Count
from django.db import transaction
from django.contrib import messages
from django.db import transaction

from .forms import CustomUserForm, CustomLoginForm, ProductForm
from .models import Product, Sale, Credit, CreditItem


# ============================== 
# 🔐 Authentication
# ==============================

def register(request):
    if request.method == 'POST':
        form = CustomUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomUserForm()
    return render(request, 'inventory/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomLoginForm()
    return render(request, 'inventory/login.html', {'form': form})

# ==============================
# 📊 Dashboard & Reports
# ==============================

@login_required
def dashboard(request):
    """Display dashboard with total counts and summary of sales/credits."""
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)

    total_products = Product.objects.count()
    total_sales = Sale.objects.aggregate(total=Sum('total_price'))['total'] or 0
    total_credits = Credit.objects.filter(is_paid=False).aggregate(total=Sum('amount'))['total'] or 0
    sales_count = Sale.objects.count()

    today_sales = Sale.objects.filter(date_sold__date=today).aggregate(total=Sum('total_price'))['total'] or 0
    weekly_sales = Sale.objects.filter(date_sold__date__gte=week_ago).aggregate(total=Sum('total_price'))['total'] or 0

    top_debts = Credit.objects.filter(is_paid=False).order_by('-date_issued')[:5]
    debt_count = Credit.objects.filter(is_paid=False).count()

    return render(request, 'inventory/dashboard.html', {
        'total_products': total_products,
        'total_sales': total_sales,
        'total_credits': total_credits,
        'sales_count': sales_count,
        'today_sales': today_sales,
        'weekly_sales': weekly_sales,
        'top_debts': top_debts,
        'debt_count': debt_count,
    })

@login_required
def sales_report(request):
    """Return JSON data for sales report with metrics."""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    try:
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        else:
            start_date = timezone.now().date() - timedelta(days=30)
            
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = timezone.now().date()
    except:
        start_date = timezone.now().date() - timedelta(days=30)
        end_date = timezone.now().date()
    
    sales_data = (Sale.objects
                  .filter(date_sold__date__gte=start_date, date_sold__date__lte=end_date)
                  .annotate(date=timezone.TruncDate('date_sold'))
                  .values('date')
                  .annotate(total=Sum('total_price'))
                  .order_by('date'))
    
    labels = []
    totals = []
    
    current_date = start_date
    while current_date <= end_date:
        labels.append(current_date.strftime('%Y-%m-%d'))
        sale = next((item for item in sales_data if item['date'] == current_date), None)
        totals.append(float(sale['total']) if sale else 0)
        current_date += timedelta(days=1)
    
    total_sales = sum(totals)
    days_in_period = (end_date - start_date).days + 1
    avg_sales = total_sales / days_in_period if days_in_period > 0 else 0
    
    best_product_data = (Sale.objects
                        .filter(date_sold__date__gte=start_date, date_sold__date__lte=end_date)
                        .values('product__name')
                        .annotate(total_quantity=Sum('quantity_sold'))
                        .order_by('-total_quantity')
                        .first())
    
    best_product = {
        'name': best_product_data['product__name'] if best_product_data else None,
        'quantity': best_product_data['total_quantity'] if best_product_data else 0
    }
    
    total_transactions = Sale.objects.filter(
        date_sold__date__gte=start_date, 
        date_sold__date__lte=end_date
    ).count()
    
    return JsonResponse({
        'labels': labels,
        'totals': totals,
        'total_sales': total_sales,
        'avg_sales': avg_sales,
        'total_transactions': total_transactions,
        'best_product': best_product,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d')
    })

@login_required
def report_page(request):
    """Render the report page with chart."""
    today = timezone.now().date()
    default_start_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
    default_end_date = today.strftime('%Y-%m-%d')
    
    return render(request, 'inventory/report.html', {
        'default_start_date': default_start_date,
        'default_end_date': default_end_date
    })

# ==============================
# 🛒 Products
# ==============================

@login_required
def product_list(request):
    """List all products."""
    products = Product.objects.all()
    return render(request, 'inventory/product_list.html', {'products': products})

@login_required
def add_product(request):
    """Add a new product."""
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product added successfully!')
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'inventory/add_product.html', {'form': form})

@login_required
def update_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'inventory/update_product.html', {'form': form, 'product': product})

@login_required
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully!')
        return redirect('product_list')
    return render(request, 'inventory/delete_product.html', {'product': product})

# ==============================
# 💰 Sales & Credits
# ==============================

@login_required
def record_sale(request):
    """Record a new sale, reduce stock, and timestamp the sale correctly."""
    products = Product.objects.all()

    if request.method == 'POST':
        product_id = request.POST['product']
        quantity = int(request.POST['quantity'])
        product = Product.objects.get(id=product_id)

        if quantity > product.quantity:
            return render(request, 'inventory/record_sale.html', {
                'error': 'Insufficient stock.',
                'products': products
            })

        total_price = quantity * product.selling_price

        Sale.objects.create(
            product=product,
            quantity_sold=quantity,
            total_price=total_price,
            date_sold=timezone.now()
        )

        product.quantity -= quantity
        product.save()
        messages.success(request, 'Sale recorded successfully!')
        return redirect('dashboard')

    return render(request, 'inventory/record_sale.html', {'products': products})

@login_required
def credit_list(request):
    """List all credit transactions with filter options."""
    credits = Credit.objects.all().prefetch_related('items__product').order_by('-date_issued')
    
    status = request.GET.get('status')
    if status == 'paid':
        credits = credits.filter(is_paid=True)
    elif status == 'unpaid':
        credits = credits.filter(is_paid=False)
    
    customer = request.GET.get('customer')
    if customer:
        credits = credits.filter(customer_name__icontains=customer)
    
    return render(request, 'inventory/credit_list.html', {
        'credits': credits,
        'total_unpaid': Credit.objects.filter(is_paid=False).aggregate(total=Sum('amount'))['total'] or 0
    })

@login_required
def debt_summary(request):
    """Show summary of all unpaid credits grouped by customer"""
    unpaid_credits = Credit.objects.filter(is_paid=False).order_by('date_issued')
    
    customer_debts = unpaid_credits.values('customer_name', 'phone').annotate(
        total_debt=Sum('amount'),
        oldest_debt=Min('date_issued'),
        credit_count=Count('id')
    ).order_by('-total_debt')
    
    summary_stats = {
        'total_unpaid': unpaid_credits.aggregate(total=Sum('amount'))['total'] or 0,
        'total_customers': customer_debts.count(),
        'total_credits': unpaid_credits.count()
    }
    
    return render(request, 'inventory/debt_summary.html', {
        'customer_debts': customer_debts,
        'summary_stats': summary_stats,
        'unpaid_credits': unpaid_credits
    })



@login_required
def mark_credit_paid(request, pk):
    credit = get_object_or_404(Credit, pk=pk)

    if request.method == 'POST':
        if not credit.is_paid:
            # Use the model method to mark as paid and record the sales
            credit.mark_as_paid(approved_by_user=request.user)
        
        return redirect('credit_list')

    return render(request, 'inventory/mark_credit_paid.html', {
        'credit': credit,
        'original_date': credit.date_issued,
        'sale_amount': credit.amount
    })
 
@login_required
def issue_credit(request):
    """Issue credit to a customer with multiple products."""
    products = Product.objects.filter(quantity__gt=0)

    if request.method == 'POST':
        customer = request.POST.get('customer', '').strip()
        phone = request.POST.get('phone', '').strip()
        notes = request.POST.get('notes', '').strip()
        
        product_ids = request.POST.getlist('products[]')
        quantities = request.POST.getlist('quantities[]')
        
        if not customer:
            messages.error(request, 'Customer name is required')
            return render(request, 'inventory/issue_credit.html', {
                'products': products,
                'preserved_data': {
                    'phone': phone,
                    'notes': notes,
                    'product_ids': product_ids,
                    'quantities': quantities
                }
            })
            
        if not product_ids or not quantities:
            messages.error(request, 'Please add at least one product')
            return render(request, 'inventory/issue_credit.html', {
                'products': products,
                'preserved_data': {
                    'customer': customer,
                    'phone': phone,
                    'notes': notes
                }
            })

        try:
            with transaction.atomic():
                credit = Credit.objects.create(
                    customer_name=customer,
                    phone=phone if phone else None,
                    amount=0,
                    is_paid=False,
                    notes=notes if notes else None,
                    created_by=request.user
                )
                
                total_amount = 0
                processed_products = set()
                
                for product_id, quantity_str in zip(product_ids, quantities):
                    if not product_id or not quantity_str:
                        continue
                        
                    try:
                        product = Product.objects.get(id=product_id)
                        quantity = int(quantity_str)
                        
                        if quantity <= 0:
                            raise ValueError(f"Quantity for {product.name} must be positive")
                        if product_id in processed_products:
                            raise ValueError(f"Duplicate product: {product.name}")
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
                        processed_products.add(product_id)
                        
                    except (Product.DoesNotExist, ValueError) as e:
                        raise ValueError(str(e))
                
                if total_amount == 0:
                    raise ValueError("No valid products were added")
                
                credit.amount = total_amount
                credit.save()
                
                messages.success(request, f"Credit issued successfully for KES {total_amount:.2f}")
                return redirect('credit_list')
            
        except Exception as e:
            messages.error(request, f"Failed to issue credit: {str(e)}")
            return render(request, 'inventory/issue_credit.html', {
                'products': products,
                'preserved_data': {
                    'customer': customer,
                    'phone': phone,
                    'notes': notes,
                    'product_ids': product_ids,
                    'quantities': quantities
                }
            })

    return render(request, 'inventory/issue_credit.html', {
        'products': products,
        'title': 'Issue New Credit'
    })