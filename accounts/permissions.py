from rest_framework.permissions import BasePermission,SAFE_METHODS


class IsAdminRole(BasePermission):
    """
    Allows access only to users with admin role.
    """

    def has_permission(self, request, view):
        print("Role:", getattr(request.user, 'role', None))
        return request.user.is_authenticated and getattr(request.user, 'role', None) == 'admin'


class IsOwnerRole(BasePermission):
    """
    Allows access only to users with owner role.
    """

    def has_permission(self, request, view):
        print("Role:", getattr(request.user, 'role', None))
        return request.user.is_authenticated and getattr(request.user, 'role', None) == 'owner'
    
