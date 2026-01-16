import os
import shutil
import logging
from tempfile import mkdtemp
from os import path
from celery import shared_task
from sphinx.config import Config
from sphinx.application import Sphinx

from documents.models import Document
from repositories.repo_handlers import RepositoryHandler

logger = logging.getLogger(__name__)

@shared_task()
def build_sphinxdocs(document_id: int):
    """
    Celery task to build Sphinx documentation for a Document.
    """
    logging.debug("Starting Sphinx build for Document version ID: %s", document_id)

    try:
        doc = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        logging.error("Document with ID %s not found.", document_id)
        return

    return run_sphinx_build(doc)


def run_sphinx_build(doc: Document):
    """
    Core logic to build Sphinx documentation.
    Separated from the task for easier testing and reuse.
    """
    source_repo = doc.source
    if not source_repo:
        logging.error("Document with ID %s has no associated source repository.", doc.pk)
        return False

    src_path = mkdtemp()
    
    try:
        # Use RepositoryHandler directly
        handler = source_repo.get_handler()
        repo = handler.create_workdir(path=src_path, reference=(doc.reference if doc.reference else "HEAD"))
        working_dir = repo.working_dir

        build_dir = path.join(src_path, "_build", "djangojsx")
        os.makedirs(build_dir, exist_ok=True)

        try:
            logger.info(f"Docs version: {doc}")
            
            # Resolve confdir relative to the repo working directory
            confdir = path.join(working_dir, doc.conf_path)
            logger.info(f"Conf dir: {confdir}")
            
            if not os.path.exists(confdir):
                logger.error(f"Configuration directory does not exist: {confdir}")
                return False

            config = Config.read(confdir, {})

            extensions = config['extensions']
            # Register the builder module as an extension
            # Note: This refers to the module where DjangoJSXBuilder and setup() are defined
            extensions.append('documents.builder.jsx_builder')

            app = Sphinx(
                srcdir=confdir,
                confdir=confdir,
                outdir=build_dir,
                doctreedir=os.path.join(src_path, '_doctrees'),
                buildername='djangojsx',
                confoverrides={'extensions': extensions, 'django': {'docId': doc.pk}},
                keep_going=True,
            )

            app.build()
            
            return True
        
        except Exception as e:
            logger.error(f"Error building docs for {doc.pk}: {e}")
            return False
            
    finally:
        # Cleanup temp directory
        try:
            if os.path.exists(src_path):
                shutil.rmtree(src_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory {src_path}: {e}")
