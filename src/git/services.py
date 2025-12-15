from django_socio_grpc import generics, proto_serializers
from rest_framework import serializers
from git.models import GitRepository
from git.grpc import git_pb2


class GitRepositorySerializer(proto_serializers.ModelProtoSerializer):
    """Serializer for GitRepository model"""
    class Meta:
        model = GitRepository
        fields = '__all__'
        proto_class = git_pb2.GitRepositoryResponse
        proto_class_list = git_pb2.GitRepositoryListResponse
        extra_kwargs = {
            'local_path': {'read_only': True},
            'last_synced_at': {'read_only': True},
            'last_commit_hash': {'read_only': True},
            'total_commits': {'read_only': True},
            'error_message': {'read_only': True},
        }

    def create(self, validated_data):
        import os
        from django.conf import settings
        
        # Generate local_path
        # Default to a 'repos' directory in the base dir if not configured
        base_dir = getattr(settings, 'GIT_REPOS_ROOT', os.path.join(settings.BASE_DIR, 'repos'))
        
        organisation = validated_data.get('organisation')
        name = validated_data.get('name')
        
        # Ensure safe path
        safe_name = "".join([c for c in name if c.isalnum() or c in ('-', '_')])
        
        validated_data['local_path'] = os.path.join(base_dir, str(organisation.id), safe_name)
        
        return super().create(validated_data)


class GitRepositoryService(generics.AsyncModelService):
    """gRPC service for Git Repository management - provides List, Retrieve, Create, Update, Delete"""
    queryset = GitRepository.objects.all()
    serializer_class = GitRepositorySerializer
