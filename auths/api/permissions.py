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