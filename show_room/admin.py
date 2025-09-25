from django.contrib import admin

# Register your models here.
from django.contrib import admin
from show_room.models import Car, CarInvestment


class CarInvestmentInline(admin.TabularInline):
    """
    Inline to add/edit CarInvestments directly inside Car admin.
    """
    model = CarInvestment
    extra = 1
    fields = ("investor", "amount", "percentage_share", "profit_share")
    readonly_fields = ("percentage_share", "profit_share")


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "model_name",
        "car_number",
        "total_amount",
        "admin_percentage",
        "total_invested",
        "remaining_amount",
    )
    search_fields = ("model_name", "car_number")
    list_filter = ("id",)
    inlines = [CarInvestmentInline]


@admin.register(CarInvestment)
class CarInvestmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "car",
        "investor",
        "amount",
        "percentage_share",
        "profit_share",
    )
    search_fields = ("car__model_name", "investor__email")
    list_filter = ("id",)
