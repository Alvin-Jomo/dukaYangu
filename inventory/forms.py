from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Product

User = get_user_model()

class CustomUserForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Email',
            'autocomplete': 'email'
        })
    )
    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Phone (optional)',
            'autocomplete': 'tel'
        })
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Username',
            'autocomplete': 'username'
        })
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Password',
            'autocomplete': 'new-password'
        }),
        help_text="Your password must contain at least 8 characters."
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Confirm Password',
            'autocomplete': 'new-password'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already in use.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if len(username) < 4:
            raise ValidationError("Username must be at least 4 characters long.")
        return username

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone and User.objects.filter(phone=phone).exists():
            raise ValidationError("This phone number is already in use.")
        return phone


class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Username/Email/Phone',
            'autocomplete': 'username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Password',
            'autocomplete': 'current-password'
        })
    )

    def clean(self):
        username_or_email_or_phone = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if not username_or_email_or_phone or not password:
            raise forms.ValidationError("Please enter both username and password.")

        UserModel = get_user_model()
        user_obj = None

        # Check if input matches email format
        if '@' in username_or_email_or_phone:
            try:
                user_obj = UserModel.objects.get(email__iexact=username_or_email_or_phone)
            except UserModel.DoesNotExist:
                pass
        # Check if input is numeric (could be phone)
        elif username_or_email_or_phone.isdigit():
            try:
                user_obj = UserModel.objects.get(phone=username_or_email_or_phone)
            except UserModel.DoesNotExist:
                pass
        
        # If not found by email or phone, try username
        if user_obj is None:
            try:
                user_obj = UserModel.objects.get(username__iexact=username_or_email_or_phone)
            except UserModel.DoesNotExist:
                raise forms.ValidationError("Invalid login credentials.")

        if not user_obj.check_password(password):
            raise forms.ValidationError("Incorrect password.")

        if not user_obj.is_active:
            raise forms.ValidationError("This account is inactive.")

        if hasattr(user_obj, 'is_approved') and not user_obj.is_approved:
            raise forms.ValidationError("Your account is pending approval.")

        self.user_cache = user_obj
        return self.cleaned_data


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'quantity', 'cost_price', 'selling_price']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Product Name'
            }),
            'category': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Category'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Stock Quantity',
                'min': '0'
            }),
            'cost_price': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Cost Price',
                'min': '0',
                'step': '0.01'
            }),
            'selling_price': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Selling Price',
                'min': '0',
                'step': '0.01'
            }),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity < 0:
            raise ValidationError("Quantity cannot be negative.")
        return quantity

    def clean(self):
        cleaned_data = super().clean()
        cost_price = cleaned_data.get('cost_price')
        selling_price = cleaned_data.get('selling_price')
        
        if cost_price and selling_price and selling_price < cost_price:
            raise ValidationError("Selling price cannot be less than cost price.")
        return cleaned_data