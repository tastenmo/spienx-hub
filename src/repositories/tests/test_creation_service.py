from django.test import TestCase
from repositories.services import GitRepositoryCreationService
from repositories.grpc import repositories_pb2
from repositories.grpc.repositories_pb2_grpc import (
    GitRepositoryCreationControllerStub,
    add_GitRepositoryCreationControllerServicer_to_server,
)
from grpc_test_utils.fake_grpc import FakeFullAIOGRPC
from accounts.models import Organisation
from django.contrib.auth.models import User
from repositories.models import GitRepository
from unittest.mock import patch
from asgiref.sync import async_to_sync

class TestGitRepositoryCreationService(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.org = Organisation.objects.create(
            name='Test Org',
            slug='test-org',
            created_by=self.user
        )
        
        self.fake_grpc = FakeFullAIOGRPC(
            add_GitRepositoryCreationControllerServicer_to_server,
            GitRepositoryCreationService.as_servicer(),
        )

    def tearDown(self):
        self.fake_grpc.close()

    @patch('repositories.services.git_repo')
    def test_init_repository(self, mock_git_repo):
        async def run_test():
            # Create stub
            stub = self.fake_grpc.get_fake_stub(GitRepositoryCreationControllerStub)
            
            request = repositories_pb2.GitRepositoryCreationInitRequest(
                name="new-repo",
                organisation_id=self.org.id,
                description="A new repo"
            )
            
            response = await stub.Init(request)
            
            self.assertTrue(response.local_path.endswith('new-repo'))
            self.assertIsNotNone(response.id)
            
            repo = await GitRepository.objects.aget(id=response.id)
            self.assertEqual(repo.name, "new-repo")
            self.assertEqual(repo.organisation_id, self.org.id)
            self.assertTrue(repo.is_bare)
            
            # Verify git init called
            mock_git_repo.init.assert_called_once()
            args, kwargs = mock_git_repo.init.call_args
            self.assertTrue(args[0].endswith('new-repo'))
            self.assertTrue(kwargs['bare'])

        async_to_sync(run_test)()
