import pytest
from documents.models import Document, Build
from documents.services import BuildReadService
from documents.grpc import documents_pb2
from documents.grpc.documents_pb2_grpc import (
    BuildReadControllerStub, 
    add_BuildReadControllerServicer_to_server
)
from repositories.models import GitRepository
from accounts.models import Organisation
from grpc_test_utils.fake_grpc import FakeFullAIOGRPC

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestBuildFiltering:
    async def test_filter_builds_by_document(self):
        # Setup
        org = await Organisation.objects.acreate(name="Test Org", slug="test-org")
        repo = await GitRepository.objects.acreate(
            name="test-repo", 
            organisation=org,
            local_path="/tmp/test-repo"
        )
        
        doc1 = await Document.objects.acreate(title="Doc 1", source=repo)
        doc2 = await Document.objects.acreate(title="Doc 2", source=repo)
        
        await Build.objects.acreate(document=doc1, reference="main", workdir=".", conf_path="conf.py")
        await Build.objects.acreate(document=doc1, reference="dev", workdir=".", conf_path="conf.py")
        await Build.objects.acreate(document=doc2, reference="main", workdir=".", conf_path="conf.py")
        
        # Initialize Fake gRPC
        fake_grpc = FakeFullAIOGRPC(
            add_BuildReadControllerServicer_to_server,
            BuildReadService.as_servicer(),
        )
        
        try:
            stub = fake_grpc.get_fake_stub(BuildReadControllerStub)

            # Test filtering for doc1
            request_doc1 = documents_pb2.BuildReadListRequest(document=doc1.id)
            response_doc1 = await stub.List(request_doc1)
            
            results_doc1 = response_doc1.results
            assert len(results_doc1) == 2
            assert all(b.document == doc1.id for b in results_doc1)
            
            # Test filtering for doc2
            request_doc2 = documents_pb2.BuildReadListRequest(document=doc2.id)
            response_doc2 = await stub.List(request_doc2)
            results_doc2 = response_doc2.results
            assert len(results_doc2) == 1
            assert results_doc2[0].document == doc2.id

            # Test no filter (all builds)
            request_all = documents_pb2.BuildReadListRequest()
            response_all = await stub.List(request_all)
            assert len(response_all.results) == 3
            
        finally:
            fake_grpc.close()
