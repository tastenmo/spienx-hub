# Repository Handlers Documentation

The repository handlers provide a clean abstraction for working with Git repositories in Django. They are located in `repositories/repo_handlers.py`.

## Overview

Three main handler classes are provided:

### 1. RepositoryHandler
Handles worktree and checkout operations for creating working directories from bare repositories.

**Key Methods:**
- `create_workdir(path, reference)` - Create a working directory worktree
- `delete_workdir(path, force)` - Delete a worktree
- `checkout_branch(workdir_path, branch)` - Checkout a branch
- `checkout_commit(workdir_path, commit_sha)` - Checkout a specific commit

### 2. RepositoryContentHandler
Handles browsing and retrieving file/folder contents from repositories.

**Key Methods:**
- `get_file_content(path, reference)` - Get file contents
- `list_directory(path, reference)` - List directory contents
- `get_file_path(file_path, reference)` - Get file with validation
- `get_tree(reference, path)` - Get Git tree object
- `get_blob(reference, path)` - Get Git blob object
- `get_file_size(path, reference)` - Get file size in bytes

### 3. RepositoryRefsHandler
Handles branch, tag, and commit operations.

**Key Methods:**
- `list_branches()` - List all branches
- `list_tags()` - List all tags
- `get_branch_info(branch_name)` - Get branch details
- `get_tag_info(tag_name)` - Get tag details
- `get_commits(reference, limit, skip)` - Get commit history with pagination
- `get_commit_details(commit_sha)` - Get single commit details
- `get_branch_commits(branch_name, limit, skip)` - Get commits for branch
- `get_tag_commits(tag_name, limit, skip)` - Get commits for tag

## Usage from Django Models

The `GitRepository` model provides convenient factory methods:

```python
repo = GitRepository.objects.get(id=1)

# Get handlers
handler = repo.get_handler()
content_handler = repo.get_content_handler()
refs_handler = repo.get_refs_handler()

# Use handlers
handler.create_workdir('/tmp/workdir', 'main')
files = content_handler.list_directory('src')
commits = refs_handler.get_commits('main', limit=10)
```

## Data Classes

### FileEntry
Represents a file or directory in a repository:
- `name` - File/directory name
- `path` - Relative path from repository root
- `type` - 'blob' (file) or 'tree' (directory)
- `size` - Size in bytes (for blobs only)
- `mode` - File mode permissions
- `sha` - Git object SHA

### CommitInfo
Represents commit metadata:
- `sha` - Commit SHA
- `author_name`, `author_email` - Author information
- `committer_name`, `committer_email` - Committer information
- `message` - Full commit message
- `summary` - First line of message
- `committed_date`, `authored_date` - Unix timestamps
- `parents` - List of parent commit SHAs

### RefInfo
Represents a branch or tag:
- `name` - Branch/tag name
- `type` - 'branch' or 'tag'
- `commit_sha` - Commit this ref points to
- `message` - Tag message (for annotated tags)

## Error Handling

All handler methods raise `ValueError` with descriptive messages on failure:

```python
try:
    content_handler.get_file_content('missing.txt')
except ValueError as e:
    print(f"Error: {e}")
```

## Performance Considerations

- Handlers use lazy-loading and caching of the GitPython Repo object
- Large directory listings are not paginated by default (consider your use case)
- Commit history can be large; use `limit` and `skip` for pagination
- File content is read entirely into memory; be cautious with large files
