from rest_framework import serializers
from show_room.models import Car, CarInvestment, CarExpense


class CarInvestmentCreateSerializer(serializers.ModelSerializer):
    """Used for creating investments inside Car POST request"""
    class Meta:
        model = CarInvestment
        fields = ["investor", "amount"]



class CarExpenseSerializer(serializers.ModelSerializer):
    investor_email = serializers.CharField(source='investor.email', read_only=True)
    
    class Meta:
        model = CarExpense
        fields = ["id", "car", "investor", "investor_email", "amount", "description", "created"]
        read_only_fields = ["created"]

    def create(self, validated_data):
        # Set investor from request user if not provided
        if 'investor' not in validated_data:
            validated_data['investor'] = self.context['request'].user
        return super().create(validated_data)


class CarListSerializer(serializers.ModelSerializer):
    """Serializer for car list view (home page) - minimal details"""
    total_invested = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    remaining_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    investor_count = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Car
        fields = [
            "id",
            "brand", "model_name", "car_number", "year", "color",
            "fuel_type", "transmission", "status",
            "total_amount", "total_invested", "remaining_amount",
            "investor_count"
        ]
    
    def get_investor_count(self, obj):
        """Get number of investors for this car"""
        return obj.investments.count()


class CarDetailSerializer(serializers.ModelSerializer):
    """Serializer for car detail view - complete details"""
    # For creating
    investments = CarInvestmentCreateSerializer(many=True, write_only=True, required=False)

    # For response
    all_investments = serializers.SerializerMethodField(read_only=True)
    all_expenses = serializers.SerializerMethodField(read_only=True)
    expense_summary = serializers.SerializerMethodField(read_only=True)
    expense_analytics = serializers.SerializerMethodField(read_only=True)
    total_invested = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    total_expenses = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    total_invested_with_expenses = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    remaining_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    profit = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    profit_distribution = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Car
        fields = [
            "id",
            "brand", "model_name", "car_number", "year", "color",
            "engine_capacity", "fuel_type", "transmission", "mileage", "status",
            "total_amount", "sold_amount", "admin_percentage",
            "total_invested", "total_expenses", "total_invested_with_expenses", 
            "remaining_amount", "profit",
            "investments", "all_investments", "all_expenses", "expense_summary", "expense_analytics", "profit_distribution",
        ]

    def create(self, validated_data):
        investments_data = validated_data.pop("investments", [])
        car = Car.objects.create(**validated_data)

        total_investments = sum(inv["amount"] for inv in investments_data)

        # ✅ Validate total amount first
        if total_investments != car.total_amount:
            raise serializers.ValidationError(
                f"Total investments ({total_investments}) must equal car total amount ({car.total_amount})."
            )

        # ✅ Now create investments
        for inv in investments_data:
            CarInvestment.objects.create(car=car, **inv)

        return car

    def get_all_investments(self, obj):
        return [
            {
                "investor": inv.investor.id,
                "investor_email": inv.investor.email,
                "initial_amount": f"{inv.amount:.2f}",
                "total_contribution": f"{inv.total_contribution:.2f}",
                "investment_share": f"{inv.investment_share:.2f}",
                "profit_amount": f"{inv.profit_amount:.2f}",
                "total_return": f"{inv.total_return:.2f}",
            }
            for inv in obj.investments.all()
        ]

    def get_all_expenses(self, obj):
        return [
            {
                "id": exp.id,
                "investor": exp.investor.id,
                "investor_email": exp.investor.email,
                "investor_name": f"{exp.investor.first_name} {exp.investor.last_name}".strip() or exp.investor.email,
                "amount": f"{exp.amount:.2f}",
                "description": exp.description,
                "created": exp.created,
                "created_date": exp.created.strftime("%Y-%m-%d"),
                "created_time": exp.created.strftime("%H:%M:%S"),
            }
            for exp in obj.expenses.all()
        ]

    def get_expense_summary(self, obj):
        """Get expense summary grouped by investor"""
        from collections import defaultdict
        
        expense_by_investor = defaultdict(lambda: {
            'investor_id': None,
            'investor_email': '',
            'investor_name': '',
            'total_expenses': 0,
            'expense_count': 0,
            'expenses': []
        })
        
        for expense in obj.expenses.all():
            investor_email = expense.investor.email
            investor_name = f"{expense.investor.first_name} {expense.investor.last_name}".strip() or expense.investor.email
            
            expense_by_investor[investor_email]['investor_id'] = expense.investor.id
            expense_by_investor[investor_email]['investor_email'] = investor_email
            expense_by_investor[investor_email]['investor_name'] = investor_name
            expense_by_investor[investor_email]['total_expenses'] += float(expense.amount)
            expense_by_investor[investor_email]['expense_count'] += 1
            expense_by_investor[investor_email]['expenses'].append({
                'id': expense.id,
                'amount': f"{expense.amount:.2f}",
                'description': expense.description,
                'date': expense.created.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        # Format the final result
        result = []
        for investor_data in expense_by_investor.values():
            investor_data['total_expenses'] = f"{investor_data['total_expenses']:.2f}"
            result.append(investor_data)
        
        return result

    def get_expense_analytics(self, obj):
        """Get expense analytics and trends"""
        expenses = obj.expenses.all().order_by('-created')
        
        if not expenses:
            return {
                'total_expenses': "0.00",
                'expense_count': 0,
                'average_expense': "0.00",
                'latest_expense': None,
                'highest_expense': None,
                'expense_percentage_of_investment': "0.00"
            }
        
        total_expenses = sum(exp.amount for exp in expenses)
        expense_count = len(expenses)
        average_expense = total_expenses / expense_count if expense_count > 0 else 0
        latest_expense = expenses[0]
        highest_expense = max(expenses, key=lambda x: x.amount)
        
        # Calculate expense as percentage of total investment
        expense_percentage = (total_expenses / obj.total_invested * 100) if obj.total_invested > 0 else 0
        
        return {
            'total_expenses': f"{total_expenses:.2f}",
            'expense_count': expense_count,
            'average_expense': f"{average_expense:.2f}",
            'latest_expense': {
                'id': latest_expense.id,
                'amount': f"{latest_expense.amount:.2f}",
                'description': latest_expense.description,
                'investor_email': latest_expense.investor.email,
                'date': latest_expense.created.strftime("%Y-%m-%d %H:%M:%S")
            },
            'highest_expense': {
                'id': highest_expense.id,
                'amount': f"{highest_expense.amount:.2f}",
                'description': highest_expense.description,
                'investor_email': highest_expense.investor.email,
                'date': highest_expense.created.strftime("%Y-%m-%d %H:%M:%S")
            },
            'expense_percentage_of_investment': f"{expense_percentage:.2f}"
        }

    def get_profit_distribution(self, obj):
        """Get profit distribution if car is sold"""
        if obj.sold_amount:
            return obj.calculate_profit_distribution()
        return None


# Backward compatibility - keep the original name
CarSerializer = CarDetailSerializer