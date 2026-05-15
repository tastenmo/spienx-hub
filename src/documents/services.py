from django_socio_grpc import generics
from django_socio_grpc.decorators import grpc_action
from django_socio_grpc.protobuf.generation_plugin import ListGenerationPlugin
from django_filters.rest_framework import DjangoFilterBackend
from .models import Document, Build, StaticAsset, Section
from .serializers import DocumentProtoSerializer, BuildProtoSerializer, PageProtoSerializer
from documents.grpc import documents_pb2
from asgiref.sync import sync_to_async
from .tasks import build_sphinxdocs
import grpc

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
        response=[
            {"name": "id", "type": "string"},
            {"name": "title", "type": "string"},
            {"name": "page_path", "type": "string"},
            {"name": "hash", "type": "string"},
            {"name": "level", "type": "int32"},
            {"name": "source_path", "type": "string"},
            {"name": "start_line", "type": "int32"},
            {"name": "end_line", "type": "int32"},
            {"name": "parent_hash", "type": "string"},
            {"name": "order_index", "type": "int32"},
            {"name": "can_open_source", "type": "bool"},
            {"name": "can_edit", "type": "bool"},
        ],
        use_generation_plugins=[ListGenerationPlugin(response=True)],
    )
    async def GetTableOfContents(self, request, context):
        build = await Build.objects.aget(pk=request.build_id)

        toc_pages = []
        if isinstance(build.global_context, dict):
            toc_pages = build.global_context.get('toc_pages') or []

        page_order = {page_path: idx for idx, page_path in enumerate(toc_pages)}

        sections = []
        async for section in Section.objects.filter(page__build_id=build.id).select_related('page', 'parent_section').order_by('page__path', 'order_index', 'start_line', 'id'):
            sections.append(section)

        def sort_key(section: Section) -> tuple[int, str, int, int, int]:
            page_idx = page_order.get(section.page.path, 10**9)
            return (page_idx, section.page.path, section.order_index, section.start_line, section.id)

        sections.sort(key=sort_key)

        items = [
            documents_pb2.BuildReadGetTableOfContentsResponse(
                id=section.sphinx_id,
                title=section.title,
                page_path=section.page.path,
                hash=section.hash,
                level=section.level,
                source_path=section.source_path,
                start_line=section.start_line,
                end_line=section.end_line,
                parent_hash=section.parent_section.hash if section.parent_section else '',
                order_index=section.order_index,
                can_open_source=bool(section.source_path),
                can_edit=False,
            )
            for section in sections
        ]

        return documents_pb2.BuildReadGetTableOfContentsListResponse(results=items)

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

    @grpc_action(
        request=[
            {"name": "document_id", "type": "int64"},
            {"name": "relative_path", "type": "string"},
        ],
        response=[
            {"name": "path", "type": "string"},
            {"name": "url", "type": "string"},
            {"name": "hash", "type": "string"},
        ],
    )
    async def GetStaticAssetUrl(self, request, context):
        asset = await StaticAsset.objects.filter(
            document_id=request.document_id,
            path=request.relative_path,
        ).afirst()

        if asset is None:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Static asset not found for document_id={request.document_id} path={request.relative_path}",
            )

        return documents_pb2.DocumentGetStaticAssetUrlResponse(
            path=asset.path,
            url=asset.file.url,
            hash=asset.hash,
        )
