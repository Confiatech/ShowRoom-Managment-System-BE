from django.db import models

# Create your models here.

from django.db import models
from django_extensions.db.models import TimeStampedModel


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
    total_amount = models.DecimalField(max_digits=30, decimal_places=2)
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


