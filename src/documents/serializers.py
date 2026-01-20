from rest_framework import serializers
from django_socio_grpc import proto_serializers
from .models import Document, Build, Page, Section, ContentBlock
from documents.grpc import documents_pb2


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = '__all__'


class BuildSerializer(serializers.ModelSerializer):
    class Meta:
        model = Build
        fields = '__all__'


class ContentBlockProtoSerializer(proto_serializers.ModelProtoSerializer):
    class Meta:
        model = ContentBlock
        proto_class = documents_pb2.ContentBlockResponse
        fields = ['content_hash', 'jsx_content']


class SectionProtoSerializer(proto_serializers.ModelProtoSerializer):
    content_block = ContentBlockProtoSerializer(read_only=True)

    class Meta:
        model = Section
        proto_class = documents_pb2.SectionResponse
        fields = ['title', 'sphinx_id', 'hash', 'source_path', 'start_line', 'end_line', 'content_block']


class PageProtoSerializer(proto_serializers.ModelProtoSerializer):
    sections = SectionProtoSerializer(many=True, read_only=True)
    current_page_name = serializers.CharField(source='path')

    class Meta:
        model = Page
        proto_class = documents_pb2.PageResponse
        fields = ['current_page_name', 'title', 'context', 'sections']


class BuildProtoSerializer(proto_serializers.ModelProtoSerializer):
    class Meta:
        model = Build
        proto_class = documents_pb2.BuildResponse
        proto_class_list = documents_pb2.BuildListResponse
        # Excluding new fields (commit_hash, version) to maintain proto compatibility
        fields = ['id', 'document', 'reference', 'workdir', 'conf_path', 'last_build_at', 'global_context']


class DocumentProtoSerializer(proto_serializers.ModelProtoSerializer):
    class Meta:
        model = Document
        proto_class = documents_pb2.DocumentResponse
        proto_class_list = documents_pb2.DocumentListResponse
        fields = ['id', 'title', 'source']