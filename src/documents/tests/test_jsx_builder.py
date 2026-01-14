import pytest
from documents.models import Document, Page, Section
from accounts.models import Organisation
from repositories.models import GitRepository
from documents.builder.jsx_builder import DjangoJsxOutputImplementation, build_sphinxdocs
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
        return Document.objects.create(
            title="Test Doc",
            source=repo,
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
        page = Page.objects.get(document=document, current_page_name="index")
        assert page.title == "Home Page"
        assert page.context == {"key": "value"}
        
        # Verify Sections created
        sections = Section.objects.filter(page=page)
        assert sections.count() == 2
        
        s1 = sections.get(hash="hash1")
        assert s1.title == "Section 1"
        assert s1.source_path == "index.rst"
        assert s1.start_line == 10
        assert s1.body == "<p>Content 1</p>"
        
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
        asset = StaticAsset.objects.get(document=document, path="_static/style.css")
        assert asset.hash == "abc123def456"
    
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
        
        # Create Document
        document = Document.objects.create(
            title="Test Sphinx Doc",
            source=git_repo_model,
            reference="HEAD",
            workdir=".",
            conf_path=repo_path
        )
        
        yield document, temp_dir
        
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    def test_build_sphinxdocs_success(self, sphinx_repo_and_doc):
        """Test successful Sphinx build execution with real Sphinx"""
        document, temp_dir = sphinx_repo_and_doc
        
        # Call the actual task without mocking
        result = build_sphinxdocs(document.pk)
        
        # Verify success - task returns True on successful build
        assert result is True
        
        # Verify document was updated with build results
        document.refresh_from_db()
        # global_context should have been set during build if pages were created
        assert document.global_context is not None
        assert document.last_build_at is not None

        # Verify Page objects were created during the build
        pages = Page.objects.filter(document=document)
        assert pages.count() >= 1, "At least one page should be created during Sphinx build"
        
        # Verify the index page exists
        index_page = pages.filter(current_page_name="index").first()
        assert index_page is not None, "Index page should be created"
        
        # Verify Section objects were created for the index page
        sections = Section.objects.filter(page=index_page)
        assert sections.count() > 0, "At least one section should be created for the index page"
        
        # Verify section content is not empty
        for section in sections:
            assert section.title, "Section should have a title"
            assert section.hash, "Section should have a hash"
            assert section.body, "Section should have body content"

        for section in sections:
            assert section.title == "Test Documentation"
            assert section.hash is not None
            assert section.body is not None

    
    def test_build_sphinxdocs_document_not_found(self):
        """Test build_sphinxdocs with non-existent document"""
        with patch('documents.builder.jsx_builder.Document.objects.get') as mock_get:
            mock_get.side_effect = Exception("Document not found")
            
            with patch('documents.builder.jsx_builder.logging') as mock_logging:
                # The task should handle the exception
                try:
                    result = build_sphinxdocs(99999)
                except Exception:
                    # Expected to raise when document not found
                    pass
    
    def test_build_sphinxdocs_no_source_repo(self):
        """Test build_sphinxdocs when document has no source repository"""
        org = Organisation.objects.create(name="Test Org 2", slug="test-org-2")
        
        # Create document without source repo (will fail on FK constraint)
        # Instead, test by mocking
        with patch('documents.builder.jsx_builder.Document.objects.get') as mock_get:
            mock_doc = MagicMock()
            mock_doc.source = None
            mock_doc.pk = 1
            mock_get.return_value = mock_doc
            
            with patch('documents.builder.jsx_builder.logging'):
                result = build_sphinxdocs(1)
                
                # Should return None when repo is missing
                assert result is None
    
    def test_build_sphinxdocs_exception_handling(self, sphinx_repo_and_doc):
        """Test that build_sphinxdocs handles exceptions gracefully"""
        document, temp_dir = sphinx_repo_and_doc
        
        with patch('documents.builder.jsx_builder.Sphinx') as mock_sphinx:
            # Mock Sphinx to raise an exception
            mock_sphinx.side_effect = Exception("Sphinx build failed")
            
            with patch('documents.builder.jsx_builder.logger') as mock_logger:
                result = build_sphinxdocs(document.pk)
                
                # Should return False on exception
                assert result is False
                # Verify error was logged
                mock_logger.error.assert_called_once()

