import pytest
import os
import shutil
import tempfile
from types import SimpleNamespace
from git import Repo
from repositories.models import GitRepository
from repositories.services import GitRepositoryService
from accounts.models import Organisation
from django.contrib.auth.models import User

@pytest.mark.django_db(transaction=True)
class TestGitRepositoryServiceActions:
    
    @pytest.fixture
    def repo_setup(self):
        # Create user and org
        user = User.objects.create_user(username='testuser', email='test@example.com', password='password')
        org = Organisation.objects.create(name="Test Org", slug="test-org")
        
        # Create temp git repo
        temp_dir = tempfile.mkdtemp()
        repo_path = os.path.join(temp_dir, "test-repo")
        os.makedirs(repo_path)
        
        # Init repo
        r = Repo.init(repo_path)
        
        # Config needed for commit
        r.config_writer().set_value("user", "name", "Test User").release()
        r.config_writer().set_value("user", "email", "test@example.com").release()
        
        # Create a file
        file_path = os.path.join(repo_path, "test.txt")
        with open(file_path, "w") as f:
            f.write("content")
            
        r.index.add(["test.txt"])
        r.index.commit("Initial commit")
        
        # Create a branch
        try:
            r.create_head('feature-branch')
        except Exception:
            # If main/master confusion, just ensure we have HEAD committed
            pass

        # Create a tag
        r.create_tag('v1.0')
        
        # Create a directory with a file
        dir_path = os.path.join(repo_path, "subdir")
        os.makedirs(dir_path)
        sub_file_path = os.path.join(dir_path, "sub.txt")
        with open(sub_file_path, "w") as f:
            f.write("sub content")
        
        r.index.add(["subdir/sub.txt"])
        r.index.commit("Add subdir")
        
        # DB Model
        git_repo = GitRepository.objects.create(
            name="Test Repo",
            organisation=org,
            local_path=repo_path,
            is_bare=False
        )
        
        yield git_repo, repo_path
        
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_list_refs(self, repo_setup):
        git_repo, _ = repo_setup
        service = GitRepositoryService()
        
        # Mock request
        request = SimpleNamespace(repository_id=git_repo.id)
        
        # Call action
        response = await service.ListRefs(request, None)
        
        # Verify
        branches = response.branches.split('\n')
        tags = response.tags.split('\n')
        
        # Check standard branch (master or main)
        assert any(b in branches for b in ['master', 'main'])
        # Check tag
        assert 'v1.0' in tags

    @pytest.mark.asyncio
    async def test_list_tree_root(self, repo_setup):
        git_repo, _ = repo_setup
        service = GitRepositoryService()
        
        request = SimpleNamespace(
            repository_id=git_repo.id,
            reference="HEAD",
            path=""
        )
        
        response = await service.ListTree(request, None)
        
        directories = response.directories.split('\n')
        files = response.files.split('\n')
        
        assert 'subdir' in directories
        assert 'test.txt' in files

    @pytest.mark.asyncio
    async def test_list_tree_subdir(self, repo_setup):
        git_repo, _ = repo_setup
        service = GitRepositoryService()
        
        request = SimpleNamespace(
            repository_id=git_repo.id,
            reference="HEAD",
            path="subdir"
        )
        
        response = await service.ListTree(request, None)
        
        directories = response.directories.split('\n') if response.directories else []
        files = response.files.split('\n')
        
        assert 'subdir/sub.txt' in files
