from rest_framework import permissions

class IsBusinessAdmin(permissions.BasePermission):
    """Allows only the 'admin' role to Create/Edit/Delete Plans."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'admin')

class IsAuthorUser(permissions.BasePermission):
    """Allows only the 'author' role to purchase plans."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'author')