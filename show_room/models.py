from django.db import models

# Create your models here.
from decimal import Decimal

from django.db import models
from django_extensions.db.models import TimeStampedModel
from django.conf import settings

class Car(TimeStampedModel):
    """
    Car details added by Admin
    """
    # Basic Information
    brand = models.CharField(max_length=150)         # e.g. Toyota, Honda, BMW
    model_name = models.CharField(max_length=150)    # e.g. Civic, Corolla
    car_number = models.CharField(max_length=100, unique=True)  # Registration / Plate number
    year = models.PositiveIntegerField(null=True, blank=True)   # Manufacturing year

    # Specs
    color = models.CharField(max_length=50, null=True, blank=True)
    engine_capacity = models.CharField(max_length=50, null=True, blank=True)  # e.g. 1.6L, 2000cc
    fuel_type = models.CharField(
        max_length=150,
        # choices=[
        #     ("petrol", "Petrol"),
        #     ("diesel", "Diesel"),
        #     ("hybrid", "Hybrid"),
        #     ("electric", "Electric"),
        # ],
        default="petrol"
    )
    transmission = models.CharField(
        max_length=150,
        # choices=[
        #     ("manual", "Manual"),
        #     ("automatic", "Automatic"),
        # ],
        default="manual"
    )
    mileage = models.PositiveIntegerField(null=True, blank=True, help_text="Mileage in KM")

    # Financials
    total_amount = models.DecimalField(max_digits=80, decimal_places=2)
    sold_amount = models.DecimalField(max_digits=80, decimal_places=2, null=True, blank=True)
    admin_percentage = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Admin commission percentage"
    )

    # Management
    status = models.CharField(
        max_length=150,
        # choices=[
        #     ("available", "Available"),
        #     ("booked", "Booked"),
        #     ("sold", "Sold"),
        # ],
        default="available"
    )

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"{self.brand} {self.model_name} ({self.car_number})"

    @property
    def total_invested(self):
        """Sum of all investments on this car."""
        return sum(inv.amount for inv in self.investments.all())

    @property
    def remaining_amount(self):
        """Remaining amount not yet invested."""
        return self.total_amount - self.total_invested


class CarInvestment(TimeStampedModel):
    """
    Relationship between Car and Investor
    """
    car = models.ForeignKey(
        Car, related_name="investments", on_delete=models.CASCADE
    )
    investor = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="car_investments", on_delete=models.CASCADE
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        unique_together = ('car', 'investor')  # one investor per car

    def __str__(self):
        return f"{self.investor.email} invested {self.amount} in {self.car.model_name}"

    @property
    def percentage_share(self):
        """Investor's share % in the car"""
        return (self.amount / self.car.total_amount) * 100 if self.car.total_amount else 0

    @property
    def profit_share(self):
        """
        Profit share after deducting admin percentage.
        Example: If admin takes 10%, remaining 90% is split by investors.
        """
        remaining_percentage = Decimal(100) - self.car.admin_percentage
        return (Decimal(self.percentage_share) / Decimal(100)) * remaining_percentage

