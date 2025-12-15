from django.test import TestCase
from git.models import GitRepository, SyncTask
from git.tasks import initialize_repository, migrate_repository, sync_repository
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

    @patch('git.tasks._get_gitpython_repo')
    def test_initialize_bare_repository(self, mock_get_repo):
        """Test creating a bare git repository"""
        MockRepo = MagicMock()
        mock_repo_instance = MagicMock()
        MockRepo.init.return_value = mock_repo_instance
        mock_get_repo.return_value = MockRepo

        repo = GitRepository.objects.create(
            name='bare-repo',
            organisation=self.org,
            source_url='',
            local_path='/git/test-org/bare-repo',
            is_bare=True
        )

        with patch('git.tasks.os.makedirs'):
            result = initialize_repository(repo.id)

        self.assertTrue(result['success'])
        self.assertEqual(result['repository_id'], repo.id)

    @patch('git.tasks._get_gitpython_repo')
    def test_initialize_regular_repository(self, mock_get_repo):
        """Test creating a regular (non-bare) git repository"""
        MockRepo = MagicMock()
        MockRepo.init.return_value = MagicMock()
        mock_get_repo.return_value = MockRepo

        repo = GitRepository.objects.create(
            name='regular-repo',
            organisation=self.org,
            source_url='',
            local_path='/git/test-org/regular-repo',
            is_bare=False
        )

        with patch('git.tasks.os.makedirs'):
            result = initialize_repository(repo.id)

        self.assertTrue(result['success'])

    def test_initialize_nonexistent_repository(self):
        """Test initializing a repository that doesn't exist"""
        result = initialize_repository(99999)
        self.assertFalse(result['success'])


class MigrateRepositoryTaskTest(TestCase):
    """Test suite for migrate_repository Celery task"""

    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.org = Organisation.objects.create(
            name='Test Org',
            slug='test-org',
            created_by=self.user
        )

    @patch('git.tasks._get_gitpython_repo')
    def test_migrate_from_source(self, mock_get_repo):
        """Test migrating a repository from source URL"""
        MockRepo = MagicMock()
        mock_repo_instance = MagicMock()
        mock_repo_instance.heads = [MagicMock(name='main')]
        mock_repo_instance.active_branch.name = 'main'
        mock_repo_instance.iter_commits.return_value = iter([1, 2, 3])
        MockRepo.clone_from.return_value = mock_repo_instance
        mock_get_repo.return_value = MockRepo

        repo = GitRepository.objects.create(
            name='github-repo',
            organisation=self.org,
            source_url='https://github.com/user/repo.git',
            local_path='/git/test-org/github-repo',
            is_mirror=True,
            is_bare=True
        )

        with patch('git.tasks.os.makedirs'):
            result = migrate_repository(repo.id, force=False)

        self.assertTrue(result['success'])
        self.assertEqual(result['repository_id'], repo.id)

    def test_migrate_nonexistent_repository(self):
        """Test migrating a repository that doesn't exist"""
        result = migrate_repository(99999)
        self.assertFalse(result['success'])


class SyncRepositoryTaskTest(TestCase):
    """Test suite for sync_repository Celery task"""

    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.org = Organisation.objects.create(
            name='Test Org',
            slug='test-org',
            created_by=self.user
        )

    @patch('git.tasks._get_gitpython_repo')
    @patch('git.tasks.os.path.exists')
    def test_sync_mirror_repository(self, mock_exists, mock_get_repo):
        """Test syncing a mirror repository"""
        MockRepo = MagicMock()
        mock_repo_instance = MagicMock()
        mock_repo_instance.remotes.origin.fetch.return_value = None
        mock_repo_instance.heads = [MagicMock(name='main')]
        mock_repo_instance.head.commit.hexsha = 'abc123def456'
        mock_repo_instance.iter_commits.return_value = iter([1, 2, 3, 4, 5])
        MockRepo.return_value = mock_repo_instance
        mock_get_repo.return_value = MockRepo
        mock_exists.return_value = True

        repo = GitRepository.objects.create(
            name='mirror-repo',
            organisation=self.org,
            source_url='https://github.com/user/repo.git',
            local_path='/git/test-org/mirror-repo',
            is_mirror=True,
            is_bare=True
        )

        result = sync_repository(repo.id)

        self.assertTrue(result['success'])
        self.assertEqual(result['total_commits'], 5)

        repo.refresh_from_db()
        self.assertEqual(repo.status, 'active')

    def test_sync_nonexistent_repository(self):
        """Test syncing a repository that doesn't exist"""
        result = sync_repository(99999)
        self.assertFalse(result['success'])

    def test_sync_creates_sync_task_creates_entry(self):
        """Test that SyncTask is created when calling sync"""
        repo = GitRepository.objects.create(
            name='sync-task-repo',
            organisation=self.org,
            source_url='https://github.com/user/repo.git',
            local_path='/git/test-org/sync-task-repo',
            is_mirror=True
        )

        # Create a sync task
        sync_task = SyncTask.objects.create(
            repository=repo,
            status='pending'
        )

        # Verify task was created
        self.assertEqual(sync_task.repository, repo)
        self.assertEqual(sync_task.status, 'pending')
