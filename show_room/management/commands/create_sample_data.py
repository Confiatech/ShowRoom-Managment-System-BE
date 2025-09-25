from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from show_room.models import Car, CarInvestment, CarExpense
from decimal import Decimal
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample data for testing the admin panel'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Create sample users
        users_data = [
            {'email': 'investor1@example.com', 'first_name': 'John', 'last_name': 'Doe', 'role': 'investor'},
            {'email': 'investor2@example.com', 'first_name': 'Jane', 'last_name': 'Smith', 'role': 'investor'},
            {'email': 'investor3@example.com', 'first_name': 'Mike', 'last_name': 'Johnson', 'role': 'investor'},
        ]
        
        users = []
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults=user_data
            )
            if created:
                user.set_password('password123')
                user.save()
                self.stdout.write(f'Created user: {user.email}')
            users.append(user)
        
        # Create sample cars
        cars_data = [
            {
                'brand': 'Toyota', 'model_name': 'Camry', 'car_number': 'ABC-123',
                'year': 2020, 'color': 'White', 'fuel_type': 'petrol',
                'transmission': 'automatic', 'total_amount': Decimal('25000'),
                'admin_percentage': Decimal('10'), 'status': 'available'
            },
            {
                'brand': 'Honda', 'model_name': 'Civic', 'car_number': 'XYZ-456',
                'year': 2019, 'color': 'Black', 'fuel_type': 'petrol',
                'transmission': 'manual', 'total_amount': Decimal('22000'),
                'admin_percentage': Decimal('12'), 'status': 'booked'
            },
            {
                'brand': 'BMW', 'model_name': '320i', 'car_number': 'BMW-789',
                'year': 2021, 'color': 'Blue', 'fuel_type': 'petrol',
                'transmission': 'automatic', 'total_amount': Decimal('35000'),
                'sold_amount': Decimal('38000'), 'admin_percentage': Decimal('15'),
                'status': 'sold'
            },
        ]
        
        cars = []
        for car_data in cars_data:
            car, created = Car.objects.get_or_create(
                car_number=car_data['car_number'],
                defaults=car_data
            )
            if created:
                self.stdout.write(f'Created car: {car}')
            cars.append(car)
        
        # Create sample investments
        investments_data = [
            {'car': cars[0], 'investor': users[0], 'amount': Decimal('15000')},
            {'car': cars[0], 'investor': users[1], 'amount': Decimal('8000')},
            {'car': cars[1], 'investor': users[1], 'amount': Decimal('12000')},
            {'car': cars[1], 'investor': users[2], 'amount': Decimal('10000')},
            {'car': cars[2], 'investor': users[0], 'amount': Decimal('20000')},
            {'car': cars[2], 'investor': users[2], 'amount': Decimal('15000')},
        ]
        
        for inv_data in investments_data:
            investment, created = CarInvestment.objects.get_or_create(
                car=inv_data['car'],
                investor=inv_data['investor'],
                defaults={'amount': inv_data['amount']}
            )
            if created:
                self.stdout.write(f'Created investment: {investment}')
        
        # Create sample expenses
        expenses_data = [
            {'car': cars[0], 'investor': users[0], 'amount': Decimal('500'), 'description': 'Oil change and maintenance'},
            {'car': cars[1], 'investor': users[1], 'amount': Decimal('800'), 'description': 'Tire replacement'},
            {'car': cars[2], 'investor': users[0], 'amount': Decimal('1200'), 'description': 'Engine repair'},
            {'car': cars[2], 'investor': users[2], 'amount': Decimal('300'), 'description': 'Car wash and detailing'},
        ]
        
        for exp_data in expenses_data:
            expense, created = CarExpense.objects.get_or_create(
                car=exp_data['car'],
                investor=exp_data['investor'],
                description=exp_data['description'],
                defaults={'amount': exp_data['amount']}
            )
            if created:
                self.stdout.write(f'Created expense: {expense}')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created sample data!')
        )