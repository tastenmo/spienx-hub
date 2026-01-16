from django_socio_grpc import generics
from django_socio_grpc.decorators import grpc_action
from .models import Document
from .serializers import DocumentProtoSerializer, PageProtoSerializer

class DocumentReadService(generics.AsyncReadOnlyModelService):
    queryset = Document.objects.all()
    serializer_class = DocumentProtoSerializer

    @grpc_action(
        request=[{"name": "document_id", "type": "int64"}],
        response=PageProtoSerializer,
        response_stream=True,
    )
    async def StreamPages(self, request, context):
        document_id = request.document_id
        
        # Cache all things (prefetching)
        document = await Document.objects.prefetch_related(
            'pages',
            'pages__sections',
            'pages__sections__content_block'
        ).aget(pk=document_id)

        # Iterate and stream
        # Using .all() on the relation uses the prefetched cache
        for page in document.pages.all():
            serializer = PageProtoSerializer(page)
            yield serializer.message

