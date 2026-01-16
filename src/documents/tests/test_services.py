from django.test import TestCase
from django.contrib.auth.models import User
from accounts.models import Organisation
from repositories.models import GitRepository
from documents.models import Document
from documents.services import DocumentReadService
from documents.grpc import documents_pb2
from documents.grpc.documents_pb2_grpc import (
    DocumentReadControllerStub, 
    add_DocumentReadControllerServicer_to_server
)
from grpc_test_utils.fake_grpc import FakeFullAIOGRPC
from asgiref.sync import async_to_sync

class TestDocumentReadService(TestCase):
    def setUp(self):
        # Create test data
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.org = Organisation.objects.create(name='Test Org', slug='test-org', created_by=self.user)
        self.repo = GitRepository.objects.create(
            name='Test Repo',
            organisation=self.org,
            local_path='/tmp/test_repo'
        )
        self.doc1 = Document.objects.create(
            title="Doc 1",
            source=self.repo,
            reference="main",
            workdir=".",
            conf_path="conf.py"
        )
        self.doc2 = Document.objects.create(
            title="Doc 2",
            source=self.repo,
            reference="dev",
            workdir=".",
            conf_path="qc_conf.py"
        )

        # Initialize Fake gRPC
        self.fake_grpc = FakeFullAIOGRPC(
            add_DocumentReadControllerServicer_to_server,
            DocumentReadService.as_servicer(),
        )

    def tearDown(self):
        self.fake_grpc.close()

    def test_list_documents(self):
        async def run_test():
            stub = self.fake_grpc.get_fake_stub(DocumentReadControllerStub)
            request = documents_pb2.DocumentListRequest()
            response = await stub.List(request)
            
            self.assertEqual(len(response.results), 2)
            titles = sorted([doc.title for doc in response.results])
            self.assertEqual(titles, ["Doc 1", "Doc 2"])
            
        async_to_sync(run_test)()

    def test_retrieve_document(self):
        async def run_test():
            stub = self.fake_grpc.get_fake_stub(DocumentReadControllerStub)
            request = documents_pb2.DocumentRetrieveRequest(id=self.doc1.id)
            response = await stub.Retrieve(request)
            
            self.assertEqual(response.id, self.doc1.id)
            self.assertEqual(response.title, "Doc 1")
            self.assertEqual(response.source, self.repo.id)
            self.assertEqual(response.reference, "main")
            
        async_to_sync(run_test)()

    def test_stream_pages(self):
        # Create Page, Sections, and ContentBlock
        from documents.models import Page, Section, ContentBlock

        # Create ContentBlock
        cb = ContentBlock.objects.create(content_hash="abc", jsx_content="<p>Block</p>")

        # Create Page for doc1
        page1 = Page.objects.create(
            document=self.doc1,
            current_page_name="page1",
            title="Page 1",
            context={"foo": "bar"}
        )

        # Create Section
        Section.objects.create(
            page=page1,
            title="Section 1",
            sphinx_id="s1",
            hash="abc",
            source_path="index.rst",
            start_line=1,
            end_line=10,
            content_block=cb
        )

        async def run_test():
            stub = self.fake_grpc.get_fake_stub(DocumentReadControllerStub)
            request = documents_pb2.DocumentReadStreamPagesRequest(document_id=self.doc1.id)

            # Streaming response is an async iterator
            responses = []
            async for response in stub.StreamPages(request):
                responses.append(response)

            self.assertEqual(len(responses), 1)
            page_resp = responses[0]
            self.assertEqual(page_resp.title, "Page 1")
            self.assertEqual(len(page_resp.sections), 1)
            self.assertEqual(page_resp.sections[0].content_block.jsx_content, "<p>Block</p>")

        async_to_sync(run_test)()

