from rest_framework import serializers
from django_socio_grpc import proto_serializers
from repositories.models import GitRepository, GitMirrorRepository, SyncTask
from repositories.grpc import repositories_pb2


class GitRepositorySerializer(proto_serializers.ModelProtoSerializer):
    """Serializer for GitRepository model"""
    git_url = serializers.SerializerMethodField()

    def get_git_url(self, obj) -> str | None:
        return getattr(obj, 'git_url', None)

    class Meta:
        model = GitRepository
        fields = '__all__'
        proto_class = repositories_pb2.GitRepositoryResponse
        proto_class_list = repositories_pb2.GitRepositoryListResponse
        extra_kwargs = {
            'local_path': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
            'git_url': {'read_only': True},
        }


class GitMirrorRepositorySerializer(proto_serializers.ModelProtoSerializer):
    """Serializer for GitMirrorRepository model"""
    class Meta:
        model = GitMirrorRepository
        fields = '__all__'
        proto_class = repositories_pb2.GitRepositoryResponse
        proto_class_list = repositories_pb2.GitRepositoryListResponse
        extra_kwargs = {
            'local_path': {'read_only': True},
            'last_synced_at': {'read_only': True},
            'error_message': {'read_only': True},
            'consecutive_failures': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
        }


class SyncTaskSerializer(proto_serializers.ModelProtoSerializer):
    """Serializer for SyncTask model"""
    class Meta:
        model = SyncTask
        fields = '__all__'
        extra_kwargs = {
            'started_at': {'read_only': True},
            'completed_at': {'read_only': True},
            'error_message': {'read_only': True},
            'commits_synced': {'read_only': True},
            'created_at': {'read_only': True},
        }
