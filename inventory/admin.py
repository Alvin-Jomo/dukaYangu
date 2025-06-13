from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Product, Sale, Credit
from .forms import CustomUserForm

class CustomUserAdmin(UserAdmin):
    form = CustomUserForm
    add_form = CustomUserForm
    
    list_display = ('username', 'email', 'phone', 'is_staff')
    list_filter = ('is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'phone', 'first_name', 'last_name')
    ordering = ('username',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 
                       'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'phone', 'password1', 'password2'),
        }),
    )

admin.site.register(User, CustomUserAdmin)
admin.site.register(Product)
admin.site.register(Sale)
admin.site.register(Credit)
