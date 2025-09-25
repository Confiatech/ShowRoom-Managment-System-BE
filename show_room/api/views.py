from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from show_room.models import Car, CarExpense
from .serializers import CarListSerializer, CarDetailSerializer, CarExpenseSerializer
from auths.api.permissions import CarPermission, ExpensePermission, IsSuperAdmin

User = get_user_model()


class CarViewSet(viewsets.ModelViewSet):
    permission_classes = [CarPermission]
    
    def get_serializer_class(self):
        """Return different serializers for list and detail views"""
        if self.action == 'list':
            return CarListSerializer
        return CarDetailSerializer

    def get_queryset(self):
        """Filter queryset based on user role and optimize based on action"""
        user = self.request.user
        
        if user.is_superuser:
            # Superusers see all cars
            base_queryset = Car.objects.all()
        else:
            # Regular users only see cars they have invested in
            base_queryset = Car.objects.filter(
                investments__investor=user
            ).distinct()
        
        if self.action == 'list':
            # For list view, we don't need expenses data
            return base_queryset.prefetch_related("investments__investor")
        return base_queryset.prefetch_related("investments__investor", "expenses__investor")

    @action(detail=True, methods=['post'], permission_classes=[ExpensePermission])
    def add_expense(self, request, pk=None):
        """Add expense to a specific car (superuser only)"""
        if not request.user.is_superuser:
            return Response(
                {"error": "Only superusers can add expenses"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        car = self.get_object()
        serializer = CarExpenseSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            serializer.save(car=car)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def profit_calculation(self, request, pk=None):
        """Get detailed profit calculation for a car"""
        car = self.get_object()
        
        if not car.sold_amount:
            return Response(
                {"error": "Car has not been sold yet"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        distribution = car.calculate_profit_distribution()
        return Response(distribution)

    @action(detail=True, methods=['get'])
    def investors(self, request, pk=None):
        """Get all investor details for a specific car"""
        car = self.get_object()
        user = request.user
        
        # Get investments for this car
        investments = car.investments.all().select_related('investor')
        
        if not investments.exists():
            return Response(
                {"message": "No investors found for this car"}, 
                status=status.HTTP_200_OK
            )
        
        # Prepare investor details
        investors_data = []
        
        for investment in investments:
            investor = investment.investor
            
            # Basic investor information
            investor_info = {
                "investor_id": investor.id,
                "email": investor.email,
                "first_name": investor.first_name or "",
                "last_name": investor.last_name or "",
                "full_name": f"{investor.first_name or ''} {investor.last_name or ''}".strip() or investor.email,

            }

            investors_data.append(investor_info)

        response_data = {
            "investors": investors_data
        }
        
        return Response(response_data, status=status.HTTP_200_OK)


class CarExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = CarExpenseSerializer
    permission_classes = [ExpensePermission]

    def get_queryset(self):
        """Filter expenses based on user role"""
        user = self.request.user
        
        if user.is_superuser:
            # Superusers see all expenses
            queryset = CarExpense.objects.all().select_related("car", "investor")
        else:
            # Regular users only see expenses for cars they invested in
            queryset = CarExpense.objects.filter(
                car__investments__investor=user
            ).select_related("car", "investor").distinct()
        
        # Filter by car_id if provided
        car_id = self.request.query_params.get('car_id')
        if car_id:
            queryset = queryset.filter(car_id=car_id)
        
        return queryset

    def perform_create(self, serializer):
        """Only superusers can create expenses"""
        if not self.request.user.is_superuser:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only superusers can create expenses")
        serializer.save()


class DashboardStatsAPIView(APIView):
    """
    Dashboard statistics API - Admin only access
    Provides overview statistics for the admin dashboard
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        """Get dashboard statistics"""
        try:
            # Car statistics
            total_cars = Car.objects.count()
            sold_cars = Car.objects.filter(status='sold').count()
            available_cars = Car.objects.filter(status='available').count()
            
            # User statistics
            total_users = User.objects.count()
            total_investors = User.objects.filter(role='investor').count()
            total_admins = User.objects.filter(role='admin').count()
            
            # Investment statistics
            from show_room.models import CarInvestment
            total_investments = CarInvestment.objects.count()
            total_invested_amount = sum(inv.amount for inv in CarInvestment.objects.all())
            
            # Expense statistics
            total_expenses = CarExpense.objects.count()
            total_expense_amount = sum(exp.amount for exp in CarExpense.objects.all())
            
            # Profit statistics (for sold cars)
            sold_cars_queryset = Car.objects.filter(status='sold', sold_amount__isnull=False)
            total_profit = sum(car.profit for car in sold_cars_queryset)
            
            # Recent activity
            recent_cars = Car.objects.order_by('-created')[:5]
            recent_expenses = CarExpense.objects.order_by('-created')[:5]
            
            # Prepare response data
            stats = {
                "overview": {
                    "total_cars": total_cars,
                    "sold_cars": sold_cars,
                    "available_cars": available_cars,
                    "total_users": total_users,
                    "total_investors": total_investors,
                    "total_admins": total_admins
                },
                "financial": {
                    "total_investments": total_investments,
                    "total_invested_amount": f"{total_invested_amount:.2f}",
                    "total_expenses": total_expenses,
                    "total_expense_amount": f"{total_expense_amount:.2f}",
                    "total_profit": f"{total_profit:.2f}",
                    "average_car_value": f"{(total_invested_amount / total_cars):.2f}" if total_cars > 0 else "0.00"
                },
                "recent_activity": {
                    "recent_cars": [
                        {
                            "id": car.id,
                            "brand": car.brand,
                            "model_name": car.model_name,
                            "car_number": car.car_number,
                            "status": car.status,
                            "total_amount": f"{car.total_amount:.2f}",
                            "created": car.created.strftime("%Y-%m-%d %H:%M:%S")
                        }
                        for car in recent_cars
                    ],
                    "recent_expenses": [
                        {
                            "id": exp.id,
                            "car_number": exp.car.car_number,
                            "investor_email": exp.investor.email,
                            "amount": f"{exp.amount:.2f}",
                            "description": exp.description,
                            "created": exp.created.strftime("%Y-%m-%d %H:%M:%S")
                        }
                        for exp in recent_expenses
                    ]
                },
                "car_status_breakdown": {
                    "available": available_cars,
                    "sold": sold_cars
                }
            }
            
            return Response(stats, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to fetch dashboard statistics: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
