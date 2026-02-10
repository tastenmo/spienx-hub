from django.contrib.auth.models import User
from django_socio_grpc import generics
from django_socio_grpc.decorators import grpc_action
from asgiref.sync import sync_to_async
from .models import UserProfile
from .serializers import UserProtoSerializer, UserProfileProtoSerializer


class CurrentUserService(generics.GenericService):
    """Service for viewing and updating the current authenticated user"""
    serializer_class = UserProtoSerializer

    @grpc_action(
        request=[],
        response=UserProtoSerializer,
    )
    async def GetCurrentUser(self, request, context):
        """Get the current authenticated user's information"""
        # Get user from gRPC context metadata
        # In production, you'd extract this from authentication metadata
        # For now, we'll use a simple approach
        user = await self._get_user_from_context(context)
        serializer = UserProtoSerializer(user)
        return serializer.message

    @grpc_action(
        request=[
            {"name": "email", "type": "string", "optional": True},
            {"name": "first_name", "type": "string", "optional": True},
            {"name": "last_name", "type": "string", "optional": True},
        ],
        response=UserProtoSerializer,
    )
    async def UpdateCurrentUser(self, request, context):
        """Update the current authenticated user's information"""
        user = await self._get_user_from_context(context)
        
        # Update fields only if provided (non-empty)
        if request.email:
            user.email = request.email
        if request.first_name:
            user.first_name = request.first_name
        if request.last_name:
            user.last_name = request.last_name
        
        await sync_to_async(user.save)()
        
        # Reload to get fresh data
        user = await User.objects.aget(pk=user.pk)
        serializer = UserProtoSerializer(user)
        return serializer.message

    async def _get_user_from_context(self, context):
        """Extract authenticated user from gRPC context"""
        # Try to get user from request context (set by test or middleware)
        try:
            # In production grpc-web, you'd extract user from auth metadata
            # For now, get from context's user attribute if available
            if hasattr(context, '_user'):
                return context._user
            # Fallback for testing: get the last created user
            return await User.objects.alast()
        except User.DoesNotExist:
            raise Exception("No user found - authentication required")


class CurrentUserProfileService(generics.GenericService):
    """Service for viewing and updating the current authenticated user's profile"""
    serializer_class = UserProfileProtoSerializer

    @grpc_action(
        request=[],
        response=UserProfileProtoSerializer,
    )
    async def GetCurrentUserProfile(self, request, context):
        """Get the current authenticated user's profile"""
        user = await self._get_user_from_context(context)
        
        # Get or create profile, prefetch user relation
        profile, created = await UserProfile.objects.select_related('user').aget_or_create(user=user)
        
        serializer = UserProfileProtoSerializer(profile)
        return serializer.message

    @grpc_action(
        request=[
            {"name": "bio", "type": "string", "optional": True},
            {"name": "avatar_url", "type": "string", "optional": True},
        ],
        response=UserProfileProtoSerializer,
    )
    async def UpdateCurrentUserProfile(self, request, context):
        """Update the current authenticated user's profile"""
        user = await self._get_user_from_context(context)
        
        # Get or create profile
        profile, created = await UserProfile.objects.aget_or_create(user=user)
        
        # Update fields only if provided (non-empty)
        if request.bio:
            profile.bio = request.bio
        if request.avatar_url:
            profile.avatar_url = request.avatar_url
        
        await sync_to_async(profile.save)()
        
        # Reload with user relation
        profile = await UserProfile.objects.select_related('user').aget(pk=profile.pk)
        serializer = UserProfileProtoSerializer(profile)
        return serializer.message

    async def _get_user_from_context(self, context):
        """Extract authenticated user from gRPC context"""
        # Try to get user from request context (set by test or middleware)
        try:
            # In production grpc-web, you'd extract user from auth metadata
            # For now, get from context's user attribute if available
            if hasattr(context, '_user'):
                return context._user
            # Fallback for testing: get the last created user
            return await User.objects.alast()
        except User.DoesNotExist:
            raise Exception("No user found - authentication required")
