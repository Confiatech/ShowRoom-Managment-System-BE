from rest_framework.permissions import BasePermission


class IsSuperAdminOrReadOnly(BasePermission):
    """
    Custom permission to only allow superadmins to create/update/delete users.
    Regular authenticated users can only read.
    """

    def has_permission(self, request, view):
        # Read permissions for any authenticated user
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return request.user and request.user.is_authenticated
        
        # Write permissions only for superadmins
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_superuser
        )


class IsSuperAdmin(BasePermission):
    """
    Custom permission to only allow superadmins.
    """

    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_superuser
        )


class IsAdminOrShowRoomOwner(BasePermission):
    """
    Custom permission for admin or show room owner operations.
    """

    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.is_superuser or request.user.role in ['admin', 'show_room_owner'])
        )


class CarPermission(BasePermission):
    """
    Custom permission for car operations:
    - Superusers & Admins: Full CRUD access to all cars
    - Show Room Owners: Full CRUD access to their own cars
    - Regular users: Read-only access to cars they have invested in
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Superusers and admins have full access
        if request.user.is_superuser or request.user.role == 'admin':
            return True
        
        # Show room owners can create/manage cars
        if request.user.role == 'show_room_owner':
            return True
        
        # Regular users can only read
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # No write permissions for regular users
        return False

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Superusers and admins have full access
        if request.user.is_superuser or request.user.role == 'admin':
            return True
        
        # Show room owners can only access their own cars
        if request.user.role == 'show_room_owner':
            return obj.show_room_owner == request.user
        
        # Regular users can only read cars they have invested in
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            query =  obj.investments.filter(investor=request.user).exists()
            if query:
                return query
            else:
                return obj.car_owner == request.user
        
        # No write permissions for regular users
        return False


class ExpensePermission(BasePermission):
    """
    Custom permission for expense operations:
    - Superusers & Admins: Full CRUD access to all expenses
    - Show Room Owners: Full CRUD access to expenses for their cars
    - Regular users: Read-only access to expenses for cars they invested in
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Superusers and admins have full access
        if request.user.is_superuser or request.user.role == 'admin':
            return True
        
        # Show room owners can manage expenses for their cars
        if request.user.role == 'show_room_owner':
            return True
        
        # Regular users can only read
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # No write permissions for regular users
        return False

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Superusers and admins have full access
        if request.user.is_superuser or request.user.role == 'admin':
            return True
        
        # Show room owners can only access expenses for their cars
        if request.user.role == 'show_room_owner':
            return obj.car.show_room_owner == request.user
        
        # Regular users can only read expenses for cars they invested in
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return obj.car.investments.filter(investor=request.user).exists()
        
        # No write permissions for regular users
        return False


class UserManagementPermission(BasePermission):
    """
    Custom permission for user management:
    - Superusers: Can manage all users including show room owners
    - Show Room Owners: Can only manage investors assigned to them
    - Regular users: No user management access
    """

    def has_permission(self, request, view):

        if not (request.user and request.user.is_authenticated):
            return False
        
        # Superusers can manage all users
        if request.user.is_superuser:
            return True
        
        # Show room owners can manage their investors
        if request.user.role == 'show_room_owner':
            return True
        if request.user.role == 'investor':
            return True
        
        # No access for regular users
        return False

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        # Superusers can manage all users
        if request.user.is_superuser:
            return True
        
        # Show room owners can only manage their assigned investors
        if request.user.role == 'show_room_owner':
            # Can manage users assigned to them or themselves
            return obj.show_room_owner == request.user or obj == request.user
        
        if request.user.role == 'investor':
            return obj == request.user
            # return True
        # No access for regular users
        return False