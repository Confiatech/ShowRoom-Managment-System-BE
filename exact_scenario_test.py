#!/usr/bin/env python3
"""
Test script for the exact scenario described in the requirements:
- Car total: 9,00,000
- 3 investors: 3,00,000 each
- Investor A adds 1,00,000 expense
- Car sold at 11,00,000
- Admin gets 30% of profit
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from show_room.models import Car, CarInvestment, CarExpense

User = get_user_model()

def run_exact_scenario():
    """Run the exact scenario from requirements"""
    
    print("🎯 Exact Scenario Test")
    print("=" * 50)
    
    # Clean up
    Car.objects.filter(car_number="EXACT-TEST").delete()
    
    # Create users
    admin, _ = User.objects.get_or_create(
        email="admin@test.com",
        defaults={"first_name": "Admin", "role": "admin"}
    )
    
    investor_a, _ = User.objects.get_or_create(
        email="investor_a@test.com",
        defaults={"first_name": "Investor A", "role": "investor"}
    )
    
    investor_b, _ = User.objects.get_or_create(
        email="investor_b@test.com",
        defaults={"first_name": "Investor B", "role": "investor"}
    )
    
    investor_c, _ = User.objects.get_or_create(
        email="investor_c@test.com",
        defaults={"first_name": "Investor C", "role": "investor"}
    )
    
    # Step 1: Admin adds car with total amount 9,00,000
    car = Car.objects.create(
        car_number="EXACT-TEST",
        brand="Toyota",
        model_name="Test Car",
        total_amount=Decimal('900000'),  # 9,00,000
        admin_percentage=Decimal('30'),  # 30%
        status="available"
    )
    
    print(f"✅ Admin adds car: ₹{car.total_amount:,}")
    
    # Step 2: Create investments
    CarInvestment.objects.create(car=car, investor=investor_a, amount=Decimal('300000'))  # 3,00,000
    CarInvestment.objects.create(car=car, investor=investor_b, amount=Decimal('300000'))  # 3,00,000
    CarInvestment.objects.create(car=car, investor=investor_c, amount=Decimal('300000'))  # 3,00,000
    
    print("✅ Initial investments:")
    print(f"   Investor A: ₹3,00,000")
    print(f"   Investor B: ₹3,00,000")
    print(f"   Investor C: ₹3,00,000")
    
    # Step 3: Investor A adds expense
    CarExpense.objects.create(
        car=car,
        investor=investor_a,
        amount=Decimal('100000'),  # 1,00,000
        description="Maintenance expense"
    )
    
    print("✅ Investor A adds expense: ₹1,00,000")
    
    # Show current state
    print(f"\n📊 Current State:")
    print(f"   Total car cost: ₹{car.total_amount:,}")
    print(f"   Total expenses: ₹{car.total_expenses:,}")
    print(f"   Total invested + expenses: ₹{car.total_invested_with_expenses:,}")
    
    print(f"\n👥 Contributions:")
    for inv in car.investments.all():
        print(f"   {inv.investor.first_name}: ₹{inv.total_contribution:,} ({inv.investment_share:.1f}%)")
    
    # Step 4: Car is sold
    car.sold_amount = Decimal('1100000')  # 11,00,000
    car.status = "sold"
    car.save()
    
    print(f"\n🏷️ Car sold for: ₹{car.sold_amount:,}")
    print(f"   Total profit: ₹{car.profit:,}")
    
    # Step 5: Calculate profit distribution
    distribution = car.calculate_profit_distribution()
    
    print(f"\n💰 Profit Distribution:")
    print(f"   Admin share (30%): ₹{distribution['admin_share']:,}")
    print(f"   Remaining for investors: ₹{distribution['remaining_profit']:,}")
    
    print(f"\n🎯 Final Distribution:")
    print(f"   Admin: ₹{distribution['admin_share']:,}")
    
    for email, data in distribution['investor_shares'].items():
        investor_name = email.split('@')[0].replace('_', ' ').title()
        print(f"   {investor_name}: ₹{data['profit']:,}")
    
    # Verify against expected results
    print(f"\n✅ Verification:")
    expected_admin = 60000  # 30% of 2,00,000
    expected_a = 56000      # 40% of 1,40,000
    expected_b = 42000      # 30% of 1,40,000
    expected_c = 42000      # 30% of 1,40,000
    
    actual_admin = float(distribution['admin_share'])
    actual_a = float(distribution['investor_shares']['investor_a@test.com']['profit'])
    actual_b = float(distribution['investor_shares']['investor_b@test.com']['profit'])
    actual_c = float(distribution['investor_shares']['investor_c@test.com']['profit'])
    
    print(f"   Expected Admin: ₹{expected_admin:,} | Actual: ₹{actual_admin:,.0f} | ✅" if abs(actual_admin - expected_admin) < 1 else f"   Expected Admin: ₹{expected_admin:,} | Actual: ₹{actual_admin:,.0f} | ❌")
    print(f"   Expected A: ₹{expected_a:,} | Actual: ₹{actual_a:,.0f} | ✅" if abs(actual_a - expected_a) < 1 else f"   Expected A: ₹{expected_a:,} | Actual: ₹{actual_a:,.0f} | ❌")
    print(f"   Expected B: ₹{expected_b:,} | Actual: ₹{actual_b:,.0f} | ✅" if abs(actual_b - expected_b) < 1 else f"   Expected B: ₹{expected_b:,} | Actual: ₹{actual_b:,.0f} | ❌")
    print(f"   Expected C: ₹{expected_c:,} | Actual: ₹{actual_c:,.0f} | ✅" if abs(actual_c - expected_c) < 1 else f"   Expected C: ₹{expected_c:,} | Actual: ₹{actual_c:,.0f} | ❌")

if __name__ == "__main__":
    run_exact_scenario()