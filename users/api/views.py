from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from auths.api.permissions import UserManagementPermission, IsSuperAdmin
from .serializers import UserSerializer, InvestorCreateSerializer, ShowRoomOwnerCreateSerializer

User = get_user_model()


class UserManagementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user management with role-based access
    """
    serializer_class = UserSerializer
    permission_classes = [UserManagementPermission]
    
    def get_queryset(self):
        """Filter users based on role"""
        user = self.request.user
        
        if user.is_superuser:
            # Super admin can see all users
            return User.objects.all().order_by('-date_joined')
        elif user.role == 'show_room_owner':
            # Show room owners can see their managed users + themselves
            return user.get_accessible_users().order_by('-date_joined')
        else:
            # Regular users can only see themselves
            return User.objects.filter(id=user.id)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action and user role"""
        if self.action == 'create_investor':
            return InvestorCreateSerializer
        elif self.action == 'create_show_room_owner':
            return ShowRoomOwnerCreateSerializer
        return UserSerializer
    
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
    
    def update(self, request, *args, **kwargs):
        """Override update to add debugging"""
        print("=== UPDATE METHOD CALLED ===")
        print(f"Update request data: {request.data}")
        print(f"Update request FILES: {request.FILES}")
        print(f"Content-Type: {request.content_type}")
        print(f"Method: {request.method}")
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """Override partial_update to add debugging"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("=== PARTIAL UPDATE METHOD CALLED ===")
        logger.info(f"Partial update request data: {request.data}")
        logger.info(f"Partial update request FILES: {request.FILES}")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Method: {request.method}")
        
        print("=== PARTIAL UPDATE METHOD CALLED ===")
        print(f"Partial update request data: {request.data}")
        print(f"Partial update request FILES: {request.FILES}")
        print(f"Content-Type: {request.content_type}")
        print(f"Method: {request.method}")
        
        return super().partial_update(request, *args, **kwargs)
    
    @action(detail=False, methods=['post'], permission_classes=[UserManagementPermission])
    def create_investor(self, request):
        """Create a new investor (for show room owners)"""
        if request.user.role != 'show_room_owner' and not request.user.is_superuser:
            return Response(
                {"error": "Only show room owners can create investors"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = InvestorCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            response_serializer = UserSerializer(user)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[IsSuperAdmin])
    def create_show_room_owner(self, request):
        """Create a new show room owner (super admin only)"""
        serializer = ShowRoomOwnerCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            response_serializer = UserSerializer(user)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['patch'], permission_classes=[IsSuperAdmin])
    def update_show_room_owner(self, request, pk=None):
        """Update a show room owner (super admin only)"""
        user = self.get_object()
        if user.role != 'show_room_owner':
            return Response(
                {"error": "This endpoint is only for show room owners"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ShowRoomOwnerCreateSerializer(
            user, 
            data=request.data, 
            partial=True, 
            context={'request': request}
        )
        if serializer.is_valid():
            user = serializer.save()
            response_serializer = UserSerializer(user)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['patch'])
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
    
    @action(detail=False, methods=['get'])
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
    
    @action(detail=False, methods=['get'])
    def user_stats(self, request):
        """Get user statistics based on current user's role"""
        user = request.user
        
        if user.is_superuser:
            # Super admin sees all stats
            total_users = User.objects.count()
            total_investors = User.objects.filter(role='investor').count()
            total_show_room_owners = User.objects.filter(role='show_room_owner').count()
            total_admins = User.objects.filter(role='admin').count()
        elif user.role == 'show_room_owner':
            # Show room owner sees only their stats
            accessible_users = user.get_accessible_users()
            total_users = accessible_users.count()
            total_investors = accessible_users.filter(role='investor').count()
            total_show_room_owners = 1 if accessible_users.filter(id=user.id).exists() else 0
            total_admins = accessible_users.filter(role='admin').count()
        else:
            # Regular users see minimal stats
            total_users = 1
            total_investors = 1 if user.role == 'investor' else 0
            total_show_room_owners = 0
            total_admins = 0
        
        return Response({
            'total_users': total_users,
            'total_investors': total_investors,
            'total_show_room_owners': total_show_room_owners,
            'total_admins': total_admins,
            'current_user_role': user.role,
            'is_superuser': user.is_superuser
        })
    
    @action(detail=False, methods=['get'])
    def investors_by_show_room_owner(self, request):
        """Get investors grouped by show room owner (super admin only)"""
        if not request.user.is_superuser:
            return Response(
                {"error": "Only super admin can access this endpoint"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        from collections import defaultdict
        
        # Get all show room owners
        show_room_owners = User.objects.filter(role='show_room_owner')
        result = []
        
        for owner in show_room_owners:
            investors = User.objects.filter(
                show_room_owner=owner,
                role='investor'
            ).order_by('-date_joined')
            
            result.append({
                'show_room_owner': {
                    'id': owner.id,
                    'email': owner.email,
                    'full_name': f"{owner.first_name or ''} {owner.last_name or ''}".strip() or owner.email,
                    'date_joined': owner.date_joined
                },
                'investors_count': investors.count(),
                'investors': UserSerializer(investors, many=True).data
            })
        
        return Response({
            'show_room_owners_count': len(result),
            'data': result
        })
    
    @action(detail=True, methods=['patch'])
    def test_image_upload(self, request, pk=None):
        """Test endpoint to debug image upload"""
        import logging
        logger = logging.getLogger(__name__)
        
        user = self.get_object()
        logger.info("=== TEST IMAGE UPLOAD ===")
        logger.info(f"Request data: {request.data}")
        logger.info(f"Request FILES: {request.FILES}")
        logger.info(f"Content-Type: {request.content_type}")
        
        print("=== TEST IMAGE UPLOAD ===")
        print(f"Request data: {request.data}")
        print(f"Request FILES: {request.FILES}")
        print(f"Content-Type: {request.content_type}")
        
        if 'image' in request.FILES:
            image_file = request.FILES['image']
            logger.info(f"Image file found: {image_file.name}")
            logger.info(f"Image size: {image_file.size}")
            logger.info(f"Image content type: {image_file.content_type}")
            
            print(f"Image file found: {image_file.name}")
            print(f"Image size: {image_file.size}")
            print(f"Image content type: {image_file.content_type}")
            
            # Store old image path for comparison
            old_image = str(user.image) if user.image else "None"
            
            # Manually update the image
            user.image = image_file
            user.save()
            
            new_image = str(user.image) if user.image else "None"
            
            logger.info(f"Image updated from {old_image} to {new_image}")
            print(f"Image updated from {old_image} to {new_image}")
            
            return Response({
                'message': 'Image updated successfully',
                'old_image': old_image,
                'new_image': new_image,
                'image_url': user.image.url if user.image else None
            })
        else:
            return Response({
                'error': 'No image file found in request',
                'available_keys': list(request.data.keys()),
                'files_keys': list(request.FILES.keys()),
                'content_type': request.content_type
            })