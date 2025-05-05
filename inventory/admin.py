from django.contrib import admin
from .models import User, Product, Sale, Credit
from django.contrib.auth.admin import UserAdmin

admin.site.register(User, UserAdmin)
admin.site.register(Product)
admin.site.register(Sale)
admin.site.register(Credit)
