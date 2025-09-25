from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Sum, Count
from show_room.models import Car, CarInvestment, CarExpense


class CarInvestmentInline(admin.TabularInline):
    """Enhanced inline for CarInvestments with better display"""
    model = CarInvestment
    extra = 0
    fields = ("investor", "amount", "total_contribution", "investment_share", "profit_amount", "total_return")
    readonly_fields = ("total_contribution", "investment_share", "profit_amount", "total_return")
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('investor')


class CarExpenseInline(admin.TabularInline):
    """Enhanced inline for CarExpenses with better display"""
    model = CarExpense
    extra = 0
    fields = ("investor", "amount", "description", "created")
    readonly_fields = ("created",)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('investor').order_by('-created')


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    """Enhanced Car admin with better organization and visual improvements"""
    
    list_display = (
        "car_info", "status_badge", "financial_summary", 
        "investment_progress", "profit_status", "view_actions"
    )
    list_filter = ("status", "fuel_type", "transmission", "brand", "year")
    search_fields = ("model_name", "car_number", "brand")
    ordering = ("-created",)
    
    fieldsets = (
        ('Basic Information', {
            'fields': (('brand', 'model_name'), ('car_number', 'year'), ('color', 'status'))
        }),
        ('Specifications', {
            'fields': (('engine_capacity', 'fuel_type'), ('transmission', 'mileage')),
            'classes': ('collapse',)
        }),
        ('Financial Details', {
            'fields': (('total_amount', 'sold_amount'), 'admin_percentage'),
        }),
        ('Calculated Fields', {
            'fields': (
                ('total_invested', 'total_expenses'), 
                ('total_invested_with_expenses', 'remaining_amount'), 
                'profit'
            ),
            'classes': ('collapse',),
            'description': 'These fields are automatically calculated based on investments and expenses.'
        }),
    )
    
    readonly_fields = (
        "total_invested", "total_expenses", "total_invested_with_expenses", 
        "remaining_amount", "profit"
    )
    
    inlines = [CarInvestmentInline, CarExpenseInline]
    
    def car_info(self, obj):
        """Display car information with styling"""
        return format_html(
            '<strong>{} {}</strong><br>'
            '<small style="color: #666;">{}</small>',
            obj.brand, obj.model_name, obj.car_number
        )
    car_info.short_description = 'Car Details'
    
    def status_badge(self, obj):
        """Display status with color coding"""
        colors = {
            'available': '#28a745',
            'booked': '#ffc107', 
            'sold': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.status.upper()
        )
    status_badge.short_description = 'Status'
    
    def financial_summary(self, obj):
        """Display financial summary"""
        return format_html(
            '<div style="font-size: 12px;">'
            '<strong>Total: ${}</strong><br>'
            '<span style="color: #28a745;">Sold: ${}</span>'
            '</div>',
            f"{obj.total_amount:,.0f}",
            f"{obj.sold_amount or 0:,.0f}"
        )
    financial_summary.short_description = 'Financials'
    
    def investment_progress(self, obj):
        """Display investment progress bar"""
        if obj.total_amount > 0:
            percentage = (obj.total_invested / obj.total_amount) * 100
            color = '#28a745' if percentage >= 100 else '#ffc107'
            return format_html(
                '<div style="width: 100px; background-color: #e9ecef; border-radius: 3px; overflow: hidden;">'
                '<div style="width: {}%; background-color: {}; height: 20px; text-align: center; '
                'line-height: 20px; color: white; font-size: 10px; font-weight: bold;">'
                '{}%</div></div>'
                '<small>${} / ${}</small>',
                min(percentage, 100), color, f"{percentage:.0f}", 
                f"{obj.total_invested:,.0f}", f"{obj.total_amount:,.0f}"
            )
        return "N/A"
    investment_progress.short_description = 'Investment Progress'
    
    def profit_status(self, obj):
        """Display profit status with color coding"""
        if obj.sold_amount:
            profit = obj.profit
            color = '#28a745' if profit > 0 else '#dc3545'
            return format_html(
                '<span style="color: {}; font-weight: bold;">${}</span>',
                color, f"{profit:,.2f}"
            )
        return format_html('<span style="color: #6c757d;">Not Sold</span>')
    profit_status.short_description = 'Profit/Loss'
    
    def view_actions(self, obj):
        """Display action buttons"""
        return format_html(
            '<a href="{}" style="background: #007cba; color: white; padding: 2px 6px; '
            'text-decoration: none; border-radius: 3px; font-size: 11px;">View</a>',
            reverse('admin:show_room_car_change', args=[obj.pk])
        )
    view_actions.short_description = 'Actions'


@admin.register(CarInvestment)
class CarInvestmentAdmin(admin.ModelAdmin):
    """Enhanced CarInvestment admin"""
    
    list_display = (
        "investment_info", "car_link", "investor_info", 
        "contribution_details", "returns_info"
    )
    list_filter = ("car__status", "car__brand", "created")
    search_fields = ("car__model_name", "car__car_number", "investor__email", "investor__first_name")
    ordering = ("-created",)
    
    fieldsets = (
        ('Investment Details', {
            'fields': (('car', 'investor'), 'amount')
        }),
        ('Calculated Returns', {
            'fields': (
                ('total_contribution', 'investment_share'), 
                ('profit_amount', 'total_return')
            ),
            'classes': ('collapse',),
            'description': 'These fields are automatically calculated.'
        }),
    )
    
    readonly_fields = ("total_contribution", "investment_share", "profit_amount", "total_return")
    
    def investment_info(self, obj):
        """Display investment amount with styling"""
        return format_html(
            '<strong style="color: #28a745;">${}</strong><br>'
            '<small>{}</small>',
            f"{obj.amount:,.2f}", obj.created.strftime('%Y-%m-%d')
        )
    investment_info.short_description = 'Investment'
    
    def car_link(self, obj):
        """Display car with link to car admin"""
        url = reverse('admin:show_room_car_change', args=[obj.car.pk])
        return format_html(
            '<a href="{}" style="text-decoration: none;">'
            '<strong>{}</strong><br>'
            '<small style="color: #666;">{}</small>'
            '</a>',
            url, obj.car, obj.car.car_number
        )
    car_link.short_description = 'Car'
    
    def investor_info(self, obj):
        """Display investor information"""
        url = reverse('admin:users_user_change', args=[obj.investor.pk])
        full_name = f"{obj.investor.first_name} {obj.investor.last_name}".strip()
        return format_html(
            '<a href="{}" style="text-decoration: none;">'
            '<strong>{}</strong><br>'
            '<small style="color: #666;">{}</small>'
            '</a>',
            url, full_name or obj.investor.email, obj.investor.email
        )
    investor_info.short_description = 'Investor'
    
    def contribution_details(self, obj):
        """Display contribution details"""
        return format_html(
            '<div style="font-size: 12px;">'
            'Total: <strong>${}</strong><br>'
            'Share: <strong>{}%</strong>'
            '</div>',
            f"{obj.total_contribution:,.2f}", f"{obj.investment_share:.1f}"
        )
    contribution_details.short_description = 'Contribution'
    
    def returns_info(self, obj):
        """Display returns information"""
        if obj.car.sold_amount:
            color = '#28a745' if obj.profit_amount > 0 else '#dc3545'
            return format_html(
                '<div style="font-size: 12px;">'
                'Profit: <span style="color: {}; font-weight: bold;">${}</span><br>'
                'Total Return: <strong>${}</strong>'
                '</div>',
                color, f"{obj.profit_amount:,.2f}", f"{obj.total_return:,.2f}"
            )
        return format_html('<span style="color: #6c757d;">Pending Sale</span>')
    returns_info.short_description = 'Returns'


@admin.register(CarExpense)
class CarExpenseAdmin(admin.ModelAdmin):
    """Enhanced CarExpense admin"""
    
    list_display = (
        "expense_info", "car_link", "investor_info", 
        "description_short", "date_added"
    )
    list_filter = ("created", "car__status", "car__brand")
    search_fields = ("car__model_name", "car__car_number", "investor__email", "description")
    ordering = ("-created",)
    date_hierarchy = 'created'
    
    fieldsets = (
        ('Expense Details', {
            'fields': (('car', 'investor'), ('amount', 'description'))
        }),
        ('Timestamps', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ("created", "modified")
    
    def expense_info(self, obj):
        """Display expense amount with styling"""
        return format_html(
            '<strong style="color: #dc3545;">${}</strong>',
            f"{obj.amount:,.2f}"
        )
    expense_info.short_description = 'Amount'
    
    def car_link(self, obj):
        """Display car with link"""
        url = reverse('admin:show_room_car_change', args=[obj.car.pk])
        return format_html(
            '<a href="{}" style="text-decoration: none;">'
            '<strong>{}</strong><br>'
            '<small style="color: #666;">{}</small>'
            '</a>',
            url, obj.car, obj.car.car_number
        )
    car_link.short_description = 'Car'
    
    def investor_info(self, obj):
        """Display investor information"""
        url = reverse('admin:users_user_change', args=[obj.investor.pk])
        full_name = f"{obj.investor.first_name} {obj.investor.last_name}".strip()
        return format_html(
            '<a href="{}" style="text-decoration: none;">{}</a>',
            url, full_name or obj.investor.email
        )
    investor_info.short_description = 'Investor'
    
    def description_short(self, obj):
        """Display truncated description"""
        if len(obj.description) > 50:
            return f"{obj.description[:50]}..."
        return obj.description
    description_short.short_description = 'Description'
    
    def date_added(self, obj):
        """Display formatted date"""
        return obj.created.strftime('%Y-%m-%d %H:%M')
    date_added.short_description = 'Date Added'
