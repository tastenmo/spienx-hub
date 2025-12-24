from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED


class HealthCheckView(APIView):
    """
    Public health check endpoint (no authentication required)
    """
    authentication_classes = []
    permission_classes = []
    
    def get(self, request):
        return Response({
            'status': 'healthy',
            'service': 'spienx-hub',
        })


class AuthTestView(APIView):
    """
    Test endpoint to verify authentication is working.
    Requires authentication - use session auth or token auth.
    
    Usage:
    curl -u admin:password http://localhost:8000/api/auth-test/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        return Response({
            'authenticated': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_superuser': user.is_superuser,
                'is_staff': user.is_staff,
            },
            'auth_method': request.auth.__class__.__name__ if request.auth else 'session',
        })


class LoginView(APIView):
    """
    Login endpoint for email/username and password.
    Returns user info and sets session cookie.
    
    POST /api/auth/login/
    {
        "username": "user@example.com",
        "password": "password123"
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return Response({
                'authenticated': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'is_superuser': user.is_superuser,
                    'is_staff': user.is_staff,
                }
            }, status=HTTP_200_OK)
        else:
            return Response(
                {'error': 'Invalid username or password'},
                status=HTTP_401_UNAUTHORIZED
            )


class LogoutView(APIView):
    """
    Logout endpoint. Requires authentication.
    
    POST /api/auth/logout/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        logout(request)
        return Response({'message': 'Successfully logged out'}, status=HTTP_200_OK)


class UserView(APIView):
    """
    Get current user info. Requires authentication.
    
    GET /api/auth/user/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        # Debug logging
        print(f"UserView: user={user}, authenticated={user.is_authenticated}")
        print(f"UserView: session={request.session.session_key}")
        
        return Response({
            'authenticated': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_superuser': user.is_superuser,
                'is_staff': user.is_staff,
            }
        }, status=HTTP_200_OK)

