from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from show_room.models import Car, CarExpense
from .serializers import CarListSerializer, CarDetailSerializer, CarExpenseSerializer


class CarViewSet(viewsets.ModelViewSet):
    queryset = Car.objects.all().prefetch_related("investments__investor", "expenses__investor")
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        """Return different serializers for list and detail views"""
        if self.action == 'list':
            return CarListSerializer
        return CarDetailSerializer

    def get_queryset(self):
        """Optimize queryset based on action"""
        if self.action == 'list':
            # For list view, we don't need expenses data
            return Car.objects.all().prefetch_related("investments__investor")
        return Car.objects.all().prefetch_related("investments__investor", "expenses__investor")

    @action(detail=True, methods=['post'])
    def add_expense(self, request, pk=None):
        """Add expense to a specific car"""
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
    queryset = CarExpense.objects.all().select_related("car", "investor")
    serializer_class = CarExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter expenses by car if car_id is provided"""
        queryset = super().get_queryset()
        car_id = self.request.query_params.get('car_id')
        if car_id:
            queryset = queryset.filter(car_id=car_id)
        return queryset
