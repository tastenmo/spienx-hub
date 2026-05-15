from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from accounts.models import Organisation
from repositories.models import GitRepository
from documents.models import Document, StaticAsset
from documents.services import DocumentService
from documents.grpc import documents_pb2
from documents.grpc.documents_pb2_grpc import (
    DocumentControllerStub,
    add_DocumentControllerServicer_to_server,
)
from grpc_test_utils.fake_grpc import FakeFullAIOGRPC
from asgiref.sync import async_to_sync


class TestDocumentStaticAssetService(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com")
        self.org = Organisation.objects.create(name="Test Org", slug="test-org", created_by=self.user)
        self.repo = GitRepository.objects.create(
            name="Test Repo",
            organisation=self.org,
            local_path="/tmp/test_repo",
        )
        self.document = Document.objects.create(title="Doc", source=self.repo)

        self.asset = StaticAsset.objects.create(
            document=self.document,
            path="_static/logo.png",
            hash="a" * 40,
        )
        self.asset.file.save("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.png", ContentFile(b"img"), save=True)

        self.fake_grpc = FakeFullAIOGRPC(
            add_DocumentControllerServicer_to_server,
            DocumentService.as_servicer(),
        )

    def tearDown(self):
        self.fake_grpc.close()

    def test_get_static_asset_url(self):
        async def run_test():
            stub = self.fake_grpc.get_fake_stub(DocumentControllerStub)
            request = documents_pb2.DocumentGetStaticAssetUrlRequest(
                document_id=self.document.id,
                relative_path="_static/logo.png",
            )

            response = await stub.GetStaticAssetUrl(request)

            self.assertEqual(response.path, "_static/logo.png")
            self.assertEqual(response.hash, "a" * 40)
            self.assertTrue(response.url.startswith("/static/static_assets/"))

        async_to_sync(run_test)()
