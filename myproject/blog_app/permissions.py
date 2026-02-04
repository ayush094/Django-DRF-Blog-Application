from rest_framework import permissions

class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    - Authors can create blogs.
    - Only the blog owner (author) can update/delete their blog.
    - Anyone can read (GET) blogs.
    """

    def has_permission(self, request, view):
        # Allow safe methods for everyone
        if request.method in permissions.SAFE_METHODS:
            return True
        # For create: only authenticated users with role author
        if view.action == 'create' or request.method == 'POST':
            return request.user and request.user.is_authenticated and request.user.role == 'author'
        # For other methods, we defer to has_object_permission
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Read-only always allowed
        if request.method in permissions.SAFE_METHODS:
            return True
        # Only owner (author) can edit/delete
        return obj.author == request.user
