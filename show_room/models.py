from django.db import models

# Create your models here.
from decimal import Decimal

from django.db import models
from django_extensions.db.models import TimeStampedModel
from django.conf import settings

class Car(TimeStampedModel):
    """
    Car details added by Admin or Show Room Owner
    Supports both investor-funded cars and consignment cars
    """
    CAR_TYPE_CHOICES = [
        ('investment', 'Investment Car'),
        ('consignment', 'Consignment Car'),
    ]
    
    # Basic Information
    brand = models.CharField(max_length=150)         # e.g. Toyota, Honda, BMW
    model_name = models.CharField(max_length=150)    # e.g. Civic, Corolla
    car_number = models.CharField(max_length=100, null=True)  # Registration / Plate number
    year = models.PositiveIntegerField(null=True, blank=True)   # Manufacturing year
    
    # Car type - determines business model
    car_type = models.CharField(
        max_length=20, 
        choices=CAR_TYPE_CHOICES, 
        default='investment',
        help_text="Investment: funded by investors, Consignment: owned by seller"
    )
    
    # For consignment cars
    asking_price = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="Asking price for consignment cars"
    )
    car_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='owned_consignment_cars',
        help_text="Owner of the consignment car (seller)"
    )
    
    # Show room owner who added this car
    show_room_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='managed_cars',
        help_text="Show room owner who manages this car"
    )

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
        total = sum(inv.amount for inv in self.investments.all())
        return round(total, 2)

    @property
    def total_expenses(self):
        """Sum of all expenses on this car."""
        total = sum(exp.amount for exp in self.expenses.all())
        return round(total, 2)

    @property
    def total_invested_with_expenses(self):
        """Sum of all investments and expenses on this car."""
        total = self.total_invested + self.total_expenses
        return round(total, 2)

    @property
    def remaining_amount(self):
        """Remaining amount not yet invested."""
        remaining = self.total_amount - self.total_invested
        return round(remaining, 2)

    @property
    def profit(self):
        """Calculate profit if car is sold (based on car type)"""
        if not self.sold_amount:
            return Decimal('0.00')
            
        if self.car_type == 'consignment':
            # For consignment cars: profit = sold_amount - asking_price - show_room_expenses
            show_room_expenses = self.get_show_room_expenses()
            profit = self.sold_amount - (self.asking_price or 0) - show_room_expenses
            return round(profit, 2)
        else:
            # For investment cars: original logic
            total_cost_basis = self.total_invested_with_expenses
            profit = self.sold_amount - total_cost_basis
            return round(profit, 2)

    def get_expense_statistics(self):
        """Get detailed expense statistics"""
        from collections import defaultdict
        
        stats = {
            'total_expenses': self.total_expenses,
            'expense_count': self.expenses.count(),
            'by_investor': defaultdict(lambda: {'total': Decimal('0.00'), 'count': 0, 'expenses': []})
        }
        
        for expense in self.expenses.all():
            investor_email = expense.investor.email
            stats['by_investor'][investor_email]['total'] += expense.amount
            stats['by_investor'][investor_email]['count'] += 1
            stats['by_investor'][investor_email]['expenses'].append({
                'id': expense.id,
                'amount': expense.amount,
                'description': expense.description,
                'date': expense.created
            })
        
        # Round totals
        for investor_data in stats['by_investor'].values():
            investor_data['total'] = round(investor_data['total'], 2)
        
        return stats

    def get_show_room_expenses(self):
        """Get total expenses added by show room owner for consignment cars"""
        if self.car_type == 'consignment':
            show_room_expenses = self.expenses.filter(investor=self.show_room_owner)
            return sum(exp.amount for exp in show_room_expenses)
        return Decimal('0.00')

    def calculate_profit_distribution(self):
        """
        Calculate profit distribution based on car type
        - Investment cars: distributed among admin and investors
        - Consignment cars: distributed between show room owner and car owner
        """
        if not self.sold_amount:
            return {
                "admin_share": Decimal('0.00'), 
                "investor_shares": {} if self.car_type == 'investment' else None,
                "show_room_owner_share": Decimal('0.00') if self.car_type == 'consignment' else None,
                "car_owner_share": Decimal('0.00') if self.car_type == 'consignment' else None,
                "total_profit": Decimal('0.00'),
                "remaining_profit": Decimal('0.00'),
                "car_type": self.car_type,
                "error": "Car has not been sold yet"
            }
        
        total_profit = round(self.profit, 2)
        
        if self.car_type == 'consignment':
            return self._calculate_consignment_profit_distribution(total_profit)
        else:
            return self._calculate_investment_profit_distribution(total_profit)

    def _calculate_investment_profit_distribution(self, total_profit):
        """Calculate profit distribution for investment cars"""
        total_cost_basis = self.total_invested_with_expenses
        
        if total_profit <= 0:
            return {
                "admin_share": Decimal('0.00'), 
                "investor_shares": {},
                "total_profit": total_profit,
                "remaining_profit": Decimal('0.00'),
                "total_cost_basis": round(total_cost_basis, 2),
                "car_type": "investment",
                "error": f"No profit to distribute. Loss: {abs(total_profit)}"
            }

        # Step 1: Calculate admin share from total profit
        admin_share = round((self.admin_percentage / Decimal('100')) * total_profit, 2)
        remaining_profit = round(total_profit - admin_share, 2)

        # Step 2: Calculate investor shares based on their contribution percentage to total cost basis
        investor_shares = {}
        for investment in self.investments.all():
            investor_contribution = investment.total_contribution
            if total_cost_basis > 0:
                contribution_percentage = investor_contribution / total_cost_basis
                investor_profit = round(remaining_profit * contribution_percentage, 2)
            else:
                contribution_percentage = 0
                investor_profit = Decimal('0.00')
                
            investor_shares[investment.investor.email] = {
                'contribution': round(investor_contribution, 2),
                'percentage': round(contribution_percentage * 100, 2),
                'profit': investor_profit,
                'total_return': round(investor_contribution + investor_profit, 2)
            }

        return {
            "admin_share": admin_share,
            "investor_shares": investor_shares,
            "total_profit": total_profit,
            "remaining_profit": remaining_profit,
            "total_cost_basis": round(total_cost_basis, 2),
            "sold_amount": round(self.sold_amount, 2),
            "car_type": "investment"
        }

    def _calculate_consignment_profit_distribution(self, total_profit):
        """Calculate profit distribution for consignment cars"""
        # New logic: Show room gets percentage of sold amount + expenses, car owner gets the rest
        show_room_percentage_amount = round((self.admin_percentage / Decimal('100')) * self.sold_amount, 2)
        show_room_expenses = round(self.get_show_room_expenses(), 2)
        show_room_total_earnings = show_room_percentage_amount + show_room_expenses
        car_owner_earnings = round(self.sold_amount - show_room_percentage_amount - show_room_expenses, 2)
        
        return {
            "show_room_owner_share": show_room_percentage_amount,
            "show_room_expenses_recovered": show_room_expenses,
            "show_room_total_earnings": show_room_total_earnings,
            "car_owner_earnings": car_owner_earnings,
            "show_room_percentage_amount": show_room_percentage_amount,
            "asking_price": round(self.asking_price or 0, 2),
            "show_room_expenses": show_room_expenses,
            "sold_amount": round(self.sold_amount, 2),
            "admin_percentage": float(self.admin_percentage),
            "car_type": "consignment",
            "calculation_method": "show_room_gets_percentage_plus_expenses"
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
        if total_invested > 0:
            share = (self.total_contribution / total_invested) * 100
            return round(share, 2)
        return Decimal('0.00')

    @property
    def profit_amount(self):
        """Calculate actual profit amount this investor will receive"""
        if not self.car.sold_amount or self.car.profit <= 0:
            return Decimal('0.00')
        
        # Admin takes their percentage from total profit first
        admin_share = (self.car.admin_percentage / Decimal('100')) * self.car.profit
        remaining_profit = self.car.profit - admin_share
        
        # Investor gets their share of remaining profit based on contribution to total cost basis
        total_cost_basis = self.car.total_invested_with_expenses
        if total_cost_basis > 0:
            contribution_percentage = self.total_contribution / total_cost_basis
            profit = remaining_profit * contribution_percentage
            return round(profit, 2)
        return Decimal('0.00')

    @property
    def total_return(self):
        """Total amount investor will get back (original investment + expenses + profit)"""
        total = self.total_contribution + self.profit_amount
        return round(total, 2)


class CarExpense(TimeStampedModel):
    """
    Car expenses added by investors or show room owners
    For investment cars: added by investors
    For consignment cars: added by show room owners
    """
    car = models.ForeignKey(
        Car, related_name="expenses", on_delete=models.CASCADE
    )
    investor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name="car_expenses", 
        on_delete=models.CASCADE,
        help_text="For investment cars: investor who paid. For consignment cars: show room owner"
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.TextField(help_text="Expense details like maintenance, repairs, etc.")

    class Meta:
        ordering = ['-created']

    def __str__(self):
        expense_type = "Show Room Expense" if self.car.car_type == 'consignment' and self.investor == self.car.show_room_owner else "Investor Expense"
        return f"{expense_type}: {self.investor.email} - {self.amount} for {self.car.model_name}"
    
    @property
    def is_show_room_expense(self):
        """Check if this is a show room owner expense for a consignment car"""
        return (self.car.car_type == 'consignment' and 
                self.investor == self.car.show_room_owner)


class CarExpenseImage(TimeStampedModel):
    """
    Images for car expenses - multiple images per expense
    """
    expense = models.ForeignKey(
        CarExpense, related_name="images", on_delete=models.CASCADE
    )
    image = models.ImageField(
        upload_to='expense_images/',
        help_text="Upload expense receipt or related image"
    )
    description = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="Optional description for the image"
    )

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f"Image for expense {self.expense.id} - {self.expense.car.model_name}"

