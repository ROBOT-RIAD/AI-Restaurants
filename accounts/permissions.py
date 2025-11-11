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
    Allows access only to users with the 'owner' role (case-insensitive).
    """
    def has_permission(self, request, view):
        role = getattr(request.user, 'role', None)
        print("Role:", role)
        return request.user.is_authenticated and str(role).lower() == 'owner'
    

class IsAdminOrOwner(BasePermission):
    """
    Allows access only to users with admin or owner role.
    """

    def has_permission(self, request, view):
        role = getattr(request.user, 'role', None)
        print("Role:", role)
        return request.user.is_authenticated and role in ['admin', 'owner']