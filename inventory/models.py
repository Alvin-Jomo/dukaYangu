from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.timezone import now
from django.db import transaction


class User(AbstractUser):
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    email = models.EmailField(unique=True, blank=False)  # Make email required

    def __str__(self):
        return self.username or self.email or str(self.id) 
   
    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email.split('@')[0]  # or some other default
        super().save(*args, **kwargs)
        
class Product(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=100, blank=True)
    quantity = models.PositiveIntegerField()
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Credit(models.Model):
    customer_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    date_issued = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date_paid = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_credits'
    )
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.customer_name} - KES {self.amount}"

    @property
    def status(self):
        if self.is_paid:
            return f"Paid on {self.date_paid.strftime('%Y-%m-%d') if self.date_paid else 'unknown date'} by {self.approved_by.username if self.approved_by else 'System'}"
        return "Unpaid"
    
    def get_items(self):
        return self.items.all()

    def mark_as_paid(self, approved_by_user):
        """Mark this credit as paid and create corresponding sales records."""
        with transaction.atomic():
            # Create sales records for each item
            for item in self.items.all():
                Sale.objects.create(
                    product=item.product,
                    quantity_sold=item.quantity,
                    total_price=item.total_price,
                    date_sold=now(),
                    is_credit_payment=True,
                    credit_reference=self,
                    sold_by=approved_by_user
                )
            
            # Update credit status
            self.is_paid = True
            self.date_paid = now()
            self.approved_by = approved_by_user
            self.save()

class CreditItem(models.Model):
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    @property
    def total_price(self):
        return self.quantity * self.unit_price

class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity_sold = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    date_sold = models.DateTimeField(auto_now_add=True)
    sold_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    is_credit_payment = models.BooleanField(default=False)
    credit_reference = models.ForeignKey(
        Credit, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='sales'
    )

    def __str__(self):
        return f"{self.product.name} - {self.quantity_sold}"

    class Meta:
        ordering = ['-date_sold']

class SalesMetrics(models.Model):
    date = models.DateField(unique=True)
    total_sales = models.DecimalField(max_digits=10, decimal_places=2)
    total_transactions = models.PositiveIntegerField()
    avg_sale_amount = models.DecimalField(max_digits=10, decimal_places=2)
    best_selling_product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    best_selling_quantity = models.PositiveIntegerField()
    
    class Meta:
        ordering = ['-date']
        verbose_name_plural = "Sales Metrics"