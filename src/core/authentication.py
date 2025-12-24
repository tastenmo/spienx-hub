from django.contrib.sessions.models import Session
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication

class GrpcSessionAuthentication(BaseAuthentication):
    """
    Custom Session Authentication for gRPC.
    Manually parses the sessionid from the cookie if middleware failed to populate user.
    """
    def authenticate(self, request):
        # 1. Check if middleware already did the job
        user = getattr(request, 'user', None)
        if user and user.is_active and user.is_authenticated:
            return (user, None)

        # 2. Fallback: Manual session lookup
        # The middleware might fail if the request object structure isn't exactly what it expects
        # or if the cookie parsing in ASGI/gRPC context is slightly off.
        
        cookie_header = request.META.get('HTTP_COOKIE', '')
        if not cookie_header:
            return None
            
        # Simple cookie parsing
        cookies = {}
        for item in cookie_header.split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                cookies[name] = value
        
        session_key = cookies.get('sessionid')
        if not session_key:
            return None
            
        try:
            session = Session.objects.get(session_key=session_key)
            uid = session.get_decoded().get('_auth_user_id')
            if uid:
                User = get_user_model()
                user = User.objects.get(pk=uid)
                if user.is_active:
                    # Attach to request for subsequent permissions checks
                    request.user = user
                    return (user, None)
        except (Session.DoesNotExist, User.DoesNotExist):
            pass
            
        return None
