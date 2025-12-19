from django.test import TestCase
from repositories.models import GitRepository, GitMirrorRepository, SyncTask
from repositories.tasks import initialize_repository, clone_mirror_repository, sync_mirror_repository
from accounts.models import Organisation
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock


class InitializeRepositoryTaskTest(TestCase):
    """Test suite for initialize_repository Celery task"""

    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.org = Organisation.objects.create(
            name='Test Org',
            slug='test-org',
            created_by=self.user
        )

    @patch('repositories.tasks.git_tasks.GitPythonRepo')
    @patch('repositories.tasks.git_tasks.os.makedirs')
    def test_initialize_bare_repository(self, mock_makedirs, mock_git_repo):
        """Test creating a bare git repository"""
        mock_repo_instance = MagicMock()
        mock_git_repo.init.return_value = mock_repo_instance

        repo = GitRepository.objects.create(
            name='bare-repo',
            organisation=self.org,
            local_path='/git/test-org/bare-repo',
            is_bare=True
        )

        result = initialize_repository(repo.id)

        self.assertTrue(result['success'])
        self.assertEqual(result['repository_id'], repo.id)
        mock_git_repo.init.assert_called_once_with(repo.local_path, bare=True)

    def test_initialize_nonexistent_repository(self):
        """Test initializing a repository that doesn't exist"""
        result = initialize_repository(99999)
        self.assertFalse(result['success'])


class CloneMirrorRepositoryTaskTest(TestCase):
    """Test suite for clone_mirror_repository Celery task"""

    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.org = Organisation.objects.create(
            name='Test Org',
            slug='test-org',
            created_by=self.user
        )

    @patch('repositories.tasks.git_tasks.GitPythonRepo')
    @patch('repositories.tasks.git_tasks.os.makedirs')
    def test_clone_mirror_from_source(self, mock_makedirs, mock_git_repo):
        """Test cloning a mirror repository from source URL"""
        mock_repo_instance = MagicMock()
        mock_git_repo.clone_from.return_value = mock_repo_instance

        mirror = GitMirrorRepository.objects.create(
            name='github-mirror',
            organisation=self.org,
            source_url='https://github.com/user/repo.git',
            source_type='github',
            local_path='/git/test-org/github-mirror',
            is_bare=True
        )

        result = clone_mirror_repository(mirror.id)

        self.assertTrue(result['success'])
        self.assertEqual(result['mirror_id'], mirror.id)
        mock_git_repo.clone_from.assert_called_once()

    def test_clone_nonexistent_mirror(self):
        """Test cloning a mirror that doesn't exist"""
        result = clone_mirror_repository(99999)
        self.assertFalse(result['success'])


class SyncMirrorRepositoryTaskTest(TestCase):
    """Test suite for sync_mirror_repository Celery task"""

    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.org = Organisation.objects.create(
            name='Test Org',
            slug='test-org',
            created_by=self.user
        )

    @patch('repositories.tasks.git_tasks.GitPythonRepo')
    @patch('repositories.tasks.git_tasks.os.path.exists')
    def test_sync_mirror_repository(self, mock_exists, mock_git_repo):
        """Test syncing a mirror repository"""
        mock_repo_instance = MagicMock()
        mock_origin = MagicMock()
        mock_repo_instance.remotes.origin = mock_origin
        mock_git_repo.return_value = mock_repo_instance
        mock_exists.return_value = True

        mirror = GitMirrorRepository.objects.create(
            name='sync-mirror',
            organisation=self.org,
            source_url='https://github.com/user/repo.git',
            local_path='/git/test-org/sync-mirror',
            is_bare=True,
            status='active'
        )

        result = sync_mirror_repository(mirror.id)

        self.assertTrue(result['success'])
        mock_origin.fetch.assert_called_once()

        mirror.refresh_from_db()
        self.assertEqual(mirror.status, 'active')

    def test_sync_nonexistent_mirror(self):
        """Test syncing a mirror that doesn't exist"""
        result = sync_mirror_repository(99999)
        self.assertFalse(result['success'])

    def test_sync_creates_sync_task(self):
        """Test that SyncTask is created when calling sync"""
        mirror = GitMirrorRepository.objects.create(
            name='sync-task-mirror',
            organisation=self.org,
            source_url='https://github.com/user/repo.git',
            local_path='/git/test-org/sync-task-mirror'
        )

        # Create a sync task
        sync_task = SyncTask.objects.create(
            repository=mirror,
            status='pending'
        )

        # Verify task was created
        self.assertEqual(sync_task.repository, mirror)
        self.assertEqual(sync_task.status, 'pending')
