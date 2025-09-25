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


class CarPermission(BasePermission):
    """
    Custom permission for car operations:
    - Superusers: Full CRUD access to all cars
    - Regular users: Read-only access to cars they have invested in
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Superusers have full access
        if request.user.is_superuser:
            return True
        
        # Regular users can only read
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # No write permissions for regular users
        return False

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Superusers have full access
        if request.user.is_superuser:
            return True
        
        # Regular users can only read cars they have invested in
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return obj.investments.filter(investor=request.user).exists()
        
        # No write permissions for regular users
        return False


class ExpensePermission(BasePermission):
    """
    Custom permission for expense operations:
    - Only superusers can create, update, delete expenses
    - Regular users can only read expenses for cars they invested in
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Superusers have full access
        if request.user.is_superuser:
            return True
        
        # Regular users can only read
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # No write permissions for regular users
        return False

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Superusers have full access
        if request.user.is_superuser:
            return True
        
        # Regular users can only read expenses for cars they invested in
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return obj.car.investments.filter(investor=request.user).exists()
        
        # No write permissions for regular users
        return False