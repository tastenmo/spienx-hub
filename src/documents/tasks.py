import os
import shutil
import logging
from tempfile import mkdtemp
from os import path
from celery import shared_task
from sphinx.config import Config
from sphinx.application import Sphinx

from documents.models import Build
from repositories.repo_handlers import RepositoryHandler

logger = logging.getLogger(__name__)

@shared_task()
def build_sphinxdocs(build_id: int):
    """
    Celery task to build Sphinx documentation for a Build.
    """
    logging.debug("Starting Sphinx build for Build ID: %s", build_id)

    try:
        build = Build.objects.get(pk=build_id)
    except Build.DoesNotExist:
        logging.error("Build with ID %s not found.", build_id)
        return

    return run_sphinx_build(build)


def run_sphinx_build(build: Build):
    """
    Core logic to build Sphinx documentation.
    Separated from the task for easier testing and reuse.
    """
    source_repo = build.document.source
    if not source_repo:
        logging.error("Build with ID %s has no associated source repository.", build.pk)
        return False

    src_path = mkdtemp()
    
    try:
        # Use RepositoryHandler directly
        handler = source_repo.get_handler()
        repo = handler.create_workdir(path=src_path, reference=(build.reference if build.reference else "HEAD"))
        working_dir = repo.working_dir
        
        # Capture commit hash and generate version
        if repo and hasattr(repo, 'head') and hasattr(repo.head, 'commit'):
            build.commit_hash = repo.head.commit.hexsha
            
        try:
            from dunamai import Version
            version = Version.from_git(working_dir)
            build.version = version.serialize()
        except Exception as e:
            logger.warning(f"Could not generate version with dunamai: {e}")
            if build.commit_hash:
                 build.version = build.commit_hash[:7]

        build.save()

        build_dir = path.join(src_path, "_build", "djangojsx")
        os.makedirs(build_dir, exist_ok=True)

        try:
            logger.info(f"Docs build: {build}")
            
            # Resolve confdir relative to the repo working directory
            confdir = path.join(working_dir, build.conf_path)
            if confdir.endswith('conf.py'):
                confdir = path.dirname(confdir)
            logger.info(f"Conf dir: {confdir}")
            
            if not os.path.exists(confdir):
                logger.error(f"Configuration directory does not exist: {confdir}")
                return False

            # Read Sphinx config and extract extensions safely
            config = Config.read(confdir, {})
            try:
                extensions = getattr(config, 'extensions', []) or []
            except Exception:
                extensions = []
            # Register the builder module as an extension
            # Note: This refers to the module where DjangoJSXBuilder and setup() are defined
            extensions.append('documents.builder.jsx_builder')

            app = Sphinx(
                srcdir=confdir,
                confdir=confdir,
                outdir=build_dir,
                doctreedir=os.path.join(src_path, '_doctrees'),
                buildername='djangojsx',
                confoverrides={'extensions': extensions, 'django': {'docId': build.pk}},
                keep_going=True,
            )

            app.build()
            
            return True
        
        except Exception as e:
            logger.error(f"Error building docs for {build.pk}: {e}")
            return False
            
    finally:
        # Cleanup temp directory
        try:
            if os.path.exists(src_path):
                shutil.rmtree(src_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory {src_path}: {e}")
