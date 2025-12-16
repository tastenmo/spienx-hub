from django.test import TestCase
from repositories.models import GitRepository, SyncTask
from repositories.services import GitRepositoryService
from accounts.models import Organisation, UserProfile
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
import uuid


class GitRepositoryServiceTest(TestCase):
    """Test gRPC service"""

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

    def test_service_exists(self):
        """Test that GitRepositoryService exists"""
        self.assertIsNotNone(GitRepositoryService)


class GitRepositoryIntegrationTest(TestCase):
    """Integration tests for git repository workflow"""

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

    def test_repository_workflow(self):
        """Test complete repository workflow"""
        # Create repository
        repo = GitRepository.objects.create(
            name='workflow-repo',
            organisation=self.org,
            source_url='https://github.com/user/repo.git',
            local_path='/git/test-org/workflow-repo'
        )

        self.assertEqual(repo.status, 'pending')

        # Simulate status change
        repo.status = 'active'
        repo.total_commits = 10
        repo.save()

        repo.refresh_from_db()
        self.assertEqual(repo.status, 'active')
        self.assertEqual(repo.total_commits, 10)

    def test_multiple_repositories_same_org(self):
        """Test creating multiple repositories in same organization"""
        repo1 = GitRepository.objects.create(
            name='repo1',
            organisation=self.org,
            source_url='',
            local_path='/git/test-org/repo1'
        )

        repo2 = GitRepository.objects.create(
            name='repo2',
            organisation=self.org,
            source_url='',
            local_path='/git/test-org/repo2'
        )

        repos = GitRepository.objects.filter(organisation=self.org)
        self.assertEqual(repos.count(), 2)

    def test_sync_task_creation(self):
        """Test SyncTask creation for repository"""
        repo = GitRepository.objects.create(
            name='sync-task-repo',
            organisation=self.org,
            source_url='https://github.com/user/repo.git',
            local_path='/git/test-org/sync-task-repo'
        )

        sync_task = SyncTask.objects.create(
            repository=repo,
            status='pending',
            task_id=str(uuid.uuid4())
        )

        self.assertEqual(sync_task.repository, repo)
        self.assertEqual(sync_task.status, 'pending')
        self.assertIsNotNone(sync_task.task_id)
