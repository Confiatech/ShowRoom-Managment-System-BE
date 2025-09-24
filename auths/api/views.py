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
)
from .permissions import IsSuperAdmin, IsSuperAdminOrReadOnly

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
    ViewSet for managing users. Only superadmins can create/update/delete users.
    
    Provides:
    - GET /users/ - List all users (authenticated users)
    - POST /users/ - Create new user (superadmin only)
    - GET /users/{id}/ - Retrieve specific user (authenticated users)
    - PUT /users/{id}/ - Update user (superadmin only)
    - PATCH /users/{id}/ - Partial update user (superadmin only)
    - DELETE /users/{id}/ - Delete user (superadmin only)
    """
    queryset = User.objects.all().order_by('-date_joined')
    permission_classes = [IsSuperAdminOrReadOnly]
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer
    
    def get_permissions(self):
        """
        Instantiate and return the list of permissions required for this view.
        """
        if self.action == 'create':
            # Only superadmins can create users
            permission_classes = [IsSuperAdmin]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # Only superadmins can modify users
            permission_classes = [IsSuperAdmin]
        else:
            # Authenticated users can list and retrieve
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def create(self, request, *args, **kwargs):
        """
        Create a new user (superadmin only).
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        response_serializer = UserSerializer(user)
        return Response(
            response_serializer.data
            ,
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
        List all users with optional filtering.
        """
        queryset = self.filter_queryset(self.get_queryset()).exclude(role='admin')
        
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
        return Response( serializer.data, status.HTTP_200_OK
        )
    
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
            return Response('You cannot deactivate your own account'
                ,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.is_active = False
        user.save()
        
        serializer = UserSerializer(user)
        return Response( serializer.data
            , status.HTTP_200_OK
        )
