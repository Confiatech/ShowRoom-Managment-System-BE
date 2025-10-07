from rest_framework import serializers
from show_room.models import Car, CarInvestment, CarExpense, CarExpenseImage


class CarInvestmentCreateSerializer(serializers.ModelSerializer):
    """Used for creating investments inside Car POST request"""
    class Meta:
        model = CarInvestment
        fields = ["investor", "amount"]



class CarExpenseImageSerializer(serializers.ModelSerializer):
    """Serializer for expense images"""
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = CarExpenseImage
        fields = ["id", "image", "description", "created"]
        read_only_fields = ["created"]
    
    def get_image(self, obj):
        """Return complete URL for image"""
        if obj.image and 'request' in self.context:
            return self.context['request'].build_absolute_uri(obj.image.url)
        elif obj.image:
            return obj.image.url
        return None


class CarExpenseSerializer(serializers.ModelSerializer):
    investor_email = serializers.CharField(source='investor.email', read_only=True)
    images = CarExpenseImageSerializer(many=True, read_only=True)
    image_count = serializers.SerializerMethodField(read_only=True)
    image_files = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        help_text="List of image files to upload with the expense"
    )
    
    class Meta:
        model = CarExpense
        fields = ["id", "car", "investor", "investor_email", "amount", "description", "images", "image_count", "image_files", "created"]
        read_only_fields = ["created"]

    def get_image_count(self, obj):
        """Get number of images for this expense"""
        try:
            return obj.images.count()
        except Exception:
            return 0

    def create(self, validated_data):
        # Extract image files from validated data
        image_files = validated_data.pop('image_files', [])
        
        # Set investor from request user if not provided
        if 'investor' not in validated_data:
            validated_data['investor'] = self.context['request'].user
        
        # Ensure investor exists in CarInvestment for this car
        if 'investor' in validated_data and 'car' in validated_data:
            car = validated_data['car']
            investor = validated_data['investor']
            
            # Check if investor already has investment in this car
            investment_exists = CarInvestment.objects.filter(
                car=car, 
                investor=investor
            ).exists()
            
            # If no investment exists, create one with 0 amount
            if not investment_exists:
                CarInvestment.objects.create(
                    car=car,
                    investor=investor,
                    amount=0.0
                )
        
        # Create the expense
        expense = super().create(validated_data)
        
        # Create images for the expense
        for image_file in image_files:
            CarExpenseImage.objects.create(
                expense=expense,
                image=image_file,
                description=""  # Default empty description
            )
        
        return expense


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
        user = self.context['request'].user if 'request' in self.context else None
        
        if user and user.is_superuser:
            # Superusers see total investor count
            return obj.investments.count()
        else:
            # Regular users just see if they are invested (1 or 0)
            return 1 if obj.investments.filter(investor=user).exists() else 0


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
        
        # Set show room owner if user is a show room owner
        user = self.context['request'].user
        if user.role == 'show_room_owner':
            validated_data['show_room_owner'] = user
        
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

    def update(self, instance, validated_data):
        investments_data = validated_data.pop("investments", None)
        
        # Update car fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Handle investments if provided
        if investments_data is not None:
            # Get current investors
            current_investors = set(instance.investments.values_list('investor_id', flat=True))
            new_investors = set(inv['investor'].id if hasattr(inv['investor'], 'id') else inv['investor'] for inv in investments_data)
            
            # Calculate total investments
            total_investments = sum(inv["amount"] for inv in investments_data)
            
            # Validate total amount
            if total_investments > instance.total_amount:
                raise serializers.ValidationError(
                    f"Total investments ({total_investments}) cannot exceed car total amount ({instance.total_amount})."
                )
            
            # Remove investors that are no longer in the list
            investors_to_remove = current_investors - new_investors
            if investors_to_remove:
                instance.investments.filter(investor_id__in=investors_to_remove).delete()
            
            # Update or create investments
            for inv_data in investments_data:
                investor_id = inv_data['investor'].id if hasattr(inv_data['investor'], 'id') else inv_data['investor']
                
                # Use get_or_create to handle the unique constraint properly
                investment, created = CarInvestment.objects.get_or_create(
                    car=instance,
                    investor_id=investor_id,
                    defaults={'amount': inv_data['amount']}
                )
                
                # If it already existed, update the amount
                if not created:
                    investment.amount = inv_data['amount']
                    investment.save()
        
        return instance

    def get_all_investments(self, obj):
        user = self.context['request'].user if 'request' in self.context else None
        
        if user and (user.is_superuser or user.role == 'admin'):
            # Superusers and admins see all investments
            investments = obj.investments.all()
        elif user and user.role == 'show_room_owner' and obj.show_room_owner == user:
            # Show room owners see investments for their cars
            investments = obj.investments.all()
        elif user:
            # Regular users only see their own investment
            investments = obj.investments.filter(investor=user)
        else:
            investments = []
        
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
            for inv in investments
        ]

    def get_all_expenses(self, obj):
        user = self.context['request'].user if 'request' in self.context else None
        
        if user and (user.is_superuser or user.role == 'admin'):
            # Superusers and admins see all expenses
            expenses = obj.expenses.all()
        elif user and user.role == 'show_room_owner' and obj.show_room_owner == user:
            # Show room owners see expenses for their cars
            expenses = obj.expenses.all()
        elif user:
            # Regular users see all expenses for cars they invested in
            # (since they can only access cars they invested in anyway)
            expenses = obj.expenses.all()
        else:
            expenses = []
        
        return [
            {
                "id": exp.id,
                "investor": exp.investor.id,
                "investor_email": exp.investor.email,
                "investor_name": f"{exp.investor.first_name} {exp.investor.last_name}".strip() or exp.investor.email,
                "amount": f"{exp.amount:.2f}",
                "description": exp.description,
                "images": [
                    {
                        "id": img.id,
                        "image": self.context['request'].build_absolute_uri(img.image.url) if img.image and 'request' in self.context else img.image.url if img.image else None,
                        "description": img.description,
                        "created": img.created
                    }
                    for img in exp.images.all()
                ],
                "image_count": exp.images.count(),
                "created": exp.created,
                "created_date": exp.created.strftime("%Y-%m-%d"),
                "created_time": exp.created.strftime("%H:%M:%S"),
            }
            for exp in expenses
        ]

    def get_expense_summary(self, obj):
        """Get expense summary grouped by investor"""
        from collections import defaultdict
        
        user = self.context['request'].user if 'request' in self.context else None
        
        if user and (user.is_superuser or user.role == 'admin'):
            # Superusers and admins see all expenses
            expenses = obj.expenses.all()
        elif user and user.role == 'show_room_owner' and obj.show_room_owner == user:
            # Show room owners see expenses for their cars
            expenses = obj.expenses.all()
        elif user:
            # Regular users see all expenses for cars they invested in
            expenses = obj.expenses.all()
        else:
            expenses = []
        
        expense_by_investor = defaultdict(lambda: {
            'investor_id': None,
            'investor_email': '',
            'investor_name': '',
            'total_expenses': 0,
            'expense_count': 0,
            'expenses': []
        })
        
        for expense in expenses:
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
                'images': [
                    {
                        'id': img.id,
                        'image': self.context['request'].build_absolute_uri(img.image.url) if img.image and 'request' in self.context else img.image.url if img.image else None,
                        'description': img.description
                    }
                    for img in expense.images.all()
                ],
                'image_count': expense.images.count(),
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
        user = self.context['request'].user if 'request' in self.context else None
        
        if user and (user.is_superuser or user.role == 'admin'):
            # Superusers and admins see all expenses
            expenses = obj.expenses.all().order_by('-created')
        elif user and user.role == 'show_room_owner' and obj.show_room_owner == user:
            # Show room owners see expenses for their cars
            expenses = obj.expenses.all().order_by('-created')
        elif user:
            # Regular users see all expenses for cars they invested in
            expenses = obj.expenses.all().order_by('-created')
        else:
            expenses = []
        
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
                'image_count': latest_expense.images.count(),
                'date': latest_expense.created.strftime("%Y-%m-%d %H:%M:%S")
            },
            'highest_expense': {
                'id': highest_expense.id,
                'amount': f"{highest_expense.amount:.2f}",
                'description': highest_expense.description,
                'investor_email': highest_expense.investor.email,
                'image_count': highest_expense.images.count(),
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