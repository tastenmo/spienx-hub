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
from unittest.mock import patch, MagicMock
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

    @patch('repositories.tasks.git_tasks.GitPythonRepo')
    @patch('repositories.tasks.git_tasks.os.makedirs')
    def test_create_repository(self, mock_makedirs, mock_git_repo):
        async def run_test():
            # Mock Celery task
            mock_task = MagicMock()
            mock_task.id = 'test-task-id'
            
            with patch('repositories.tasks.initialize_repository') as mock_init_task:
                mock_init_task.delay.return_value = mock_task
                
                # Create stub
                stub = self.fake_grpc.get_fake_stub(GitRepositoryCreationControllerStub)
                
                request = repositories_pb2.GitRepositoryCreationCreateRequest(
                    name="new-repo",
                    organisation_id=self.org.id,
                    description="A new repo",
                    is_public=True
                )
                
                response = await stub.Create(request)
                
                self.assertTrue(response.local_path.endswith('new-repo'))
                self.assertIsNotNone(response.id)
                self.assertIn('new-repo.git', response.git_url)
                
                repo = await GitRepository.objects.aget(id=response.id)
                self.assertEqual(repo.name, "new-repo")
                self.assertEqual(repo.organisation_id, self.org.id)
                self.assertTrue(repo.is_bare)
                self.assertTrue(repo.is_public)
                
                # Verify task was dispatched
                mock_init_task.delay.assert_called_once_with(repo.id)

        async_to_sync(run_test)()
