"""
Handler classes for Git repository operations.
Provides abstraction over GitPython for working with bare and non-bare repositories.
"""

import os
import shutil
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple

from git import Repo, InvalidGitRepositoryError, NoSuchPathError, GitCommandError
from git.objects import Commit, Tree, Blob


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class FileEntry:
    """Represents a file or directory in a repository tree"""
    name: str
    path: str
    type: str  # 'blob' or 'tree'
    size: Optional[int] = None  # Size in bytes for blobs
    mode: Optional[int] = None  # File mode (e.g., 33188 for regular file)
    sha: Optional[str] = None   # Git object SHA


@dataclass
class CommitInfo:
    """Represents commit metadata"""
    sha: str
    author_name: str
    author_email: str
    committer_name: str
    committer_email: str
    message: str
    summary: str  # First line of message
    committed_date: int  # Unix timestamp
    authored_date: int  # Unix timestamp
    parents: List[str]  # Parent commit SHAs


@dataclass
class RefInfo:
    """Represents a branch or tag reference"""
    name: str
    type: str  # 'branch' or 'tag'
    commit_sha: str
    message: Optional[str] = None  # For annotated tags


# ============================================================================
# REPOSITORY HANDLER
# ============================================================================

class RepositoryHandler:
    """Handles worktree and checkout operations for repositories"""

    def __init__(self, repo_path: str, is_bare: bool = True):
        """
        Initialize the handler.
        
        Args:
            repo_path: Path to the git repository
            is_bare: Whether the repository is bare
        """
        self.repo_path = repo_path
        self.is_bare = is_bare
        self._repo = None

    @property
    def repo(self) -> Repo:
        """Lazy-load and cache the GitPython Repo object"""
        if self._repo is None:
            try:
                self._repo = Repo(self.repo_path)
            except InvalidGitRepositoryError as e:
                raise ValueError(f"Invalid git repository at {self.repo_path}: {str(e)}")
        return self._repo

    def create_workdir(self, path: str, reference: str = "HEAD") -> Repo:
        """
        Create a working directory (worktree) from this repository.
        
        Args:
            path: Target path for the working directory
            reference: Branch, tag, or commit to checkout (default: HEAD)
            
        Returns:
            GitPython Repo object for the worktree
            
        Raises:
            ValueError: If the repository is invalid or operation fails
        """
        os.makedirs(path, exist_ok=True)

        if self.is_bare:
            try:
                self.repo.git.worktree('add', path, reference)
                return Repo(path)
            except (InvalidGitRepositoryError, NoSuchPathError, GitCommandError) as e:
                raise ValueError(f"Failed to create worktree: {str(e)}")
        else:
            return Repo(self.repo_path)

    def delete_workdir(self, path: str, force: bool = False) -> bool:
        """
        Delete a worktree created with create_workdir.
        
        Args:
            path: Path to the worktree
            force: Force removal even if there are uncommitted changes
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If operation fails
        """
        try:
            cmd_args = ['worktree', 'remove', path]
            if force:
                cmd_args.append('--force')
            self.repo.git.execute(cmd_args)
            return True
        except GitCommandError as e:
            raise ValueError(f"Failed to delete worktree: {str(e)}")

    def checkout_branch(self, workdir_path: str, branch: str) -> bool:
        """
        Checkout a branch in a worktree.
        
        Args:
            workdir_path: Path to the worktree
            branch: Branch name to checkout
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If operation fails
        """
        try:
            workdir = Repo(workdir_path)
            workdir.heads[branch].checkout()
            return True
        except (IndexError, GitCommandError) as e:
            raise ValueError(f"Failed to checkout branch '{branch}': {str(e)}")

    def checkout_commit(self, workdir_path: str, commit_sha: str) -> bool:
        """
        Checkout a specific commit in a worktree (detached HEAD).
        
        Args:
            workdir_path: Path to the worktree
            commit_sha: Commit SHA to checkout
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If operation fails
        """
        try:
            workdir = Repo(workdir_path)
            workdir.git.checkout(commit_sha)
            return True
        except GitCommandError as e:
            raise ValueError(f"Failed to checkout commit '{commit_sha}': {str(e)}")


# ============================================================================
# REPOSITORY CONTENT HANDLER
# ============================================================================

class RepositoryContentHandler:
    """Handles browsing and retrieving content from repositories"""

    def __init__(self, repo_path: str):
        """
        Initialize the handler.
        
        Args:
            repo_path: Path to the git repository
        """
        self.repo_path = repo_path
        self._repo = None

    @property
    def repo(self) -> Repo:
        """Lazy-load and cache the GitPython Repo object"""
        if self._repo is None:
            try:
                self._repo = Repo(self.repo_path)
            except InvalidGitRepositoryError as e:
                raise ValueError(f"Invalid git repository at {self.repo_path}: {str(e)}")
        return self._repo

    def get_file_content(self, path: str, reference: str = "HEAD") -> str:
        """
        Get the contents of a file from the repository.
        
        Args:
            path: File path relative to repository root
            reference: Branch, tag, or commit (default: HEAD)
            
        Returns:
            File content as string
            
        Raises:
            ValueError: If file doesn't exist or operation fails
        """
        try:
            commit = self.repo.commit(reference)
            blob = commit.tree / path
            if not isinstance(blob, Blob):
                raise ValueError(f"'{path}' is not a file")
            return blob.data_stream.read().decode('utf-8', errors='replace')
        except (GitCommandError, AttributeError, KeyError) as e:
            raise ValueError(f"Failed to get file '{path}': {str(e)}")

    def list_directory(self, path: str = "", reference: str = "HEAD") -> List[FileEntry]:
        """
        List contents of a directory in the repository.
        
        Args:
            path: Directory path relative to repository root (empty string for root)
            reference: Branch, tag, or commit (default: HEAD)
            
        Returns:
            List of FileEntry objects
            
        Raises:
            ValueError: If directory doesn't exist or operation fails
        """
        try:
            commit = self.repo.commit(reference)
            
            if path:
                tree = commit.tree / path
            else:
                tree = commit.tree
            
            if not isinstance(tree, Tree):
                raise ValueError(f"'{path}' is not a directory")
            
            entries = []
            for item in tree:
                entry = FileEntry(
                    name=item.name,
                    path=f"{path}/{item.name}" if path else item.name,
                    type='tree' if isinstance(item, Tree) else 'blob',
                    size=item.size if isinstance(item, Blob) else None,
                    mode=item.mode,
                    sha=item.hexsha,
                )
                entries.append(entry)
            
            return sorted(entries, key=lambda e: (e.type == 'blob', e.name))
        except (GitCommandError, AttributeError, KeyError) as e:
            raise ValueError(f"Failed to list directory '{path}': {str(e)}")

    def get_file_path(self, file_path: str, reference: str = "HEAD") -> Optional[str]:
        """
        Get the full content of a file by path, with validation.
        
        Args:
            file_path: Path to file relative to repository root
            reference: Branch, tag, or commit (default: HEAD)
            
        Returns:
            File content as string, or None if not found
            
        Raises:
            ValueError: If operation fails
        """
        try:
            return self.get_file_content(file_path, reference)
        except ValueError:
            return None

    def get_tree(self, reference: str = "HEAD", path: str = "") -> Tree:
        """
        Get the Git tree object at the specified reference and path.
        
        Args:
            reference: Branch, tag, or commit (default: HEAD)
            path: Path within the tree (empty string for root)
            
        Returns:
            GitPython Tree object
            
        Raises:
            ValueError: If operation fails
        """
        try:
            commit = self.repo.commit(reference)
            if path:
                return commit.tree / path
            return commit.tree
        except (GitCommandError, AttributeError, KeyError) as e:
            raise ValueError(f"Failed to get tree at '{path}': {str(e)}")

    def get_blob(self, reference: str = "HEAD", path: str = "") -> Blob:
        """
        Get the Git blob object at the specified reference and path.
        
        Args:
            reference: Branch, tag, or commit (default: HEAD)
            path: Path to the blob
            
        Returns:
            GitPython Blob object
            
        Raises:
            ValueError: If operation fails
        """
        try:
            commit = self.repo.commit(reference)
            blob = commit.tree / path
            if not isinstance(blob, Blob):
                raise ValueError(f"'{path}' is not a blob")
            return blob
        except (GitCommandError, AttributeError, KeyError) as e:
            raise ValueError(f"Failed to get blob at '{path}': {str(e)}")

    def get_file_size(self, path: str, reference: str = "HEAD") -> int:
        """
        Get the size of a file in bytes.
        
        Args:
            path: File path relative to repository root
            reference: Branch, tag, or commit (default: HEAD)
            
        Returns:
            File size in bytes
            
        Raises:
            ValueError: If file doesn't exist or operation fails
        """
        blob = self.get_blob(reference, path)
        return blob.size


# ============================================================================
# REPOSITORY REFS HANDLER
# ============================================================================

class RepositoryRefsHandler:
    """Handles branch, tag, and commit operations for repositories"""

    def __init__(self, repo_path: str):
        """
        Initialize the handler.
        
        Args:
            repo_path: Path to the git repository
        """
        self.repo_path = repo_path
        self._repo = None

    @property
    def repo(self) -> Repo:
        """Lazy-load and cache the GitPython Repo object"""
        if self._repo is None:
            try:
                self._repo = Repo(self.repo_path)
            except InvalidGitRepositoryError as e:
                raise ValueError(f"Invalid git repository at {self.repo_path}: {str(e)}")
        return self._repo

    def list_branches(self) -> List[RefInfo]:
        """
        List all branches in the repository.
        
        Returns:
            List of RefInfo objects for branches
            
        Raises:
            ValueError: If operation fails
        """
        try:
            refs = []
            for branch in self.repo.heads:
                refs.append(RefInfo(
                    name=branch.name,
                    type='branch',
                    commit_sha=branch.commit.hexsha,
                ))
            return sorted(refs, key=lambda r: r.name)
        except GitCommandError as e:
            raise ValueError(f"Failed to list branches: {str(e)}")

    def list_tags(self) -> List[RefInfo]:
        """
        List all tags in the repository.
        
        Returns:
            List of RefInfo objects for tags
            
        Raises:
            ValueError: If operation fails
        """
        try:
            refs = []
            for tag in self.repo.tags:
                commit_sha = tag.commit.hexsha if isinstance(tag.commit, Commit) else str(tag.commit)
                refs.append(RefInfo(
                    name=tag.name,
                    type='tag',
                    commit_sha=commit_sha,
                    message=tag.tag.message if tag.tag else None,
                ))
            return sorted(refs, key=lambda r: r.name)
        except GitCommandError as e:
            raise ValueError(f"Failed to list tags: {str(e)}")

    def get_branch_info(self, branch_name: str) -> RefInfo:
        """
        Get information about a specific branch.
        
        Args:
            branch_name: Name of the branch
            
        Returns:
            RefInfo object for the branch
            
        Raises:
            ValueError: If branch doesn't exist or operation fails
        """
        try:
            branch = self.repo.heads[branch_name]
            return RefInfo(
                name=branch.name,
                type='branch',
                commit_sha=branch.commit.hexsha,
            )
        except (IndexError, GitCommandError) as e:
            raise ValueError(f"Branch '{branch_name}' not found: {str(e)}")

    def get_tag_info(self, tag_name: str) -> RefInfo:
        """
        Get information about a specific tag.
        
        Args:
            tag_name: Name of the tag
            
        Returns:
            RefInfo object for the tag
            
        Raises:
            ValueError: If tag doesn't exist or operation fails
        """
        try:
            tag = self.repo.tags[tag_name]
            commit_sha = tag.commit.hexsha if isinstance(tag.commit, Commit) else str(tag.commit)
            return RefInfo(
                name=tag.name,
                type='tag',
                commit_sha=commit_sha,
                message=tag.tag.message if tag.tag else None,
            )
        except (IndexError, GitCommandError) as e:
            raise ValueError(f"Tag '{tag_name}' not found: {str(e)}")

    def get_commits(
        self,
        reference: str = "HEAD",
        limit: int = 50,
        skip: int = 0,
    ) -> List[CommitInfo]:
        """
        Get commit history for a reference with pagination.
        
        Args:
            reference: Branch, tag, or commit (default: HEAD)
            limit: Maximum number of commits to return (default: 50)
            skip: Number of commits to skip (default: 0)
            
        Returns:
            List of CommitInfo objects
            
        Raises:
            ValueError: If operation fails
        """
        try:
            commits = []
            for i, commit in enumerate(self.repo.iter_commits(reference)):
                if i < skip:
                    continue
                if i >= skip + limit:
                    break
                
                commits.append(self._commit_to_info(commit))
            
            return commits
        except GitCommandError as e:
            raise ValueError(f"Failed to get commits for '{reference}': {str(e)}")

    def get_commit_details(self, commit_sha: str) -> CommitInfo:
        """
        Get detailed information about a specific commit.
        
        Args:
            commit_sha: Commit SHA
            
        Returns:
            CommitInfo object
            
        Raises:
            ValueError: If commit doesn't exist or operation fails
        """
        try:
            commit = self.repo.commit(commit_sha)
            return self._commit_to_info(commit)
        except (GitCommandError, ValueError) as e:
            raise ValueError(f"Commit '{commit_sha}' not found: {str(e)}")

    def _commit_to_info(self, commit: Commit) -> CommitInfo:
        """Convert a GitPython Commit to CommitInfo"""
        message = commit.message or ""
        summary = message.split('\n')[0]
        
        return CommitInfo(
            sha=commit.hexsha,
            author_name=commit.author.name,
            author_email=commit.author.email,
            committer_name=commit.committer.name,
            committer_email=commit.committer.email,
            message=message,
            summary=summary,
            committed_date=commit.committed_date,
            authored_date=commit.authored_date,
            parents=[p.hexsha for p in commit.parents],
        )

    def get_branch_commits(
        self,
        branch_name: str,
        limit: int = 50,
        skip: int = 0,
    ) -> List[CommitInfo]:
        """
        Get commits for a specific branch.
        
        Args:
            branch_name: Name of the branch
            limit: Maximum number of commits to return
            skip: Number of commits to skip
            
        Returns:
            List of CommitInfo objects
            
        Raises:
            ValueError: If operation fails
        """
        return self.get_commits(branch_name, limit, skip)

    def get_tag_commits(
        self,
        tag_name: str,
        limit: int = 50,
        skip: int = 0,
    ) -> List[CommitInfo]:
        """
        Get commits reachable from a specific tag.
        
        Args:
            tag_name: Name of the tag
            limit: Maximum number of commits to return
            skip: Number of commits to skip
            
        Returns:
            List of CommitInfo objects
            
        Raises:
            ValueError: If operation fails
        """
        return self.get_commits(tag_name, limit, skip)
