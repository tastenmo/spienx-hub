from django.test import TestCase
from django.contrib.auth.models import User
from repositories.models import GitRepository, GitMirrorRepository, SyncTask
from accounts.models import Organisation, UserProfile
import uuid
import os
import tempfile
import shutil
from git import Repo


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
            organisation=self.org
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

    def test_create_workdir_with_bare_repository(self):
        """Test creating a working directory from a bare repository"""
        # Create a temporary directory for testing
        temp_dir = tempfile.mkdtemp()
        bare_repo_path = os.path.join(temp_dir, 'bare-repo.git')
        workdir_path = os.path.join(temp_dir, 'workdir')
        
        try:
            # Initialize a bare repository with some content
            init_repo = Repo.init(bare_repo_path, bare=True)
            
            # Create a temporary clone to add content
            temp_clone_path = os.path.join(temp_dir, 'temp-clone')
            clone = Repo.clone_from(f'file://{bare_repo_path}', temp_clone_path)
            
            # Add a test file
            test_file = os.path.join(temp_clone_path, 'test.txt')
            with open(test_file, 'w') as f:
                f.write('Test content')
            
            clone.index.add(['test.txt'])
            clone.index.commit('Initial commit')
            clone.remote('origin').push('master:master')
            
            # Clean up temp clone
            shutil.rmtree(temp_clone_path)
            
            # Create GitRepository model instance
            repo = GitRepository.objects.create(
                name='workdir-test-repo',
                organisation=self.org,
                local_path=bare_repo_path,
                is_bare=True
            )
            
            # Test create_workdir
            working_repo = repo.create_workdir(workdir_path, reference='master')
            
            # Verify the worktree was created
            self.assertTrue(os.path.exists(workdir_path))
            self.assertTrue(os.path.isdir(workdir_path))
            
            # Verify the test file exists in worktree
            test_file_in_workdir = os.path.join(workdir_path, 'test.txt')
            self.assertTrue(os.path.exists(test_file_in_workdir))
            
            # Verify working_repo is a valid Repo object
            self.assertIsInstance(working_repo, Repo)
            self.assertEqual(working_repo.working_dir, workdir_path)
            
            # Verify file content
            with open(test_file_in_workdir, 'r') as f:
                content = f.read()
            self.assertEqual(content, 'Test content')
            
        finally:
            # Clean up
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    def test_create_workdir_with_non_bare_repository(self):
        """Test create_workdir with a non-bare repository"""
        # Create a temporary non-bare repository
        temp_dir = tempfile.mkdtemp()
        repo_path = os.path.join(temp_dir, 'non-bare-repo')
        
        try:
            # Initialize a non-bare repository
            git_repo = Repo.init(repo_path)
            
            # Add a test file
            test_file = os.path.join(repo_path, 'readme.txt')
            with open(test_file, 'w') as f:
                f.write('Non-bare repo content')
            
            git_repo.index.add(['readme.txt'])
            git_repo.index.commit('Initial commit')
            
            # Create GitRepository model instance
            repo = GitRepository.objects.create(
                name='non-bare-test-repo',
                organisation=self.org,
                local_path=repo_path,
                is_bare=False
            )
            
            # Test create_workdir - should return the existing repo
            # For non-bare repos, the path is ignored
            returned_repo = repo.create_workdir(repo_path)
            
            # Verify it returns the existing non-bare repository
            self.assertIsInstance(returned_repo, Repo)
            self.assertEqual(returned_repo.working_dir, repo_path)
            
        finally:
            # Clean up
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def test_create_workdir_creates_directory(self):
        """Test that create_workdir creates the target directory if it doesn't exist"""
        temp_dir = tempfile.mkdtemp()
        bare_repo_path = os.path.join(temp_dir, 'bare-repo.git')
        workdir_path = os.path.join(temp_dir, 'nested', 'workdir')
        
        try:
            # Initialize a bare repository with content
            init_repo = Repo.init(bare_repo_path, bare=True)
            
            # Create a temporary clone to add content
            temp_clone_path = os.path.join(temp_dir, 'temp-clone')
            clone = Repo.clone_from(f'file://{bare_repo_path}', temp_clone_path)
            
            test_file = os.path.join(temp_clone_path, 'test.txt')
            with open(test_file, 'w') as f:
                f.write('Test')
            
            clone.index.add(['test.txt'])
            clone.index.commit('Initial commit')
            clone.remote('origin').push('master:master')
            
            shutil.rmtree(temp_clone_path)
            
            # Create GitRepository
            repo = GitRepository.objects.create(
                name='nested-workdir-test',
                organisation=self.org,
                local_path=bare_repo_path,
                is_bare=True
            )
            
            # Verify the nested directory doesn't exist yet
            self.assertFalse(os.path.exists(workdir_path))
            
            # Create workdir
            repo.create_workdir(workdir_path, reference='master')
            
            # Verify the directory was created
            self.assertTrue(os.path.exists(workdir_path))
            self.assertTrue(os.path.isdir(workdir_path))
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    


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
            organisation=self.org
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
