import json

from django.http import QueryDict

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from datetime import datetime
from django.core.paginator import Paginator
from show_room.models import Car, CarExpense, CarExpenseImage, CarInvestment
from .serializers import (
    CarListSerializer, CarDetailSerializer, CarExpenseSerializer, CarExpenseImageSerializer,
    ConsignmentCarCreateSerializer, ConsignmentCarExpenseSerializer
)
from auths.api.permissions import CarPermission, ExpensePermission, IsSuperAdmin, IsAdminOrShowRoomOwner

User = get_user_model()


class CarViewSet(viewsets.ModelViewSet):
    permission_classes = [CarPermission]
    
    def create(self, request, *args, **kwargs):
        """Override create to parse investments JSON string from form-data"""
      
        
        # Create a mutable copy of the data
        if isinstance(request.data, QueryDict):
            data = request.data.copy()
        else:
            data = dict(request.data)
        
        # Parse investments if it's a string (from form-data)
        if 'investments' in data:
            investments_value = data.get('investments')
            print("investments_value", investments_value)
            
            if isinstance(investments_value, str):
                try:
                    parsed_investments = json.loads(investments_value)
                    data['investments'] = parsed_investments
                except (json.JSONDecodeError, ValueError) as e:
                    return Response(
                        {'investments': [f'Invalid JSON format: {str(e)}']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                parsed_investments = []
        
        # Create serializer with parsed data
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Create investments
        for inv in parsed_investments:
            CarInvestment.objects.create(
                car=serializer.instance,
                investor=User.objects.get(id=inv["investor"]),
                amount=inv["amount"]
            )
            
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def list(self, request, *args, **kwargs):
        """
        List cars with pagination support
        """
        from django.core.paginator import Paginator
        
        # Get the queryset
        queryset = self.filter_queryset(self.get_queryset())
        
        # Get pagination parameters
        page_size = int(request.query_params.get('page_size', 10))
        page_number = int(request.query_params.get('page', 1))
        
        # Apply pagination
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page_number)
        
        # Serialize the paginated data
        serializer = self.get_serializer(page_obj, many=True)
        
        # Prepare response data with pagination info
        response_data = {
            'results': serializer.data,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'page_size': page_size,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
                'previous_page': page_obj.previous_page_number() if page_obj.has_previous() else None
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    
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

    @action(detail=False, methods=['get'], permission_classes=[IsAdminOrShowRoomOwner])
    def show_room_earnings_stats(self, request):
        """
        Get show room earnings statistics with date range filtering and pagination
        Only for show room owners and admins
        """
        from datetime import datetime
        from django.core.paginator import Paginator
        # from django.db.models import Q
        
        user = request.user
        
        # Debug: Print user info
        # print(f"User requesting earnings stats: {user.email}, Role: {user.role}, ID: {user.id}")
        
        # Only show room owners can access their own stats, admins can see all
        if user.role == 'show_room_owner':
            cars_queryset = Car.objects.filter(show_room_owner=user)
            # print(f"Show room owner filtering: Found {cars_queryset.count()} cars for user {user.id}")
        elif user.is_superuser or user.role == 'admin':
            # For admins, optionally filter by show_room_owner_id
            show_room_owner_id = request.query_params.get('show_room_owner_id')
            if show_room_owner_id:
                try:
                    show_room_owner = User.objects.get(id=show_room_owner_id, role='show_room_owner')
                    cars_queryset = Car.objects.filter(show_room_owner=show_room_owner)
                    # print(f"Admin filtering by show_room_owner_id {show_room_owner_id}: Found {cars_queryset.count()} cars")
                except User.DoesNotExist:
                    return Response(
                        {"error": "Show room owner not found"}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                cars_queryset = Car.objects.all()
                # pri+nt(f"Admin viewing all cars: Found {cars_queryset.count()} cars")
        else:
            return Response(
                {"error": "Only show room owners and admins can access earnings stats"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Date range filtering
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                cars_queryset = cars_queryset.filter(created__date__gte=start_date)
            except ValueError:
                return Response(
                    {"error": "Invalid start_date format. Use YYYY-MM-DD"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                cars_queryset = cars_queryset.filter(created__date__lte=end_date)
            except ValueError:
                return Response(
                    {"error": "Invalid end_date format. Use YYYY-MM-DD"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Filter only sold cars (where earnings are realized)
        sold_cars = cars_queryset.filter(
            status='sold',
            sold_amount__isnull=False,
            sold_amount__gt=0
        ).order_by('-created')
        
        # print(f"After date filtering and sold status: Found {sold_cars.count()} sold cars")
        
        # Debug: Print car details
        # for car in sold_cars:
        #     print(f"Car ID: {car.id}, Number: {car.car_number}, Show Room Owner: {car.show_room_owner_id}, User ID: {user.id}")
        
        # Calculate earnings for each car
        earnings_data = []
        total_earnings = 0
        
        for car in sold_cars:
            if car.car_type == 'investment':
                # For investment cars: admin gets percentage of profit
                profit = car.profit
                if profit > 0:
                    earning = (car.admin_percentage / 100) * profit
                else:
                    earning = 0
                    
                earnings_data.append({
                    'car_id': car.id,
                    'car_number': car.car_number,
                    'brand': car.brand,
                    'model_name': car.model_name,
                    'car_type': car.car_type,
                    'total_amount': f"{car.total_amount:.2f}",
                    'sold_amount': f"{car.sold_amount:.2f}",
                    'admin_percentage': f"{car.admin_percentage:.2f}",
                    'profit': f"{profit:.2f}",
                    'earning_from_car': f"{earning:.2f}",
                    'sold_date': car.modified.strftime("%Y-%m-%d"),
                    'calculation_method': 'percentage_of_profit'
                })
                
            elif car.car_type == 'consignment':
                # For consignment cars: show room gets percentage of sold amount + expenses recovered
                percentage_amount = (car.admin_percentage / 100) * car.sold_amount
                show_room_expenses = car.get_show_room_expenses()
                total_earning = percentage_amount + show_room_expenses
                
                earnings_data.append({
                    'car_id': car.id,
                    'car_number': car.car_number,
                    'brand': car.brand,
                    'model_name': car.model_name,
                    'car_type': car.car_type,
                    'asking_price': f"{car.asking_price:.2f}" if car.asking_price else "0.00",
                    'sold_amount': f"{car.sold_amount:.2f}",
                    'admin_percentage': f"{car.admin_percentage:.2f}",
                    'percentage_amount': f"{percentage_amount:.2f}",
                    'show_room_expenses': f"{show_room_expenses:.2f}",
                    'earning_from_car': f"{total_earning:.2f}",
                    'sold_date': car.modified.strftime("%Y-%m-%d"),
                    'calculation_method': 'percentage_plus_expenses'
                })
                earning = total_earning
            
            total_earnings += earning
        
        # Pagination
        page_size = int(request.query_params.get('page_size', 10))
        page_number = int(request.query_params.get('page', 1))
        
        paginator = Paginator(earnings_data, page_size)
        page_obj = paginator.get_page(page_number)
        
        # Summary statistics
        summary = {
            'show_room_owner': {
                'id': user.id,
                'email': user.email,
                'name': f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email,
                'show_room_name': user.show_room_name
            } if user.role == 'show_room_owner' else None,
            'total_sold_cars': sold_cars.count(),
            'total_earnings': f"{total_earnings:.2f}",
            'date_range': {
                'start_date': start_date.strftime('%Y-%m-%d') if start_date else None,
                'end_date': end_date.strftime('%Y-%m-%d') if end_date else None
            },
            'car_type_breakdown': {
                'investment_cars': sold_cars.filter(car_type='investment').count(),
                'consignment_cars': sold_cars.filter(car_type='consignment').count()
            }
        }
        
        # Response data
        response_data = {
            'summary': summary,
            'earnings': list(page_obj),
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'page_size': page_size,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
                'previous_page': page_obj.previous_page_number() if page_obj.has_previous() else None
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

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
        
        # Permission check is handled by perform_create
        self.perform_create(serializer)
        
        # Get the created expense
        expense = serializer.instance
        
        # Return the complete expense data with images
        response_serializer = self.get_serializer(expense)
        headers = self.get_success_headers(response_serializer.data)
        
        return Response(
            response_serializer.data, 
            status=status.HTTP_201_CREATED, 
            headers=headers
        )

    def update(self, request, *args, **kwargs):
        """Override update to handle image management (PUT)"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Update the expense
        self.perform_update(serializer)
        expense = serializer.instance
        
        # Handle image operations
        self._handle_image_operations(request, expense)
        
        # Return updated expense with images
        response_serializer = self.get_serializer(expense)
        return Response(response_serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """Override partial_update to handle image management (PATCH)"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def _handle_image_operations(self, request, expense):
        """Handle adding, removing, and updating images"""
        # 1. Remove images if images_to_remove is provided (array of image IDs)
        images_to_remove = request.data.get('images_to_remove', [])
        
        # Handle both JSON array and form data list
        if isinstance(images_to_remove, str):
            import json
            try:
                images_to_remove = json.loads(images_to_remove)
            except json.JSONDecodeError:
                images_to_remove = []
        elif not isinstance(images_to_remove, list):
            images_to_remove = request.data.getlist('images_to_remove', [])
        
        if images_to_remove:
            CarExpenseImage.objects.filter(
                id__in=images_to_remove,
                expense=expense
            ).delete()
        
        # 2. Add new images if provided (using 'images' key)
        new_images = request.FILES.getlist('images', [])
        descriptions = request.data.getlist('descriptions', [])
        
        for i, image in enumerate(new_images):
            description = descriptions[i] if i < len(descriptions) else ""
            CarExpenseImage.objects.create(
                expense=expense,
                image=image,
                description=description
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
