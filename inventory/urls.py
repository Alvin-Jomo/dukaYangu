# urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='inventory/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.add_product, name='add_product'),
    path('sales/record/', views.record_sale, name='record_sale'),
    path('credits/', views.credit_list, name='credit_list'),  # Add this line
    path('credits/issue/', views.issue_credit, name='issue_credit'),
    path('reports/sales/', views.sales_report, name='sales_report'),
    path('reports/', views.report_page, name='report_page'),

    path('products/<int:pk>/edit/', views.update_product, name='update_product'),
    path('products/<int:pk>/delete/', views.delete_product, name='delete_product'),

    path('debts/', views.debt_summary, name='debt_summary'),
    path('credits/<int:pk>/pay/', views.mark_credit_paid, name='mark_credit_paid'),
]