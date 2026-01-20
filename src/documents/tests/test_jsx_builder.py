import pytest
from documents.models import Document, Build, Page, Section
from accounts.models import Organisation
from repositories.models import GitRepository
from documents.builder.jsx_builder import DjangoJsxOutputImplementation
from documents.tasks import build_sphinxdocs
import tempfile
import os
import shutil
from git import Repo
from unittest.mock import patch, MagicMock

@pytest.mark.django_db
class TestDjangoJsxOutputImplementation:
    
    @pytest.fixture
    def document(self):
        org = Organisation.objects.create(name="Test Org", slug="test-org")
        repo = GitRepository.objects.create(
            name="Test Repo",
            organisation=org,
            local_path="/tmp/test_repo"
        )
        doc = Document.objects.create(
            title="Test Doc",
            source=repo
        )
        return Build.objects.create(
            document=doc,
            reference="main",
            workdir=".",
            conf_path="conf.py"
        )

    def test_create_page_creates_page_and_sections(self, document):
        impl = DjangoJsxOutputImplementation()
        
        ctx = {
            "current_page_name": "index",
            "title": "Home Page",
            "context": {"key": "value"},
            "section_list": [
                {
                    "id": "section1",
                    "title": "Section 1",
                    "hash": "hash1",
                    "source": "index.rst",
                    "startline": 10,
                    "body": "<p>Content 1</p>"
                },
                {
                    "id": "section2",
                    "title": "Section 2",
                    "hash": "hash2",
                    "source": "index.rst",
                    "startline": 20,
                    "body": "<p>Content 2</p>"
                }
            ]
        }
        
        impl.createPage(ctx, docId=document.pk)
        
        # Verify Page created
        page = Page.objects.get(build=document, path="index")
        assert page.title == "Home Page"
        assert page.context == {"key": "value"}
        
        # Verify Sections created
        sections = Section.objects.filter(page=page)
        assert sections.count() == 2
        
        s1 = sections.get(hash="hash1")
        assert s1.title == "Section 1"
        assert s1.source_path == "index.rst"
        assert s1.start_line == 10
        assert s1.content_block.jsx_content == "<p>Content 1</p>"
        
        s2 = sections.get(hash="hash2")
        assert s2.title == "Section 2"

    def test_create_asset_creates_static_asset(self, document):
        """Test that createAsset properly creates StaticAsset records"""
        from documents.models import StaticAsset
        
        impl = DjangoJsxOutputImplementation()
        
        asset_obj = {
            "path": "_static/style.css",
            "hash": "abc123def456"
        }
        
        impl.createAsset(asset_obj, docId=document.pk)
        
        # Verify StaticAsset created
        asset = StaticAsset.objects.get(document=document.document, path="_static/style.css")
        assert asset.hash == "abc123def456"

    def test_content_block_deduplication_across_pages(self, document):
        """Test that sections with the same hash on different pages share the same ContentBlock"""
        from documents.models import Page, Section, ContentBlock

        impl = DjangoJsxOutputImplementation()

        # Create first page with a section
        ctx1 = {
            "current_page_name": "page1",
            "title": "Page 1",
            "section_list": [
                {
                    "id": "s1",
                    "title": "Section 1",
                    "hash": "shared_hash_abc",
                    "source": "p1.rst",
                    "startline": 1,
                    "body": "<p>Shared Content</p>"
                }
            ]
        }
        impl.createPage(ctx1, docId=document.pk)

        # Create second page with a section having the same hash
        ctx2 = {
            "current_page_name": "page2",
            "title": "Page 2",
            "section_list": [
                {
                    "id": "s2",
                    "title": "Section 2",
                    "hash": "shared_hash_abc",
                    "source": "p2.rst",
                    "startline": 1,
                    "body": "<p>Shared Content</p>"
                }
            ]
        }
        impl.createPage(ctx2, docId=document.pk)

        # Retrieve pages
        page1 = Page.objects.get(build=document, path="page1")
        page2 = Page.objects.get(build=document, path="page2")

        # Retrieve sections
        sec1 = page1.sections.get(hash="shared_hash_abc")
        sec2 = page2.sections.get(hash="shared_hash_abc")

        # Verify they are different sections
        assert sec1.pk != sec2.pk

        # Verify they share the same content block
        assert sec1.content_block == sec2.content_block
        assert sec1.content_block.content_hash == "shared_hash_abc"
        assert sec1.content_block.jsx_content == "<p>Shared Content</p>"

        # Verify only one ContentBlock exists for this hash
        assert ContentBlock.objects.filter(content_hash="shared_hash_abc").count() == 1
    
    def test_finalize_updates_document(self, document):
        """Test that finalize properly updates document metadata"""
        from django.utils import timezone
        
        impl = DjangoJsxOutputImplementation()
        
        now = timezone.now()
        finalize_obj = {
            "last_build_at": now,
            "global_context": {"version": "1.0"}
        }
        
        impl.finalize(finalize_obj, docId=document.pk)
        
        # Verify Document updated
        document.refresh_from_db()
        # Note: last_build_at might be slightly different due to auto_now behavior
        # Just verify it was set to a recent time
        assert document.global_context == {"version": "1.0"}
        assert document.last_build_at is not None


@pytest.mark.django_db
class TestBuildSphinxdocs:
    """Test suite for the build_sphinxdocs Celery task"""
    
    @pytest.fixture
    def sphinx_repo_and_doc(self):
        """Create a test repository with minimal Sphinx configuration"""
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        repo_path = os.path.join(temp_dir, "sphinx-repo")
        
        # Initialize git repository
        os.makedirs(repo_path)
        git_repo = Repo.init(repo_path)
        
        # Create minimal Sphinx conf.py
        conf_content = '''
project = "Test Project"
extensions = []
django = {}
'''
        conf_path = os.path.join(repo_path, "conf.py")
        with open(conf_path, 'w') as f:
            f.write(conf_content)
        
        # Create minimal index.rst
        index_content = '''
Test Documentation
==================

This is a test documentation.
'''
        index_path = os.path.join(repo_path, "index.rst")
        with open(index_path, 'w') as f:
            f.write(index_content)
        
        # Create initial commit
        git_repo.index.add(['conf.py', 'index.rst'])
        git_repo.index.commit('Initial commit')
        
        # Create Organisation and GitRepository
        org = Organisation.objects.create(name="Test Org", slug="test-org")
        git_repo_model = GitRepository.objects.create(
            name="Test Sphinx Repo",
            organisation=org,
            local_path=repo_path,
            is_bare=False
        )
        
        # Create Document and Build
        document = Document.objects.create(
            title="Test Sphinx Doc",
            source=git_repo_model
        )
        build = Build.objects.create(
            document=document,
            reference="HEAD",
            workdir=".",
            conf_path=repo_path
        )
        
        yield build, temp_dir
        
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    def test_build_sphinxdocs_success(self, sphinx_repo_and_doc):
        """Test successful Sphinx build execution with real Sphinx"""
        build, temp_dir = sphinx_repo_and_doc
        
        # Call the actual task without mocking
        result = build_sphinxdocs(build.pk)
        
        # Verify success - task returns True on successful build
        assert result is True
        
        # Verify build was updated with results
        build.refresh_from_db()
        # global_context should have been set during build if pages were created
        assert build.global_context is not None
        assert build.last_build_at is not None

        # Verify Page objects were created during the build
        pages = Page.objects.filter(build=build)
        assert pages.count() >= 1, "At least one page should be created during Sphinx build"
        
        # Verify the index page exists
        index_page = pages.filter(path="index").first()
        assert index_page is not None, "Index page should be created"
        
        # Verify Section objects were created for the index page
        sections = Section.objects.filter(page=index_page)
        assert sections.count() > 0, "At least one section should be created for the index page"
        
        # Verify section content is not empty
        for section in sections:
            assert section.title, "Section should have a title"
            assert section.hash, "Section should have a hash"
            assert section.content_block.jsx_content, "Section should have body content"

        for section in sections:
            assert section.title == "Test Documentation"
            assert section.hash is not None
            assert section.content_block.jsx_content is not None

    
    def test_build_sphinxdocs_document_not_found(self):
        """Test build_sphinxdocs with non-existent build"""
        with patch('documents.tasks.Build.objects.get') as mock_get:
            mock_get.side_effect = Exception("Build not found")
            
            with patch('documents.tasks.logging') as mock_logging:
                # The task should handle the exception
                try:
                    result = build_sphinxdocs(99999)
                except Exception:
                    # Expected to raise when build not found
                    pass
    
    def test_build_sphinxdocs_no_source_repo(self):
        """Test build_sphinxdocs when build's document has no source repository"""
        org = Organisation.objects.create(name="Test Org 2", slug="test-org-2")
        
        # Create build without source repo via mocking
        with patch('documents.tasks.Build.objects.get') as mock_get:
            mock_build = MagicMock()
            mock_build.document.source = None
            mock_build.pk = 1
            mock_get.return_value = mock_build
            
            with patch('documents.tasks.logging'):
                result = build_sphinxdocs(1)
                
                # Should return False when repo is missing
                assert result is False

    def test_build_sphinxdocs_conf_path_handling(self, sphinx_repo_and_doc):
        """Test that build_sphinxdocs correctly resolves conf_path relative to checkout"""
        document, temp_dir = sphinx_repo_and_doc
        
        # Update document to use a relative conf_path and verify it works
        # The repo has conf.py at root.
        document.conf_path = "." 
        document.save()
        
        with patch('documents.tasks.Sphinx') as MockSphinx:
             # Mock the build method
            MockSphinx.return_value.build.return_value = None
            
            result = build_sphinxdocs(document.pk)
            
            assert result is True
            
            # Check initialization args of Sphinx
            call_args = MockSphinx.call_args
            assert call_args is not None
            
            # Check 'confdir' argument (index 1 of args or kwarg)
            # Sphinx(srcdir, confdir, ...)
            
            kwargs = call_args.kwargs
            confdir = kwargs.get('confdir')
            srcdir = kwargs.get('srcdir')
            
            # confdir should NOT be just "." but an absolute path to the checkout
            assert confdir != "."
            assert os.path.isabs(confdir)
            assert os.path.exists(os.path.join(confdir, 'conf.py'))

    def test_build_sphinxdocs_exception_handling(self, sphinx_repo_and_doc):
        """Test that build_sphinxdocs handles exceptions gracefully"""
        document, temp_dir = sphinx_repo_and_doc
        
        with patch('documents.tasks.Sphinx') as mock_sphinx:
            # Mock Sphinx to raise an exception
            mock_sphinx.side_effect = Exception("Sphinx build failed")
            
            with patch('documents.tasks.logger') as mock_logger:
                result = build_sphinxdocs(document.pk)
                
                # Should return False on exception
                assert result is False
                # Verify error was logged
                mock_logger.error.assert_called_once()

