from django.contrib import admin

# Register your models here.
from django.contrib import admin
from show_room.models import Car, CarInvestment, CarExpense


class CarInvestmentInline(admin.TabularInline):
    """
    Inline to add/edit CarInvestments directly inside Car admin.
    """
    model = CarInvestment
    extra = 1
    fields = ("investor", "amount", "total_contribution", "investment_share", "profit_amount", "total_return")
    readonly_fields = ("total_contribution", "investment_share", "profit_amount", "total_return")


class CarExpenseInline(admin.TabularInline):
    """
    Inline to add/edit CarExpenses directly inside Car admin.
    """
    model = CarExpense
    extra = 1
    fields = ("investor", "amount", "description")
    readonly_fields = ("created",)


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "model_name",
        "car_number",
        "total_amount",
        "sold_amount",
        "admin_percentage",
        "total_invested",
        "total_expenses",
        "total_invested_with_expenses",
        "remaining_amount",
        "profit",
    )
    search_fields = ("model_name", "car_number")
    list_filter = ("status", "fuel_type", "transmission")
    inlines = [CarInvestmentInline, CarExpenseInline]
    
    def get_readonly_fields(self, request, obj=None):
        readonly = ["total_invested", "total_expenses", "total_invested_with_expenses", "remaining_amount", "profit"]
        return readonly


@admin.register(CarInvestment)
class CarInvestmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "car",
        "investor",
        "amount",
        "total_contribution",
        "investment_share",
        "profit_amount",
        "total_return",
    )
    search_fields = ("car__model_name", "investor__email")
    list_filter = ("car__status",)
    readonly_fields = ("total_contribution", "investment_share", "profit_amount", "total_return")


@admin.register(CarExpense)
class CarExpenseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "car",
        "investor",
        "amount",
        "description",
        "created",
    )
    search_fields = ("car__model_name", "investor__email", "description")
    list_filter = ("created", "car__status")
    readonly_fields = ("created",)
