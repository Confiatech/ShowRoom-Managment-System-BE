from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from show_room.models import Car, CarExpense
from .serializers import CarListSerializer, CarDetailSerializer, CarExpenseSerializer
from auths.api.permissions import CarPermission, ExpensePermission


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
