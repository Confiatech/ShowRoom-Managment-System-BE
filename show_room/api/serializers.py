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


class CarSerializer(serializers.ModelSerializer):
    # For creating
    investments = CarInvestmentCreateSerializer(many=True, write_only=True, required=False)

    # For response
    all_investments = serializers.SerializerMethodField(read_only=True)
    all_expenses = serializers.SerializerMethodField(read_only=True)
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
            "investments", "all_investments", "all_expenses", "profit_distribution",
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
                "initial_amount": str(inv.amount),
                "total_contribution": str(inv.total_contribution),
                "investment_share": str(inv.investment_share),
                "profit_amount": str(inv.profit_amount),
                "total_return": str(inv.total_return),
            }
            for inv in obj.investments.all()
        ]

    def get_all_expenses(self, obj):
        return [
            {
                "id": exp.id,
                "investor": exp.investor.id,
                "investor_email": exp.investor.email,
                "amount": str(exp.amount),
                "description": exp.description,
                "created": exp.created,
            }
            for exp in obj.expenses.all()
        ]

    def get_profit_distribution(self, obj):
        """Get profit distribution if car is sold"""
        if obj.sold_amount:
            return obj.calculate_profit_distribution()
        return None

