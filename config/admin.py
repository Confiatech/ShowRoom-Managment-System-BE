from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils.html import format_html
from django.db.models import Sum, Count, Avg
from django.urls import path
from django.shortcuts import render
from django.http import JsonResponse
from show_room.models import Car, CarInvestment, CarExpense
from users.models import User


class CustomAdminSite(AdminSite):
    """Custom admin site with enhanced dashboard"""
    
    site_header = "Car Investment Management System"
    site_title = "Car Investment Admin"
    index_title = "Dashboard"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard-stats/', self.admin_view(self.dashboard_stats), name='dashboard_stats'),
        ]
        return custom_urls + urls
    
    def dashboard_stats(self, request):
        """API endpoint for dashboard statistics"""
        # Car statistics
        total_cars = Car.objects.count()
        available_cars = Car.objects.filter(status='available').count()
        sold_cars = Car.objects.filter(status='sold').count()
        
        # Investment statistics
        total_investments = CarInvestment.objects.aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        # Expense statistics
        total_expenses = CarExpense.objects.aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        # User statistics
        total_users = User.objects.count()
        active_investors = User.objects.filter(
            car_investments__isnull=False
        ).distinct().count()
        
        # Financial overview
        cars_with_amounts = Car.objects.aggregate(
            total_car_value=Sum('total_amount'),
            total_sold_value=Sum('sold_amount')
        )
        
        stats = {
            'cars': {
                'total': total_cars,
                'available': available_cars,
                'sold': sold_cars,
                'booked': total_cars - available_cars - sold_cars
            },
            'investments': {
                'total_amount': total_investments['total'] or 0,
                'total_count': total_investments['count'] or 0,
                'average_investment': (total_investments['total'] / total_investments['count']) if total_investments['count'] else 0
            },
            'expenses': {
                'total_amount': total_expenses['total'] or 0,
                'total_count': total_expenses['count'] or 0
            },
            'users': {
                'total': total_users,
                'active_investors': active_investors
            },
            'financial': {
                'total_car_value': cars_with_amounts['total_car_value'] or 0,
                'total_sold_value': cars_with_amounts['total_sold_value'] or 0
            }
        }
        
        return JsonResponse(stats)
    
    def index(self, request, extra_context=None):
        """Enhanced admin index with dashboard widgets"""
        extra_context = extra_context or {}
        
        # Quick stats for the dashboard
        extra_context.update({
            'total_cars': Car.objects.count(),
            'total_investments': CarInvestment.objects.aggregate(Sum('amount'))['amount__sum'] or 0,
            'total_expenses': CarExpense.objects.aggregate(Sum('amount'))['amount__sum'] or 0,
            'active_investors': User.objects.filter(car_investments__isnull=False).distinct().count(),
        })
        
        return super().index(request, extra_context)


# Create custom admin site instance
admin_site = CustomAdminSite(name='custom_admin')

# Register all models with the custom admin site
from show_room.admin import CarAdmin, CarInvestmentAdmin, CarExpenseAdmin
from users.admin import UserAdmin
from show_room.models import Car, CarInvestment, CarExpense
from users.models import User

admin_site.register(Car, CarAdmin)
admin_site.register(CarInvestment, CarInvestmentAdmin)
admin_site.register(CarExpense, CarExpenseAdmin)
admin_site.register(User, UserAdmin)