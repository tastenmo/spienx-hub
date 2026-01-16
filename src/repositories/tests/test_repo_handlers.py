from django.test import TestCase
from unittest.mock import patch, MagicMock, PropertyMock
from repositories.repo_handlers import (
    RepositoryHandler,
    RepositoryContentHandler,
    RepositoryRefsHandler,
    FileEntry,
    CommitInfo,
    RefInfo
)
from git import InvalidGitRepositoryError, GitCommandError
from git.objects import Blob, Tree, Commit


class TestRepositoryHandler(TestCase):
    @patch('repositories.repo_handlers.Repo')
    def test_init_valid_repo(self, mock_repo):
        handler = RepositoryHandler('/path/to/repo')
        self.assertIsNotNone(handler.repo)
        mock_repo.assert_called_with('/path/to/repo')

    @patch('repositories.repo_handlers.Repo')
    def test_init_invalid_repo(self, mock_repo):
        mock_repo.side_effect = InvalidGitRepositoryError()
        handler = RepositoryHandler('/path/to/repo')
        with self.assertRaises(ValueError):
            _ = handler.repo

    @patch('repositories.repo_handlers.os.makedirs')
    @patch('repositories.repo_handlers.Repo')
    def test_create_workdir_bare(self, mock_repo, mock_makedirs):
        # Setup
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        
        # Test bare repo
        handler = RepositoryHandler('/path/to/repo', is_bare=True)
        handler.create_workdir('/workdir/path', 'main')
        
        mock_makedirs.assert_called_with('/workdir/path', exist_ok=True)
        mock_repo_instance.git.worktree.assert_called_with('add', '/workdir/path', 'main')

    @patch('repositories.repo_handlers.os.makedirs')
    @patch('repositories.repo_handlers.Repo')
    def test_create_workdir_non_bare(self, mock_repo, mock_makedirs):
        handler = RepositoryHandler('/path/to/repo', is_bare=False)
        result = handler.create_workdir('/workdir/path')
        
        mock_makedirs.assert_called_with('/workdir/path', exist_ok=True)
        self.assertIsNotNone(result)

    @patch('repositories.repo_handlers.Repo')
    def test_delete_workdir(self, mock_repo):
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        
        handler = RepositoryHandler('/path/to/repo')
        handler.delete_workdir('/workdir/path')
        
        mock_repo_instance.git.execute.assert_called_with(['worktree', 'remove', '/workdir/path'])
        
        # Test force
        handler.delete_workdir('/workdir/path', force=True)
        mock_repo_instance.git.execute.assert_called_with(['worktree', 'remove', '/workdir/path', '--force'])

    @patch('repositories.repo_handlers.Repo')
    def test_checkout_branch(self, mock_repo):
        mock_workdir = MagicMock()
        mock_head = MagicMock()
        mock_workdir.heads = {'main': mock_head}
        mock_repo.return_value = mock_workdir
        
        handler = RepositoryHandler('/path/to/repo')
        handler.checkout_branch('/workdir/path', 'main')
        
        mock_head.checkout.assert_called_once()

    @patch('repositories.repo_handlers.Repo')
    def test_checkout_commit(self, mock_repo):
        mock_workdir = MagicMock()
        mock_repo.return_value = mock_workdir
        
        handler = RepositoryHandler('/path/to/repo')
        handler.checkout_commit('/workdir/path', 'sha123')
        
        mock_workdir.git.checkout.assert_called_with('sha123')


class TestRepositoryContentHandler(TestCase):
    def setUp(self):
        self.mock_repo_patcher = patch('repositories.repo_handlers.Repo')
        self.mock_repo_cls = self.mock_repo_patcher.start()
        self.mock_repo = MagicMock()
        self.mock_repo_cls.return_value = self.mock_repo
        self.handler = RepositoryContentHandler('/path/to/repo')

    def tearDown(self):
        self.mock_repo_patcher.stop()

    def test_get_file_content(self):
        mock_commit = MagicMock()
        mock_blob = MagicMock(spec=Blob)
        mock_blob.data_stream.read.return_value = b'file content'
        
        # Setup commit -> tree traversal
        self.mock_repo.commit.return_value = mock_commit
        # Mock the path traversal via __truediv__
        mock_commit.tree.__truediv__.return_value = mock_blob
        
        content = self.handler.get_file_content('file.txt')
        self.assertEqual(content, 'file content')

    def test_get_file_content_not_a_file(self):
        mock_commit = MagicMock()
        mock_tree = MagicMock(spec=Tree) # Not a Blob
        
        self.mock_repo.commit.return_value = mock_commit
        mock_commit.tree.__truediv__.return_value = mock_tree
        
        with self.assertRaises(ValueError):
            self.handler.get_file_content('dir')

    def test_list_directory(self):
        mock_commit = MagicMock()
        mock_tree = MagicMock(spec=Tree)
        
        # Setup tree items
        item_blob = MagicMock(spec=Blob)
        item_blob.name = 'file.txt'
        item_blob.size = 100
        item_blob.mode = 33188
        item_blob.hexsha = 'sha1'
        
        item_tree = MagicMock(spec=Tree)
        item_tree.name = 'subdir'
        item_tree.mode = 16384
        item_tree.hexsha = 'sha2'
        
        mock_tree.__iter__.return_value = [item_blob, item_tree]
        self.mock_repo.commit.return_value = mock_commit
        mock_commit.tree = mock_tree
        
        entries = self.handler.list_directory()
        
        self.assertEqual(len(entries), 2)
        # file.txt and subdir. Sorted: blob then tree? 
        # lambda e: (e.type == 'blob', e.name) -> False < True, so tree comes first? 
        # Wait: type='tree' for tree, 'blob' for blob. 
        # (True, 'file.txt') vs (False, 'subdir'). False comes first in boolean sort? False=0, True=1.
        # So trees should be first.
        
        self.assertEqual(entries[0].name, 'subdir')
        self.assertEqual(entries[0].type, 'tree')
        self.assertEqual(entries[1].name, 'file.txt')
        self.assertEqual(entries[1].type, 'blob')

    def test_get_file_path(self):
        mock_commit = MagicMock()
        mock_blob = MagicMock(spec=Blob)
        mock_blob.data_stream.read.return_value = b'content'
        
        self.mock_repo.commit.return_value = mock_commit
        mock_commit.tree.__truediv__.return_value = mock_blob
        
        content = self.handler.get_file_path('file.txt')
        self.assertEqual(content, 'content')

    def test_get_file_path_missing(self):
        self.mock_repo.commit.side_effect = ValueError("Missing")
        result = self.handler.get_file_path('missing.txt')
        self.assertIsNone(result)

    def test_get_tree(self):
        mock_commit = MagicMock()
        mock_tree = MagicMock(spec=Tree)
        self.mock_repo.commit.return_value = mock_commit
        mock_commit.tree.__truediv__.return_value = mock_tree
        
        tree = self.handler.get_tree(path='subdir')
        self.assertEqual(tree, mock_tree)

    def test_get_blob(self):
        mock_commit = MagicMock()
        mock_blob = MagicMock(spec=Blob)
        self.mock_repo.commit.return_value = mock_commit
        mock_commit.tree.__truediv__.return_value = mock_blob
        
        blob = self.handler.get_blob(path='file.txt')
        self.assertEqual(blob, mock_blob)


class TestRepositoryRefsHandler(TestCase):
    def setUp(self):
        self.mock_repo_patcher = patch('repositories.repo_handlers.Repo')
        self.mock_repo_cls = self.mock_repo_patcher.start()
        self.mock_repo = MagicMock()
        self.mock_repo_cls.return_value = self.mock_repo
        self.handler = RepositoryRefsHandler('/path/to/repo')

    def tearDown(self):
        self.mock_repo_patcher.stop()

    def test_list_branches(self):
        b1 = MagicMock()
        b1.name = 'main'
        b1.commit.hexsha = 'sha1'
        
        b2 = MagicMock()
        b2.name = 'dev'
        b2.commit.hexsha = 'sha2'
        
        self.mock_repo.heads = [b1, b2]
        
        branches = self.handler.list_branches()
        self.assertEqual(len(branches), 2)
        # Sorted by name
        self.assertEqual(branches[0].name, 'dev')
        self.assertEqual(branches[1].name, 'main')

    def test_list_tags(self):
        t1 = MagicMock()
        t1.name = 'v1.0'
        t1.commit.hexsha = 'sha1'
        t1.tag = None
        
        self.mock_repo.tags = [t1]
        
        tags = self.handler.list_tags()
        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0].name, 'v1.0')

    def test_get_commits(self):
        c1 = MagicMock(spec=Commit)
        c1.hexsha = 'sha1'
        c1.author.name = 'Author'
        c1.author.email = 'auth@test.com'
        c1.committer.name = 'Committer'
        c1.committer.email = 'comm@test.com'
        c1.message = 'Initial commit'
        c1.committed_date = 100
        c1.authored_date = 100
        c1.parents = []
        
        self.mock_repo.iter_commits.return_value = [c1]
        
        commits = self.handler.get_commits()
        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0].sha, 'sha1')
        self.assertEqual(commits[0].message, 'Initial commit')

    def test_get_branch_info(self):
        mock_branch = MagicMock()
        mock_branch.name = 'main'
        mock_branch.commit.hexsha = 'sha1'
        self.mock_repo.heads = {'main': mock_branch}

        info = self.handler.get_branch_info('main')
        self.assertEqual(info.name, 'main')
        self.assertEqual(info.commit_sha, 'sha1')

    def test_get_tag_info(self):
        mock_tag = MagicMock()
        mock_tag.name = 'v1'
        mock_tag.commit.hexsha = 'sha1'
        mock_tag.tag.message = 'release'
        self.mock_repo.tags = {'v1': mock_tag}

        info = self.handler.get_tag_info('v1')
        self.assertEqual(info.name, 'v1')
        self.assertEqual(info.message, 'release')

    def test_get_commit_details(self):
        mock_commit = MagicMock(spec=Commit)
        mock_commit.hexsha = 'sha1'
        mock_commit.message = 'msg'
        mock_commit.author.name = 'A'
        mock_commit.author.email = 'a@e.com'
        mock_commit.committer.name = 'C'
        mock_commit.committer.email = 'c@e.com'
        mock_commit.parents = []
        
        self.mock_repo.commit.return_value = mock_commit
        
        info = self.handler.get_commit_details('sha1')
        self.assertEqual(info.sha, 'sha1')

