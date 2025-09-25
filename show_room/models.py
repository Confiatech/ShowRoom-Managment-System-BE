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
    def total_expenses(self):
        """Sum of all expenses on this car."""
        return sum(exp.amount for exp in self.expenses.all())

    @property
    def total_invested_with_expenses(self):
        """Sum of all investments and expenses on this car."""
        return self.total_invested + self.total_expenses

    @property
    def remaining_amount(self):
        """Remaining amount not yet invested."""
        return self.total_amount - self.total_invested

    @property
    def profit(self):
        """Calculate profit if car is sold (based on original car amount, not including expenses)"""
        if self.sold_amount:
            return self.sold_amount - self.total_amount
        return Decimal('0')

    def calculate_profit_distribution(self):
        """
        Calculate profit distribution among admin and investors
        Returns dict with admin_share and investor_shares
        """
        if not self.sold_amount:
            return {
                "admin_share": Decimal('0'), 
                "investor_shares": {},
                "total_profit": Decimal('0'),
                "remaining_profit": Decimal('0'),
                "error": "Car has not been sold yet"
            }
        
        if self.profit <= 0:
            return {
                "admin_share": Decimal('0'), 
                "investor_shares": {},
                "total_profit": self.profit,
                "remaining_profit": Decimal('0'),
                "error": f"No profit to distribute. Loss: {abs(self.profit)}"
            }

        # Step 1: Calculate admin share
        admin_share = (self.admin_percentage / Decimal('100')) * self.profit
        remaining_profit = self.profit - admin_share

        # Step 2: Calculate investor shares based on contribution percentage
        investor_shares = {}
        total_contribution = self.total_invested_with_expenses

        for investment in self.investments.all():
            investor_contribution = investment.total_contribution
            contribution_percentage = investor_contribution / total_contribution if total_contribution > 0 else 0
            investor_profit = remaining_profit * contribution_percentage
            investor_shares[investment.investor.email] = {
                'contribution': investor_contribution,
                'percentage': contribution_percentage * 100,
                'profit': investor_profit
            }

        return {
            "admin_share": admin_share,
            "investor_shares": investor_shares,
            "total_profit": self.profit,
            "remaining_profit": remaining_profit
        }


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
    def total_contribution(self):
        """Total contribution including initial investment and expenses"""
        expenses = CarExpense.objects.filter(car=self.car, investor=self.investor)
        total_expenses = sum(expense.amount for expense in expenses)
        return self.amount + total_expenses

    @property
    def investment_share(self):
        """Investor's share % in the car based on total contribution"""
        total_invested = self.car.total_invested_with_expenses
        return (self.total_contribution / total_invested) * 100 if total_invested else 0

    @property
    def profit_amount(self):
        """Calculate actual profit amount this investor will receive"""
        if not self.car.sold_amount or self.car.profit <= 0:
            return Decimal('0')
        
        # Admin takes their percentage first
        admin_share = (self.car.admin_percentage / Decimal('100')) * self.car.profit
        remaining_profit = self.car.profit - admin_share
        
        # Investor gets their share of remaining profit
        total_contribution = self.car.total_invested_with_expenses
        contribution_percentage = self.total_contribution / total_contribution if total_contribution > 0 else 0
        return remaining_profit * contribution_percentage

    @property
    def total_return(self):
        """Total amount investor will get back (original investment + expenses + profit)"""
        return self.total_contribution + self.profit_amount


class CarExpense(TimeStampedModel):
    """
    Car expenses added by investors
    """
    car = models.ForeignKey(
        Car, related_name="expenses", on_delete=models.CASCADE
    )
    investor = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="car_expenses", on_delete=models.CASCADE
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.TextField(help_text="Expense details like maintenance, repairs, etc.")

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f"{self.investor.email} - {self.amount} expense for {self.car.model_name}"

