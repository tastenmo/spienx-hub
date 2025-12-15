from django.test import TestCase
from django.contrib.auth.models import User
from git.models import GitRepository, GitBranch, GitCommit, SyncTask
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
            source_url='https://github.com/user/repo.git',
            source_type='github',
            local_path='/git/test-org/bare-repo',
            is_bare=True,
            is_mirror=True
        )

        self.assertEqual(repo.name, 'bare-repo')
        self.assertTrue(repo.is_bare)
        self.assertTrue(repo.is_mirror)
        self.assertEqual(repo.status, 'pending')
        self.assertEqual(str(repo), 'Test Org/bare-repo')

    def test_create_regular_repository(self):
        """Test creating a regular (non-bare) repository"""
        repo = GitRepository.objects.create(
            name='regular-repo',
            organisation=self.org,
            source_url='https://gitlab.com/user/repo.git',
            source_type='gitlab',
            local_path='/git/test-org/regular-repo',
            is_bare=False,
            is_mirror=False
        )

        self.assertFalse(repo.is_bare)
        self.assertFalse(repo.is_mirror)

    def test_repository_status_transitions(self):
        """Test valid status transitions"""
        repo = GitRepository.objects.create(
            name='status-repo',
            organisation=self.org,
            source_url='',
            local_path='/git/test-org/status-repo'
        )

        statuses = ['pending', 'initializing', 'mirroring', 'active', 'failed', 'archived']
        for status in statuses:
            repo.status = status
            repo.save()
            repo.refresh_from_db()
            self.assertEqual(repo.status, status)

    def test_repository_owner_tracking(self):
        """Test tracking repository owner"""
        repo = GitRepository.objects.create(
            name='owned-repo',
            organisation=self.org,
            source_url='',
            local_path='/git/test-org/owned-repo',
            owner=self.profile
        )

        self.assertEqual(repo.owner, self.profile)
        self.assertEqual(repo.owner.user, self.user)

    def test_repository_error_tracking(self):
        """Test tracking errors in repository"""
        repo = GitRepository.objects.create(
            name='error-repo',
            organisation=self.org,
            source_url='https://invalid-url.git',
            local_path='/git/test-org/error-repo',
            status='failed',
            error_message='Connection refused'
        )

        self.assertEqual(repo.status, 'failed')
        self.assertEqual(repo.error_message, 'Connection refused')

    def test_unique_together_constraint(self):
        """Test unique constraint on organisation + name"""
        GitRepository.objects.create(
            name='unique-repo',
            organisation=self.org,
            source_url='',
            local_path='/git/test-org/unique-repo'
        )

        with self.assertRaises(Exception):
            GitRepository.objects.create(
                name='unique-repo',
                organisation=self.org,
                source_url='https://other.git',
                local_path='/git/test-org/other-unique-repo'
            )

    def test_repository_metadata_tracking(self):
        """Test tracking repository metadata"""
        repo = GitRepository.objects.create(
            name='metadata-repo',
            organisation=self.org,
            source_url='https://github.com/user/repo.git',
            local_path='/git/test-org/metadata-repo',
            default_branch='develop',
            total_commits=42,
            last_commit_hash='abc123def456'
        )

        self.assertEqual(repo.default_branch, 'develop')
        self.assertEqual(repo.total_commits, 42)
        self.assertEqual(repo.last_commit_hash, 'abc123def456')


class GitBranchModelTest(TestCase):
    """Test suite for GitBranch model"""

    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.org = Organisation.objects.create(
            name='Test Org',
            slug='test-org',
            created_by=self.user
        )
        self.repo = GitRepository.objects.create(
            name='test-repo',
            organisation=self.org,
            source_url='',
            local_path='/git/test-org/test-repo'
        )

    def test_create_branch(self):
        """Test creating a branch"""
        branch = GitBranch.objects.create(
            repository=self.repo,
            name='main',
            commit_hash='abc123'
        )

        self.assertEqual(branch.name, 'main')
        self.assertEqual(branch.commit_hash, 'abc123')
        self.assertFalse(branch.is_default)
        self.assertEqual(str(branch), 'test-repo/main')

    def test_set_default_branch(self):
        """Test marking a branch as default"""
        main_branch = GitBranch.objects.create(
            repository=self.repo,
            name='main',
            commit_hash='abc123',
            is_default=True
        )

        develop_branch = GitBranch.objects.create(
            repository=self.repo,
            name='develop',
            commit_hash='def456',
            is_default=False
        )

        self.assertTrue(main_branch.is_default)
        self.assertFalse(develop_branch.is_default)

    def test_unique_branch_name_per_repo(self):
        """Test unique constraint on repository + name"""
        GitBranch.objects.create(
            repository=self.repo,
            name='feature',
            commit_hash='abc123'
        )

        with self.assertRaises(Exception):
            GitBranch.objects.create(
                repository=self.repo,
                name='feature',
                commit_hash='def456'
            )


class GitCommitModelTest(TestCase):
    """Test suite for GitCommit model"""

    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.org = Organisation.objects.create(
            name='Test Org',
            slug='test-org',
            created_by=self.user
        )
        self.repo = GitRepository.objects.create(
            name='test-repo',
            organisation=self.org,
            source_url='',
            local_path='/git/test-org/test-repo'
        )

    def test_create_commit(self):
        """Test creating a commit record"""
        from django.utils import timezone
        
        commit = GitCommit.objects.create(
            repository=self.repo,
            commit_hash='abc123def456',
            author_name='Test Author',
            author_email='author@example.com',
            message='Initial commit',
            committed_at=timezone.now()
        )

        self.assertEqual(commit.commit_hash, 'abc123def456')
        self.assertEqual(commit.author_name, 'Test Author')
        self.assertEqual(commit.author_email, 'author@example.com')
        self.assertIn('abc123de', str(commit))

    def test_commit_ordering(self):
        """Test that commits are ordered by commit time"""
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        
        commit1 = GitCommit.objects.create(
            repository=self.repo,
            commit_hash='aaa111',
            author_name='Author A',
            author_email='a@example.com',
            message='First',
            committed_at=now - timedelta(days=2)
        )
        
        commit2 = GitCommit.objects.create(
            repository=self.repo,
            commit_hash='bbb222',
            author_name='Author B',
            author_email='b@example.com',
            message='Second',
            committed_at=now - timedelta(days=1)
        )
        
        commits = list(GitCommit.objects.all())
        self.assertEqual(commits[0].commit_hash, 'bbb222')
        self.assertEqual(commits[1].commit_hash, 'aaa111')

    def test_unique_commit_hash_per_repo(self):
        """Test unique constraint on repository + commit_hash"""
        from django.utils import timezone
        
        GitCommit.objects.create(
            repository=self.repo,
            commit_hash='abc123',
            author_name='Author',
            author_email='author@example.com',
            message='Test',
            committed_at=timezone.now()
        )

        with self.assertRaises(Exception):
            GitCommit.objects.create(
                repository=self.repo,
                commit_hash='abc123',
                author_name='Other Author',
                author_email='other@example.com',
                message='Other',
                committed_at=timezone.now()
            )


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
        self.repo = GitRepository.objects.create(
            name='test-repo',
            organisation=self.org,
            source_url='',
            local_path='/git/test-org/test-repo'
        )

    def test_create_sync_task(self):
        """Test creating a sync task"""
        task = SyncTask.objects.create(
            repository=self.repo,
            status='pending'
        )

        self.assertEqual(task.repository, self.repo)
        self.assertEqual(task.status, 'pending')
        self.assertEqual(task.commits_synced, 0)
        self.assertIsNone(task.started_at)
        self.assertIsNone(task.completed_at)

    def test_sync_task_status_transitions(self):
        """Test valid sync task status transitions"""
        task = SyncTask.objects.create(
            repository=self.repo,
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
            repository=self.repo,
            status='running',
            task_id=celery_id
        )

        self.assertEqual(task.task_id, celery_id)

    def test_sync_task_error_tracking(self):
        """Test tracking sync errors"""
        task = SyncTask.objects.create(
            repository=self.repo,
            status='failed',
            error_message='Network timeout occurred'
        )

        self.assertEqual(task.status, 'failed')
        self.assertEqual(task.error_message, 'Network timeout occurred')

    def test_sync_task_success_tracking(self):
        """Test tracking successful sync"""
        from django.utils import timezone
        
        task = SyncTask.objects.create(
            repository=self.repo,
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
