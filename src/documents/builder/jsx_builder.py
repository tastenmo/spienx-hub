from __future__ import annotations

import hashlib
import os
import types
from os import path
from typing import TYPE_CHECKING, Any

import logging

logger = logging.getLogger(__name__)

from sphinx.application import Sphinx
from sphinx.builders.html import BuildInfo
from jsx_builder.builders import JSXBuilder, JsxOutputImplementation
from django.core.files import File
from documents.models import Build, Page, Section, StaticAsset, ContentBlock

class DjangoJsxOutputImplementation(JsxOutputImplementation):
    """Django ORM implementation wrapper for JSX output."""

    def dump(self, obj: Any, file: Any, *args: Any, **kwds: Any) -> None:
        pass

    def finalize(self, obj: Any, *args: Any, **kwds: Any) -> None:


        if kwds.get("docId"):
            build = Build.objects.get(pk=kwds["docId"])

            logging.debug("Finalizing Build for obj: %s ", build)

            logging.debug("Global context: %s ", obj)

            # If obj contains 'global_context', use it directly
            if isinstance(obj, dict) and "global_context" in obj:
                build.global_context = obj["global_context"]
            else:
                # Extract only JSON-serializable keys to avoid storing Sphinx objects
                safe_context = {}
                if isinstance(obj, dict):
                    # Keep only safe, serializable keys
                    safe_keys = [
                        'master_doc', 'root_doc', 'project', 'release', 'version',
                        'language', 'author', 'copyright', 'extensions', 'templates_path',
                        'source_suffix', 'exclude_patterns', 'html_theme', 'html_logo',
                        'toc_pages'
                    ]
                    for key in safe_keys:
                        if key in obj:
                            safe_context[key] = obj[key]
                build.global_context = safe_context
            build.last_build_at = obj.get("last_build_at")
            build.save()
        
    def createAsset(self, obj: Any, *args: Any, **kwds: Any) -> None:

        if kwds.get("docId"):
            build = Build.objects.get(pk=kwds["docId"])

            asset_path = obj.get("path", "")
            absolute_path = obj.get("absolute_path", "")
            hash_val = obj.get("hash", "")

            if not asset_path:
                return

            logging.debug("Creating StaticAsset for obj: %s ", asset_path)

            if not hash_val and absolute_path and path.exists(absolute_path):
                hash_val = self._sha1_file(absolute_path)

            asset, _ = StaticAsset.objects.get_or_create(
                document=build.document,
                path=asset_path,
                defaults={
                    'hash': hash_val,
                }
            )

            dirty_fields: list[str] = []

            if hash_val and asset.hash != hash_val:
                asset.hash = hash_val
                dirty_fields.append("hash")

            if absolute_path and path.exists(absolute_path):
                ext = path.splitext(obj.get("filename") or path.basename(absolute_path))[1].lower()
                if not ext:
                    ext = ".bin"
                filename = f"{hash_val}{ext}" if hash_val else (obj.get("filename") or path.basename(absolute_path))
                target_name = f"static_assets/{filename}"
                if asset.file.storage.exists(target_name):
                    asset.file.storage.delete(target_name)
                with open(absolute_path, "rb") as file_handle:
                    asset.file.save(filename, File(file_handle), save=False)
                dirty_fields.append("file")

            if dirty_fields:
                # Use set() to avoid duplicate fields when both hash and file changed.
                asset.save(update_fields=list(set(dirty_fields)))

    def _sha1_file(self, file_path: str) -> str:
        sha1 = hashlib.sha1()
        with open(file_path, "rb") as file_handle:
            for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
                sha1.update(chunk)
        return sha1.hexdigest()
    
    def createPage(self, obj: Any, *args: Any, **kwds: Any) -> types.NoneType:
        
        if kwds.get("docId"):
            build = Build.objects.get(pk=kwds["docId"])

            # Get page name from context - could be 'pagename' or 'current_page_name'
            page_name = obj.get("current_page_name") or obj.get("pagename", "")
            
            # Skip if no page name
            if not page_name:
                logging.debug("No page name found in context, skipping page creation")
                return

            # Use update_or_create to avoid duplicates
            page, created = Page.objects.update_or_create(
                build=build,
                path=page_name,
                defaults={
                    'title': obj.get("title", ""),
                    'context': obj.get("context", {}),
                    'jsx_content': obj.get("body", ""),
                }
            )

            if page:

                logging.debug("Created Page: %s ", page.path)

                # Create sections for the page
                sections = obj.get("section_list", [])
                sections_by_hash: dict[str, Section] = {}
                pending_parent_links: list[tuple[Section, str]] = []
                for section_data in sections:
                    hash_val = section_data.get("hash", "")
                    body = section_data.get("body", "")
                    
                    if not hash_val or not body:
                        continue

                    # Create or retrieve content block for the section
                    content_block, _ = ContentBlock.objects.get_or_create(
                        content_hash=hash_val,
                        defaults={
                            'jsx_content': body,
                        }
                    ) 

                    section, created = Section.objects.update_or_create(
                        page=page,
                        hash=hash_val, 
                        defaults={
                            'title': section_data.get("title", ""),
                            'sphinx_id': section_data.get("id", ""),
                            'source_path': section_data.get("source", ""),
                            'start_line': section_data.get("startline", 0) or 0,
                            'end_line': section_data.get("endline", 0) or 0,
                            'level': section_data.get("level", 1) or 1,
                            'order_index': section_data.get("order_index", 0) or 0,
                            'content_block': content_block,
                        }
                    )
                    sections_by_hash[hash_val] = section
                    pending_parent_links.append((section, section_data.get("parent_hash", "") or ""))

                for section, parent_hash in pending_parent_links:
                    parent_section = sections_by_hash.get(parent_hash) if parent_hash else None
                    if section.parent_section_id != (parent_section.id if parent_section else None):
                        section.parent_section = parent_section
                        section.save(update_fields=['parent_section'])

    def createSection(self, obj: Any, *args: Any, **kwds: Any) -> None:
        pass  # Implement section creation if needed

        
class DjangoJSXBuilder(JSXBuilder):
    """
    A Sphinx builder that outputs documentation using Django ORM.
    """

    name = 'djangojsx'
    epilog = 'You can now process the Django ORM entries.'

    implementation = DjangoJsxOutputImplementation()
    implementation_dumps_unicode = True
    additional_dump_args: tuple[Any] = ()
    globalcontext_filename = 'globalcontext.json'
    


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_builder(DjangoJSXBuilder)
    app.add_config_value('django', {}, 'html')
    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }




