from django.utils.deprecation import MiddlewareMixin

class DisableCSRFMiddleware(MiddlewareMixin):
    """
    Disable CSRF validation for all requests.
    Useful for pure API-based backends.
    """

    def process_request(self, request):
        setattr(request, "_dont_enforce_csrf_checks", True)
