from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.db.models import Q

from .serializers import (
    LoginSerializer,
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    UserPasswordResetSerializer,
)
from .permissions import IsSuperAdmin, IsSuperAdminOrReadOnly, UserManagementPermission

User = get_user_model()


class LoginAPIView(APIView):
    """
    Login API endpoint that authenticates users and returns JWT tokens with user details.
    """
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        """
        Authenticate user with email and password.
        
        Expected payload:
        {
            "email": "user@example.com",
            "password": "userpassword"
        }
        
        Returns:
        - JWT access and refresh tokens
        - User profile information
        """
        # Validate input data using serializer
        serializer = LoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get validated data
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            # Authenticate user
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                if user.is_active:
                    # Generate JWT tokens
                    refresh = RefreshToken.for_user(user)
                    access_token = refresh.access_token
                    
                    # Serialize user data
                    user_serializer = UserSerializer(user)
                    
                    # Prepare response data
                    response_data = {
                        'access_token': str(access_token),
                        'refresh_token': str(refresh),
                        **user_serializer.data
                    }
                    
                    return Response(response_data, status=status.HTTP_200_OK)
                else:

                    return Response('Account is deactivated', status=status.HTTP_401_UNAUTHORIZED)
            else:
                return Response('Invalid email or password', status=status.HTTP_401_UNAUTHORIZED)
                
        except Exception as e:
            return Response(f'An error occurred during login {e}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users with role-based access control.
    
    Provides:
    - GET /users/ - List users (role-based filtering)
    - POST /users/ - Create new user (role-based permissions)
    - GET /users/{id}/ - Retrieve specific user
    - PUT /users/{id}/ - Update user (role-based permissions)
    - PATCH /users/{id}/ - Partial update user (role-based permissions)
    - DELETE /users/{id}/ - Delete user (role-based permissions)
    
    Additional actions:
    - POST /users/create_investor/ - Create investor (show room owner)
    - POST /users/create_show_room_owner/ - Create show room owner (super admin)
    - GET /users/my_investors/ - Get managed investors (show room owner)
    - GET /users/all_show_room_owners/ - Get all show room owners (super admin)
    - PATCH /users/{id}/change_password/ - Change user password
    """
    permission_classes = [UserManagementPermission]
    
    def get_queryset(self):
        """Filter users based on role"""
        user = self.request.user
        
        if user.is_superuser:
            # Super admin can see all users
            return User.objects.all().order_by('-date_joined').exclude(id=user.id)
        elif user.role == 'show_room_owner':
            # Show room owners can see their managed users + themselves
            return user.get_accessible_users().order_by('-date_joined')
        else:
            # Regular users can only see themselves
            return User.objects.filter(id=user.id)
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action == 'create_investor':
            # Import here to avoid circular imports
            from users.api.serializers import InvestorCreateSerializer
            return InvestorCreateSerializer
        elif self.action == 'create_show_room_owner':
            # Import here to avoid circular imports
            from users.api.serializers import ShowRoomOwnerCreateSerializer
            return ShowRoomOwnerCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer
    
    def get_permissions(self):
        """
        Instantiate and return the list of permissions required for this view.
        """
        if self.action == 'create_show_room_owner':
            # Only superadmins can create show room owners
            permission_classes = [IsSuperAdmin]
        elif self.action in ['create', 'create_investor', 'update', 'partial_update', 'destroy', 'change_password']:
            # Role-based permissions for user management
            permission_classes = [UserManagementPermission]
        else:
            # Authenticated users can list and retrieve (filtered by role)
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        """Handle user creation with proper role assignment"""
        user = self.request.user
        
        # Only super admin can create show room owners
        if serializer.validated_data.get('role') == 'show_room_owner' and not user.is_superuser:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only super admin can create show room owners")
        
        # Show room owners can only create investors
        if user.role == 'show_room_owner' and serializer.validated_data.get('role') != 'investor':
            serializer.validated_data['role'] = 'investor'
            serializer.validated_data['show_room_owner'] = user
        
        serializer.save()
    
    def create(self, request, *args, **kwargs):
        """
        Create a new user with role-based permissions.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        response_serializer = UserSerializer(serializer.instance)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """
        Update user (superadmin only).
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        response_serializer = UserSerializer(user)
        return Response(response_serializer.data, status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete user (superadmin only).
        """
        instance = self.get_object()
        
        # Prevent superadmin from deleting themselves
        if instance == request.user:
            return Response('You cannot delete your own account',status=status.HTTP_400_BAD_REQUEST
            )
        
        instance.delete()
        return Response('User deleted successfully'
            ,
            status=status.HTTP_204_NO_CONTENT
        )
    
    def list(self, request, *args, **kwargs):
        """
        List users with role-based filtering and optional search.
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Exclude admin role users for non-superusers
        if not request.user.is_superuser:
            queryset = queryset.exclude(role='admin')
        
        # Optional search functionality
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(cnic__icontains=search)
            )
        
        # Optional role filtering
        role = request.query_params.get('role', None)
        if role:
            queryset = queryset.filter(role=role)
        
        # Optional active status filtering
        is_active = request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve specific user details.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        Get current user's profile.
        """
        serializer = UserSerializer(request.user)
        return Response( serializer.data, status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsSuperAdmin])
    def activate(self, request, pk=None):
        """
        Activate a user account (superadmin only).
        """
        user = self.get_object()
        user.is_active = True
        user.save()
        
        serializer = UserSerializer(user)
        return Response(
            serializer.data, status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsSuperAdmin])
    def deactivate(self, request, pk=None):
        """
        Deactivate a user account (superadmin only).
        """
        user = self.get_object()
        
        # Prevent superadmin from deactivating themselves
        if user == request.user:
            return Response('You cannot deactivate your own account',
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.is_active = False
        user.save()
        
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], permission_classes=[UserManagementPermission])
    def create_investor(self, request):
        """Create a new investor (for show room owners)"""
        if request.user.role != 'show_room_owner' and not request.user.is_superuser:
            return Response(
                {"error": "Only show room owners can create investors"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Import here to avoid circular imports
        from users.api.serializers import InvestorCreateSerializer
        
        serializer = InvestorCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            response_serializer = UserSerializer(user)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[IsSuperAdmin])
    def create_show_room_owner(self, request):
        """Create a new show room owner (super admin only)"""
        # Import here to avoid circular imports
        from users.api.serializers import ShowRoomOwnerCreateSerializer
        
        serializer = ShowRoomOwnerCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            response_serializer = UserSerializer(user)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['patch'], permission_classes=[UserManagementPermission])
    def change_password(self, request, pk=None):
        """Change user password"""
        user_to_change = self.get_object()
        current_user = request.user
        
        # Check permissions
        if not (current_user.is_superuser or 
                (current_user.role == 'show_room_owner' and user_to_change.show_room_owner == current_user) or
                current_user == user_to_change):
            return Response(
                {"error": "You don't have permission to change this user's password"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        new_password = request.data.get('password')
        if not new_password:
            return Response(
                {"error": "Password is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user_to_change.set_password(new_password)
        user_to_change.save()
        
        return Response(
            {"message": "Password changed successfully"}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'], permission_classes=[UserManagementPermission])
    def my_investors(self, request):
        """Get investors managed by the current show room owner"""
        if request.user.role != 'show_room_owner':
            return Response(
                {"error": "Only show room owners can access this endpoint"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        investors = User.objects.filter(
            show_room_owner=request.user,
            role='investor'
        ).order_by('-date_joined')
        
        serializer = UserSerializer(investors, many=True)
        return Response({
            'count': investors.count(),
            'investors': serializer.data
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsSuperAdmin])
    def all_show_room_owners(self, request):
        """Get all show room owners (super admin only)"""
        show_room_owners = User.objects.filter(role='show_room_owner').order_by('-date_joined')
        serializer = UserSerializer(show_room_owners, many=True)
        return Response({
            'count': show_room_owners.count(),
            'show_room_owners': serializer.data
        })
    
    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def reset_user_password(self, request, pk=None):
        """
        Reset user password by show room owner (only new password required)
        Show room owners can reset passwords for their managed users
        
        Expected payload:
        {
            "new_password": "newpassword123"
        }
        """
        user_to_reset = self.get_object()
        current_user = request.user
        
        # Check if current user is a show room owner and the target user is managed by them
        if current_user.role == 'investor' and current_user.id != user_to_reset.id:
            return Response(
                {"error": "You can only reset passwords for users you manage"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate input using serializer
        serializer = UserPasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Set new password
            new_password = serializer.validated_data['new_password']
            user_to_reset.set_password(new_password)
            user_to_reset.save()
            
            return Response({
                "message": f"Password successfully reset for user {user_to_reset.email}",
                "user_id": user_to_reset.id,
                "user_email": user_to_reset.email,
                "reset_by": current_user.email,
                "timestamp": user_to_reset.last_login
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to reset password: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
