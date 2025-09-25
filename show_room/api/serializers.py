from rest_framework import serializers
from show_room.models import Car, CarInvestment


class CarInvestmentCreateSerializer(serializers.ModelSerializer):
    """Used for creating investments inside Car POST request"""
    class Meta:
        model = CarInvestment
        fields = ["investor", "amount"]



class CarSerializer(serializers.ModelSerializer):
    # For creating
    investments = CarInvestmentCreateSerializer(many=True, write_only=True, required=False)

    # For response
    all_investments = serializers.SerializerMethodField(read_only=True)
    total_invested = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    remaining_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = Car
        fields = [
            "id",
            "brand", "model_name", "car_number", "year", "color",
            "engine_capacity", "fuel_type", "transmission", "mileage", "status",
            "total_amount", "admin_percentage",
            "total_invested", "remaining_amount",
            "investments", "all_investments",
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
                "amount": str(inv.amount),
                "percentage_share": str(inv.percentage_share),
                "profit_share": str(inv.profit_share),
            }
            for inv in obj.investments.all()
        ]

