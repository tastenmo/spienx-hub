from django_socio_grpc import generics
from django_socio_grpc.decorators import grpc_action
from django_filters.rest_framework import DjangoFilterBackend
from .models import Document, Build
from .serializers import DocumentProtoSerializer, BuildProtoSerializer, PageProtoSerializer
from asgiref.sync import sync_to_async
from .tasks import build_sphinxdocs

class BuildReadService(generics.AsyncReadOnlyModelService):
    queryset = Build.objects.all()
    serializer_class = BuildProtoSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['document']

    @grpc_action(
        request=[{"name": "document", "type": "int64", "optional": True}],
        response=BuildProtoSerializer,
        use_response_list=True
    )
    async def List(self, request, context):
        queryset = self.get_queryset()
        if request.document:
            queryset = queryset.filter(document=request.document)
        # Wrap serialization in sync_to_async to handle DB access safely
        return await sync_to_async(lambda: self.get_serializer(queryset, many=True).message)()

    @grpc_action(
        request=[{"name": "build_id", "type": "int64"}],
        response=PageProtoSerializer,
        response_stream=True,
    )
    async def StreamPages(self, request, context):
        build_id = request.build_id
        
        # Cache all things (prefetching)
        build = await Build.objects.prefetch_related(
            'pages',
            'pages__sections',
            'pages__sections__content_block'
        ).aget(pk=build_id)

        # Iterate and stream
        # Using .all() on the relation uses the prefetched cache
        for page in build.pages.all():
            serializer = PageProtoSerializer(page)
            yield serializer.message

    @grpc_action(
        request=[{"name": "build_id", "type": "int64"}],
        response=BuildProtoSerializer,
    )
    async def StartBuild(self, request, context):
        """Start a Sphinx build for an existing Build by id."""
        build = await Build.objects.aget(pk=request.build_id)
        # Trigger Celery task asynchronously
        await sync_to_async(build_sphinxdocs.delay)(build.pk)
        return BuildProtoSerializer(build).message


class DocumentService(generics.AsyncModelService):
    """Service for Document operations"""
    queryset = Document.objects.all()
    serializer_class = DocumentProtoSerializer
    
    @grpc_action(
        request=[
            {"name": "title", "type": "string"},
            {"name": "source", "type": "int64"},
            {"name": "reference", "type": "string"},
            {"name": "workdir", "type": "string"},
            {"name": "conf_path", "type": "string"},
            {"name": "start_immediately", "type": "bool"},
        ],
        response=BuildProtoSerializer,
    )
    async def CreateAndStartBuild(self, request, context):
        """
        Create a new `Document` and an associated `Build`, then start the Sphinx build.
        Returns the created `Build`.
        """
        # Create Document (async)
        doc = await Document.objects.acreate(
            title=getattr(request, 'title', ''),
            source_id=getattr(request, 'source', None),
        )

        # Create Build (async)
        build = await Build.objects.acreate(
            document=doc,
            reference=(getattr(request, 'reference', None) or 'HEAD'),
            workdir=(getattr(request, 'workdir', None) or '.'),
            conf_path=(getattr(request, 'conf_path', None) or 'conf.py'),
        )

        # Start Celery task (fire-and-forget)
        start_now = getattr(request, 'start_immediately', True)
        if start_now:
            # Use Celery async execution
            await sync_to_async(build_sphinxdocs.delay)(build.pk)

        serializer = BuildProtoSerializer(build)
        return serializer.message
