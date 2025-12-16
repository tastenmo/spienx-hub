from django_socio_grpc import generics, proto_serializers
from django_socio_grpc.decorators import grpc_action
from repositories.models import GitRepository
from repositories.grpc import repositories_pb2

from git import Repo as git_repo


class GitRepositorySerializer(proto_serializers.ModelProtoSerializer):
    """Serializer for GitRepository model"""
    class Meta:
        model = GitRepository
        fields = '__all__'
        proto_class = repositories_pb2.GitRepositoryResponse
        proto_class_list = repositories_pb2.GitRepositoryListResponse
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


class GitRepositoryCreationService(generics.GenericService):
    """gRPC service for creating Git Repositories"""
    @grpc_action(
        request=[
            {"name": "name", "type": "string"},
            {"name": "organisation_id", "type": "int64"},
            {"name": "description", "type": "string"},
        ],
        response=[
            {"name": "id", "type": "int64"},
            {"name": "local_path", "type": "string"},
        ],
    )
    async def Init(self, request, context):
        
        # build the local_path
        import os
        from django.conf import settings
        from repositories.models import GitRepository
        from accounts.models import Organisation
        base_dir = getattr(settings, 'GIT_REPOS_ROOT', os.path.join(settings.BASE_DIR, 'repos'))
        organisation = await Organisation.objects.aget(id=request.organisation_id)
        safe_name = "".join([c for c in request.name if c.isalnum() or c in ('-', '_')])
        local_path = os.path.join(base_dir, safe_name)

        repo = git_repo.init(local_path, bare=True)

        git_repository = GitRepository(
            name=request.name,
            organisation=organisation,
            description=request.description,
            local_path=local_path,
            status='active',
            is_bare=True,
        )
        await git_repository.asave()

        return repositories_pb2.GitRepositoryCreationInitResponse(
            id=git_repository.id,
            local_path=git_repository.local_path
        )



