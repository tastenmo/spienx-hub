from django.test import TestCase
from django.contrib.auth.models import User
from repositories.models import GitRepository, GitMirrorRepository, SyncTask
from accounts.models import Organisation, UserProfile
import uuid


class GitRepositoryModelTest(TestCase):
    """Test suite for GitRepository model"""

    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.org = Organisation.objects.create(
            name='Test Org',
            slug='test-org',
            created_by=self.user
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            organisation=self.org,
            role='admin'
        )

    def test_create_bare_repository(self):
        """Test creating a bare repository"""
        repo = GitRepository.objects.create(
            name='bare-repo',
            organisation=self.org,
            local_path='/git/test-org/bare-repo',
            is_bare=True
        )

        self.assertEqual(repo.name, 'bare-repo')
        self.assertTrue(repo.is_bare)
        self.assertEqual(str(repo), 'Test Org/bare-repo')

    def test_create_non_bare_repository(self):
        """Test creating a non-bare repository"""
        repo = GitRepository.objects.create(
            name='regular-repo',
            organisation=self.org,
            local_path='/git/test-org/regular-repo',
            is_bare=False
        )

        self.assertFalse(repo.is_bare)

    def test_repository_owner_tracking(self):
        """Test tracking repository owner"""
        repo = GitRepository.objects.create(
            name='owned-repo',
            organisation=self.org,
            local_path='/git/test-org/owned-repo',
            owner=self.profile
        )

        self.assertEqual(repo.owner, self.profile)
        self.assertEqual(repo.owner.user, self.user)

    def test_unique_together_constraint(self):
        """Test unique constraint on organisation + name"""
        GitRepository.objects.create(
            name='unique-repo',
            organisation=self.org,
            local_path='/git/test-org/unique-repo'
        )

        with self.assertRaises(Exception):
            GitRepository.objects.create(
                name='unique-repo',
                organisation=self.org,
                local_path='/git/test-org/other-unique-repo'
            )

    def test_git_url_property(self):
        """Test git_url property returns correct URL"""
        repo = GitRepository.objects.create(
            name='test-repo',
            organisation=self.org,
            local_path='/git/test-org/test-repo'
        )

        self.assertIn('test-repo.git', repo.git_url)
        self.assertIn(self.org.name, repo.git_url)


class GitMirrorRepositoryModelTest(TestCase):
    """Test suite for GitMirrorRepository model"""

    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.org = Organisation.objects.create(
            name='Test Org',
            slug='test-org',
            created_by=self.user
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            organisation=self.org,
            role='admin'
        )

    def test_create_mirror_repository(self):
        """Test creating a mirror repository"""
        mirror = GitMirrorRepository.objects.create(
            name='mirror-repo',
            organisation=self.org,
            source_url='https://github.com/user/repo.git',
            source_type='github',
            local_path='/git/test-org/mirror-repo',
            is_bare=True
        )

        self.assertEqual(mirror.name, 'mirror-repo')
        self.assertEqual(mirror.source_url, 'https://github.com/user/repo.git')
        self.assertEqual(mirror.source_type, 'github')
        self.assertEqual(mirror.status, 'pending')
        self.assertTrue(mirror.auto_sync)
        self.assertEqual(str(mirror), 'Test Org/mirror-repo (mirror)')

    def test_mirror_status_transitions(self):
        """Test valid status transitions for mirrors"""
        mirror = GitMirrorRepository.objects.create(
            name='status-mirror',
            organisation=self.org,
            source_url='https://github.com/user/repo.git',
            local_path='/git/test-org/status-mirror'
        )

        statuses = ['pending', 'initializing', 'active', 'failed', 'paused']
        for status in statuses:
            mirror.status = status
            mirror.save()
            mirror.refresh_from_db()
            self.assertEqual(mirror.status, status)

    def test_mirror_error_tracking(self):
        """Test tracking errors in mirror repositories"""
        mirror = GitMirrorRepository.objects.create(
            name='error-mirror',
            organisation=self.org,
            source_url='https://invalid-url.git',
            local_path='/git/test-org/error-mirror',
            status='failed',
            error_message='Connection refused',
            consecutive_failures=3
        )

        self.assertEqual(mirror.status, 'failed')
        self.assertEqual(mirror.error_message, 'Connection refused')
        self.assertEqual(mirror.consecutive_failures, 3)

    def test_mirror_sync_configuration(self):
        """Test sync configuration for mirrors"""
        mirror = GitMirrorRepository.objects.create(
            name='sync-mirror',
            organisation=self.org,
            source_url='https://github.com/user/repo.git',
            local_path='/git/test-org/sync-mirror',
            auto_sync=True,
            sync_interval=7200
        )

        self.assertTrue(mirror.auto_sync)
        self.assertEqual(mirror.sync_interval, 7200)

    def test_mirror_inherits_from_gitrepository(self):
        """Test that GitMirrorRepository inherits from GitRepository"""
        mirror = GitMirrorRepository.objects.create(
            name='inherit-test',
            organisation=self.org,
            source_url='https://github.com/user/repo.git',
            local_path='/git/test-org/inherit-test'
        )

        # Should be accessible as GitRepository
        repo = GitRepository.objects.get(id=mirror.id)
        self.assertEqual(repo.name, 'inherit-test')
        self.assertEqual(repo.organisation, self.org)


class SyncTaskModelTest(TestCase):
    """Test suite for SyncTask model"""

    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.org = Organisation.objects.create(
            name='Test Org',
            slug='test-org',
            created_by=self.user
        )
        self.mirror = GitMirrorRepository.objects.create(
            name='test-mirror',
            organisation=self.org,
            source_url='https://github.com/user/repo.git',
            local_path='/git/test-org/test-mirror'
        )

    def test_create_sync_task(self):
        """Test creating a sync task"""
        task = SyncTask.objects.create(
            repository=self.mirror,
            status='pending'
        )

        self.assertEqual(task.repository, self.mirror)
        self.assertEqual(task.status, 'pending')
        self.assertEqual(task.commits_synced, 0)
        self.assertIsNone(task.started_at)
        self.assertIsNone(task.completed_at)

    def test_sync_task_status_transitions(self):
        """Test valid sync task status transitions"""
        task = SyncTask.objects.create(
            repository=self.mirror,
            status='pending'
        )

        statuses = ['pending', 'running', 'completed', 'failed']
        for status in statuses:
            task.status = status
            task.save()
            task.refresh_from_db()
            self.assertEqual(task.status, status)

    def test_sync_task_with_celery_id(self):
        """Test tracking Celery task ID"""
        celery_id = str(uuid.uuid4())
        task = SyncTask.objects.create(
            repository=self.mirror,
            status='running',
            task_id=celery_id
        )

        self.assertEqual(task.task_id, celery_id)

    def test_sync_task_error_tracking(self):
        """Test tracking sync errors"""
        task = SyncTask.objects.create(
            repository=self.mirror,
            status='failed',
            error_message='Network timeout occurred'
        )

        self.assertEqual(task.status, 'failed')
        self.assertEqual(task.error_message, 'Network timeout occurred')

    def test_sync_task_success_tracking(self):
        """Test tracking successful sync"""
        from django.utils import timezone
        
        task = SyncTask.objects.create(
            repository=self.mirror,
            status='pending'
        )

        task.status = 'running'
        task.started_at = timezone.now()
        task.save()

        task.status = 'completed'
        task.completed_at = timezone.now()
        task.commits_synced = 25
        task.save()

        task.refresh_from_db()
        self.assertEqual(task.status, 'completed')
        self.assertIsNotNone(task.started_at)
        self.assertIsNotNone(task.completed_at)
        self.assertEqual(task.commits_synced, 25)
