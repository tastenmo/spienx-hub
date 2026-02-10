from django.contrib.auth.models import User
from django_socio_grpc import proto_serializers
from .models import UserProfile
from accounts.grpc import accounts_pb2


class UserProtoSerializer(proto_serializers.ModelProtoSerializer):
    """Serializer for Django User model"""
    
    class Meta:
        model = User
        proto_class = accounts_pb2.UserResponse
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class UserProfileProtoSerializer(proto_serializers.ModelProtoSerializer):
    """Serializer for UserProfile model"""
    user = UserProtoSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        proto_class = accounts_pb2.UserProfileResponse
        fields = ['id', 'user', 'bio', 'avatar_url', 'is_active']
