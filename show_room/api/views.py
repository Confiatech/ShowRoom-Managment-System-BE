from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from show_room.models import Car, CarExpense, CarExpenseImage, CarInvestment
from .serializers import (
    CarListSerializer, CarDetailSerializer, CarExpenseSerializer, CarExpenseImageSerializer,
    ConsignmentCarCreateSerializer, ConsignmentCarExpenseSerializer
)
from auths.api.permissions import CarPermission, ExpensePermission, IsSuperAdmin, IsAdminOrShowRoomOwner

User = get_user_model()


class CarViewSet(viewsets.ModelViewSet):
    permission_classes = [CarPermission]
    
    def get_serializer_class(self):
        """Return different serializers based on action"""
        if self.action == 'list':
            return CarListSerializer
        elif self.action == 'create_consignment_car':
            return ConsignmentCarCreateSerializer
        return CarDetailSerializer

    def get_queryset(self):
        """Filter queryset based on user role and optimize based on action"""
        user = self.request.user
        
        if user.is_superuser or user.role == 'admin':
            # Superusers and admins see all cars (both investment and consignment)
            base_queryset = Car.objects.all()
        elif user.role == 'show_room_owner':
            # Show room owners see cars they manage (both types)
            base_queryset = Car.objects.filter(show_room_owner=user)
        else:
            # Regular users see:
            # 1. Investment cars they have invested in
            # 2. Consignment cars they own
            base_queryset = Car.objects.filter(
                Q(investments__investor=user) |  # Investment cars they invested in
                Q(car_owner=user)  # Consignment cars they own
            ).distinct()
        
        # Optional filtering by car_type
        car_type = self.request.query_params.get('car_type')
        if car_type in ['investment', 'consignment']:
            base_queryset = base_queryset.filter(car_type=car_type)
        
        if self.action == 'list':
            # For list view, we don't need expenses data
            return base_queryset.prefetch_related("investments__investor", "car_owner")
        return base_queryset.prefetch_related(
            "investments__investor", 
            "expenses__investor", 
            "expenses__images",
            "car_owner"
        )

    @action(detail=True, methods=['post'], permission_classes=[ExpensePermission])
    def add_expense(self, request, pk=None):
        """Add expense to a specific car (admin/show room owner only)"""
        user = request.user
        if not (user.is_superuser or user.role in ['admin', 'show_room_owner']):
            return Response(
                {"error": "Only admins and show room owners can add expenses"}, 
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
        """Get detailed profit calculation for a car (works for both investment and consignment cars)"""
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

    @action(detail=True, methods=['post', 'patch'], permission_classes=[IsAdminOrShowRoomOwner])
    def manage_investments(self, request, pk=None):
        """Add or update investments for a specific car (superuser only)"""
        car = self.get_object()
        
        if request.method == 'POST':
            # Add new investments
            investments_data = request.data.get('investments', [])
            
            if not investments_data:
                return Response(
                    {"error": "No investments data provided"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate total investments
            total_new_investments = sum(float(inv.get('amount', 0)) for inv in investments_data)
            current_total_invested = car.total_invested
            
            if (current_total_invested + total_new_investments) > car.total_amount:
                return Response(
                    {"error": f"Total investments ({current_total_invested + total_new_investments}) would exceed car total amount ({car.total_amount})"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create or update investments
            created_investments = []
            for inv_data in investments_data:
                try:
                    investor_id = inv_data.get('investor')
                    amount = float(inv_data.get('amount', 0))
                    
                    if not investor_id or amount <= 0:
                        continue
                    
                    # Check if investor exists
                    try:
                        investor = User.objects.get(id=investor_id)
                    except User.DoesNotExist:
                        return Response(
                            {"error": f"Investor with ID {investor_id} does not exist"}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    # Create or update investment
                    from show_room.models import CarInvestment
                    investment, created = CarInvestment.objects.get_or_create(
                        car=car,
                        investor=investor,
                        defaults={'amount': amount}
                    )
                    
                    if not created:
                        # Update existing investment
                        investment.amount += amount  # Add to existing amount
                        investment.save()
                    
                    created_investments.append({
                        'investor_id': investor.id,
                        'investor_email': investor.email,
                        'amount': float(investment.amount),
                        'created': created
                    })
                    
                except Exception as e:
                    return Response(
                        {"error": f"Error processing investment: {str(e)}"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            return Response({
                'message': f'Successfully processed {len(created_investments)} investments',
                'investments': created_investments,
                'car_total_invested': float(car.total_invested)
            }, status=status.HTTP_201_CREATED)
        
        elif request.method == 'PATCH':
            # Update existing investments
            investments_data = request.data.get('investments', [])
            
            if not investments_data:
                return Response(
                    {"error": "No investments data provided"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Calculate total of new investments
            total_new_investments = sum(float(inv.get('amount', 0)) for inv in investments_data)
            
            if total_new_investments > car.total_amount:
                return Response(
                    {"error": f"Total investments ({total_new_investments}) cannot exceed car total amount ({car.total_amount})"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Clear existing investments and create new ones
            car.investments.all().delete()
            
            updated_investments = []
            for inv_data in investments_data:
                try:
                    investor_id = inv_data.get('investor')
                    amount = float(inv_data.get('amount', 0))
                    
                    if not investor_id or amount <= 0:
                        continue
                    
                    # Check if investor exists
                    try:
                        investor = User.objects.get(id=investor_id)
                    except User.DoesNotExist:
                        return Response(
                            {"error": f"Investor with ID {investor_id} does not exist"}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    # Create new investment
                    from show_room.models import CarInvestment
                    investment = CarInvestment.objects.create(
                        car=car,
                        investor=investor,
                        amount=amount
                    )
                    
                    updated_investments.append({
                        'investor_id': investor.id,
                        'investor_email': investor.email,
                        'amount': float(investment.amount)
                    })
                    
                except Exception as e:
                    return Response(
                        {"error": f"Error processing investment: {str(e)}"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            return Response({
                'message': f'Successfully updated {len(updated_investments)} investments',
                'investments': updated_investments,
                'car_total_invested': float(car.total_invested)
            }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[IsAdminOrShowRoomOwner])
    def create_consignment_car(self, request):
        """
        Create a new consignment car where show room owner manages a car for a seller
        """
        if request.user.role != 'show_room_owner' and not request.user.is_superuser:
            return Response(
                {"error": "Only show room owners can create consignment cars"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ConsignmentCarCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            car = serializer.save()
            response_serializer = CarDetailSerializer(car, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrShowRoomOwner])
    def add_consignment_expense(self, request, pk=None):
        """
        Add expense to a consignment car (show room owner only)
        """
        car = self.get_object()
        
        if car.car_type != 'consignment':
            return Response(
                {"error": "This endpoint is only for consignment cars"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if request.user.role != 'show_room_owner' or car.show_room_owner != request.user:
            return Response(
                {"error": "Only the managing show room owner can add expenses to consignment cars"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ConsignmentCarExpenseSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            expense = serializer.save(car=car)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class CarExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = CarExpenseSerializer
    permission_classes = [ExpensePermission]

    def get_queryset(self):
        """Filter expenses based on user role"""
        user = self.request.user
        
        if user.is_superuser or user.role == 'admin':
            # Superusers and admins see all expenses
            queryset = CarExpense.objects.all().select_related("car", "investor").prefetch_related("images")
        elif user.role == 'show_room_owner':
            # Show room owners see expenses for their cars only
            queryset = CarExpense.objects.filter(
                car__show_room_owner=user
            ).select_related("car", "investor").prefetch_related("images")
        else:
            # Regular users only see expenses for cars they invested in
            queryset = CarExpense.objects.filter(
                car__investments__investor=user
            ).select_related("car", "investor").prefetch_related("images").distinct()
        
        # Filter by car_id if provided
        car_id = self.request.query_params.get('car_id')
        if car_id:
            queryset = queryset.filter(car_id=car_id)
        
        return queryset

    def perform_create(self, serializer):
        """Only admins and show room owners can create expenses"""
        user = self.request.user
        if not (user.is_superuser or user.role in ['admin', 'show_room_owner']):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only admins and show room owners can create expenses")
        serializer.save()

    def create(self, request, *args, **kwargs):
        """Override create to handle image files and return complete expense data"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check permissions
        user = request.user
        if not (user.is_superuser or user.role in ['admin', 'show_room_owner']):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only admins and show room owners can create expenses")
        
        # Create the expense with images
        expense = serializer.save()
        
        # Return the complete expense data with images
        response_serializer = self.get_serializer(expense)
        headers = self.get_success_headers(response_serializer.data)
        
        return Response(
            response_serializer.data, 
            status=status.HTTP_201_CREATED, 
            headers=headers
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrShowRoomOwner])
    def add_images(self, request, pk=None):
        """Add images to an existing expense"""
        expense = self.get_object()
        
        # Handle multiple image uploads
        images = request.FILES.getlist('images')
        descriptions = request.data.getlist('descriptions', [])
        
        if not images:
            return Response(
                {"error": "No images provided"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_images = []
        for i, image in enumerate(images):
            description = descriptions[i] if i < len(descriptions) else ""
            
            image_obj = CarExpenseImage.objects.create(
                expense=expense,
                image=image,
                description=description
            )
            
            created_images.append({
                'id': image_obj.id,
                'image': request.build_absolute_uri(image_obj.image.url),
                'description': image_obj.description,
                'created': image_obj.created
            })
        
        return Response({
            'message': f'Successfully added {len(created_images)} images to expense',
            'images': created_images,
            'expense_id': expense.id
        }, status=status.HTTP_201_CREATED)


class CarExpenseImageViewSet(viewsets.ModelViewSet):
    """ViewSet for managing expense images"""
    serializer_class = CarExpenseImageSerializer
    permission_classes = [ExpensePermission]

    def get_queryset(self):
        """Filter images based on user role and expense access"""
        user = self.request.user
        
        if user.is_superuser or user.role == 'admin':
            # Superusers and admins see all expense images
            queryset = CarExpenseImage.objects.all().select_related("expense__car", "expense__investor")
        elif user.role == 'show_room_owner':
            # Show room owners see images for expenses of their cars
            queryset = CarExpenseImage.objects.filter(
                expense__car__show_room_owner=user
            ).select_related("expense__car", "expense__investor")
        else:
            # Regular users only see images for expenses of cars they invested in
            queryset = CarExpenseImage.objects.filter(
                expense__car__investments__investor=user
            ).select_related("expense__car", "expense__investor").distinct()
        
        # Filter by expense_id if provided
        expense_id = self.request.query_params.get('expense_id')
        if expense_id:
            queryset = queryset.filter(expense_id=expense_id)
        
        return queryset

    def perform_create(self, serializer):
        """Only admins and show room owners can create expense images"""
        user = self.request.user
        if not (user.is_superuser or user.role in ['admin', 'show_room_owner']):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only admins and show room owners can create expense images")
        serializer.save()

    @action(detail=False, methods=['post'], permission_classes=[IsAdminOrShowRoomOwner])
    def bulk_upload(self, request):
        """Bulk upload images for an expense"""
        expense_id = request.data.get('expense_id')
        if not expense_id:
            return Response(
                {"error": "expense_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            expense = CarExpense.objects.get(id=expense_id)
        except CarExpense.DoesNotExist:
            return Response(
                {"error": "Expense not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Handle multiple image uploads
        images = request.FILES.getlist('images')
        descriptions = request.data.getlist('descriptions', [])
        
        if not images:
            return Response(
                {"error": "No images provided"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_images = []
        for i, image in enumerate(images):
            description = descriptions[i] if i < len(descriptions) else ""
            
            image_obj = CarExpenseImage.objects.create(
                expense=expense,
                image=image,
                description=description
            )
            
            created_images.append({
                'id': image_obj.id,
                'image': request.build_absolute_uri(image_obj.image.url),
                'description': image_obj.description,
                'created': image_obj.created
            })
        
        return Response({
            'message': f'Successfully uploaded {len(created_images)} images',
            'images': created_images
        }, status=status.HTTP_201_CREATED)


class DashboardStatsAPIView(APIView):
    """
    Dashboard statistics API - Admin and Show Room Owner access
    Provides overview statistics for the dashboard
    """
    permission_classes = [IsAdminOrShowRoomOwner]

    def get(self, request):
        """Get dashboard statistics"""
        try:
            user = request.user
            
            # Filter data based on user role
            if user.is_superuser or user.role == 'admin':
                # Superusers and admins see all data
                cars_queryset = Car.objects.all()
                expenses_queryset = CarExpense.objects.all()
                investments_queryset = CarInvestment.objects.all()
                users_queryset = User.objects.all()
            elif user.role == 'show_room_owner':
                # Show room owners see only their data
                cars_queryset = Car.objects.filter(show_room_owner=user)
                expenses_queryset = CarExpense.objects.filter(car__show_room_owner=user)
                investments_queryset = CarInvestment.objects.filter(car__show_room_owner=user)
                users_queryset = user.get_accessible_users()
            else:
                # Regular users have no access (handled by permission)
                cars_queryset = Car.objects.none()
                expenses_queryset = CarExpense.objects.none()
                investments_queryset = CarInvestment.objects.none()
                users_queryset = User.objects.none()
            
            # Car statistics
            total_cars = cars_queryset.count()
            sold_cars = cars_queryset.filter(status='sold').count()
            available_cars = cars_queryset.filter(status='available').count()
            
            # User statistics
            total_users = users_queryset.exclude(id=user.id).count()
            total_investors = users_queryset.filter(role='investor').count()
            total_show_room_owners = users_queryset.filter(role='show_room_owner').count()
            total_admins = users_queryset.filter(role='admin').count()
            
            # Investment statistics
            total_investments = investments_queryset.count()
            total_invested_amount = sum(inv.amount for inv in investments_queryset)
            
            # Expense statistics
            total_expenses = expenses_queryset.count()
            total_expense_amount = sum(exp.amount for exp in expenses_queryset)
            
            # Profit statistics (for sold cars)
            sold_cars_queryset = cars_queryset.filter(status='sold', sold_amount__isnull=False)
            total_profit = sum(car.profit for car in sold_cars_queryset)
            
            # Recent activity
            recent_cars = cars_queryset.order_by('-created')[:5]
            recent_expenses = expenses_queryset.select_related('car', 'investor').prefetch_related('images').order_by('-created')[:5]
            
            # Prepare response data
            stats = {
                "overview": {
                    "total_cars": total_cars,
                    "sold_cars": sold_cars,
                    "available_cars": available_cars,
                    "total_users": total_users,
                    "total_investors": total_investors,
                    "total_show_room_owners": total_show_room_owners,
                    "total_admins": total_admins,
                    "user_role": user.role,
                    "is_superuser": user.is_superuser
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
                            "image_count": exp.images.count(),
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
            print(e)
            return Response(
                {"error": f"Failed to fetch dashboard statistics: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
