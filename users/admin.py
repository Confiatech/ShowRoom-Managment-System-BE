from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Count
from users.models import User


class UserInvestmentInline(admin.TabularInline):
    """Inline display for user investments"""
    from show_room.models import CarInvestment
    model = CarInvestment
    fk_name = 'investor'
    extra = 0
    fields = ('car', 'amount', 'total_contribution', 'investment_share', 'created')
    readonly_fields = ('total_contribution', 'investment_share', 'created')
    verbose_name = "Investment"
    verbose_name_plural = "Car Investments"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('car')


class UserExpenseInline(admin.TabularInline):
    """Inline display for user expenses"""
    from show_room.models import CarExpense
    model = CarExpense
    fk_name = 'investor'
    extra = 0
    fields = ('car', 'amount', 'description', 'created')
    readonly_fields = ('created',)
    verbose_name = "Expense"
    verbose_name_plural = "Car Expenses"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('car')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Enhanced User admin with better organization and visual display"""
    
    list_display = (
        'user_info', 'role_badge', 'contact_info', 'show_room_owner','investment_summary', 
        'activity_status', 'join_date'
    )
    list_filter = ('role', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number', 'cnic')
    ordering = ('-date_joined',)
    list_per_page = 25
    
    fieldsets = (
        ('User Identity', {
            'fields': (('email', 'role'), ('first_name', 'last_name')),
            'description': 'Basic user identification and role information.'
        }),
        ('Contact Information', {
            'fields': (('phone_number', 'cnic',
            'image',
            'show_room_name',
            ), 'address'),
            'classes': ('collapse',)
        }),
        ('Account Status', {
            'fields': (('is_active', 'is_staff'), 'is_superuser'),
        }),
        ('Permissions & Groups', {
            'fields': ('groups', 'user_permissions'),
            'classes': ('collapse',),
            'description': 'User permissions and group memberships.'
        }),
        ('Important Dates', {
            'fields': (('date_joined', 'last_login'),),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('Create New User', {
            'classes': ('wide',),
            'fields': (
                ('email', 'role'), 
                ('first_name', 'last_name'), 
                ('phone_number', 'cnic'),
                ('password1', 'password2')
            ),
            'description': 'Enter the required information to create a new user account.'
        }),
    )
    
    readonly_fields = ('date_joined', 'last_login')
    inlines = [UserInvestmentInline, UserExpenseInline]
    
    def user_info(self, obj):
        """Display user information with avatar and styling"""
        full_name = f"{obj.first_name} {obj.last_name}".strip()
        display_name = full_name if full_name else obj.email.split('@')[0]
        
        # Create a simple avatar with initials
        initials = ""
        if obj.first_name and obj.last_name:
            initials = f"{obj.first_name[0]}{obj.last_name[0]}".upper()
        elif obj.first_name:
            initials = obj.first_name[0].upper()
        else:
            initials = obj.email[0].upper()
        
        return format_html(
            '<div style="display: flex; align-items: center; gap: 12px; padding: 8px; '
            'background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%); border-radius: 8px; '
            'border: 1px solid #e2e8f0;">'
            '<div style="width: 45px; height: 45px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); '
            'display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 16px; '
            'box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);">'
            '{}</div>'
            '<div>'
            '<div style="font-weight: 600; color: #1a202c; font-size: 15px; margin-bottom: 2px;">{}</div>'
            '<div style="color: #4a5568; font-size: 13px; background: #ffffff; padding: 2px 8px; '
            'border-radius: 4px; border: 1px solid #e2e8f0;">{}</div>'
            '</div>'
            '</div>',
            initials, display_name, obj.email
        )
    user_info.short_description = 'User'
    
    def role_badge(self, obj):
        """Display role with color-coded badge"""
        role_colors = {
            'admin': '#e53e3e',
            'investor': '#38a169',
            'manager': '#3182ce',
        }
        color = role_colors.get(obj.role, '#718096')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 12px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold; text-transform: uppercase;">'
            '{}</span>',
            color, obj.role
        )
    role_badge.short_description = 'Role'
    
    def contact_info(self, obj):
        """Display contact information"""
        phone = obj.phone_number or 'Not provided'
        cnic = obj.cnic or 'Not provided'
        
        return format_html(
            '<div style="background: #f8fafc; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0;">'
            '<div style="margin-bottom: 4px; color: #2d3748; font-size: 12px; font-weight: 500;">'
            '<span style="color: #667eea;">📞</span> {}</div>'
            '<div style="color: #2d3748; font-size: 12px; font-weight: 500;">'
            '<span style="color: #667eea;">🆔</span> {}</div>'
            '</div>',
            phone, cnic
        )
    contact_info.short_description = 'Contact'
    
    def investment_summary(self, obj):
        """Display investment and expense summary with visual indicators"""
        # Get aggregated data
        investment_data = obj.car_investments.aggregate(
            total_amount=Sum('amount'),
            count=Count('id')
        )
        expense_data = obj.car_expenses.aggregate(
            total_amount=Sum('amount'),
            count=Count('id')
        )
        
        total_investments = investment_data['total_amount'] or 0
        investment_count = investment_data['count'] or 0
        total_expenses = expense_data['total_amount'] or 0
        expense_count = expense_data['count'] or 0
        
        return format_html(
            '<div style="background: #f8fafc; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0;">'
            '<div style="display: flex; align-items: center; margin-bottom: 4px; '
            'background: #ffffff; padding: 4px 6px; border-radius: 4px;">'
            '<span style="color: #38a169; font-weight: bold; font-size: 12px;">💰 ${}</span>'
            '<span style="color: #4a5568; margin-left: 6px; font-size: 11px;">({} inv.)</span>'
            '</div>'
            '<div style="display: flex; align-items: center; '
            'background: #ffffff; padding: 4px 6px; border-radius: 4px;">'
            '<span style="color: #e53e3e; font-weight: bold; font-size: 12px;">💸 ${}</span>'
            '<span style="color: #4a5568; margin-left: 6px; font-size: 11px;">({} exp.)</span>'
            '</div>'
            '</div>',
            f"{total_investments:,.0f}", investment_count,
            f"{total_expenses:,.0f}", expense_count
        )
    investment_summary.short_description = 'Financial Activity'
    
    def activity_status(self, obj):
        """Display activity status with visual indicators"""
        status_color = '#38a169' if obj.is_active else '#e53e3e'
        status_bg = '#f0fff4' if obj.is_active else '#fed7d7'
        status_text = 'Active' if obj.is_active else 'Inactive'
        
        # Check if user has recent activity
        has_investments = obj.car_investments.exists()
        has_expenses = obj.car_expenses.exists()
        
        activity_indicators = []
        if has_investments:
            activity_indicators.append('📈 Investor')
        if has_expenses:
            activity_indicators.append('💳 Expenses')
        if obj.is_staff:
            activity_indicators.append('👑 Staff')
        
        return format_html(
            '<div style="background: {}; padding: 8px; border-radius: 6px; border: 1px solid {};">'
            '<div style="margin-bottom: 4px;">'
            '<span style="color: {}; font-weight: bold; font-size: 13px;">● {}</span>'
            '</div>'
            '<div style="color: #2d3748; font-size: 11px; font-weight: 500; '
            'background: #ffffff; padding: 2px 6px; border-radius: 3px;">{}</div>'
            '</div>',
            status_bg, status_color, status_color, status_text,
            ' | '.join(activity_indicators) if activity_indicators else 'No activity'
        )
    activity_status.short_description = 'Status'
    
    def join_date(self, obj):
        """Display formatted join date"""
        return format_html(
            '<div style="background: #f8fafc; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0; text-align: center;">'
            '<div style="font-size: 13px; color: #2d3748; font-weight: 600; margin-bottom: 2px;">{}</div>'
            '<div style="font-size: 11px; color: #4a5568; background: #ffffff; padding: 2px 6px; '
            'border-radius: 3px; display: inline-block;">{}</div>'
            '</div>',
            obj.date_joined.strftime('%b %d, %Y'),
            obj.date_joined.strftime('%I:%M %p')
        )
    join_date.short_description = 'Joined'
    
    def get_queryset(self, request):
        """Optimize queryset with prefetch_related for better performance"""
        return super().get_queryset(request).prefetch_related(
            'car_investments', 'car_expenses'
        )
    
    # Custom admin actions
    actions = ['activate_users', 'deactivate_users', 'export_user_summary']
    
    def activate_users(self, request, queryset):
        """Activate selected users"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} users were successfully activated.')
    activate_users.short_description = "Activate selected users"
    
    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} users were successfully deactivated.')
    deactivate_users.short_description = "Deactivate selected users"
    
    def export_user_summary(self, request, queryset):
        """Export user summary (placeholder for future implementation)"""
        count = queryset.count()
        self.message_user(request, f'Export functionality for {count} users will be implemented soon.')
    export_user_summary.short_description = "Export user summary"