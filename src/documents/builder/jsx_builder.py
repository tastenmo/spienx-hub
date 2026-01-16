from __future__ import annotations

import os
import types
from os import path
from typing import TYPE_CHECKING, Any

import logging

logger = logging.getLogger(__name__)

from sphinx.application import Sphinx
from sphinx.builders.html import BuildInfo
from jsx_builder.builders import JSXBuilder, JsxOutputImplementation
from documents.models import Document, Page, Section, StaticAsset, ContentBlock

class DjangoJsxOutputImplementation(JsxOutputImplementation):
    """Django ORM implementation wrapper for JSX output."""

    def dump(self, obj: Any, file: Any, *args: Any, **kwds: Any) -> None:
        pass

    def finalize(self, obj: Any, *args: Any, **kwds: Any) -> None:


        if kwds.get("docId"):
            doc = Document.objects.get(pk=kwds["docId"])

            logging.debug("Finalizing Document for obj: %s ", doc.title)

            doc.last_build_at = obj.get("last_build_at")
            doc.global_context = obj.get("global_context", {})
            doc.save()
        
    def createAsset(self, obj: Any, *args: Any, **kwds: Any) -> None:

        if kwds.get("docId"):
            doc = Document.objects.get(pk=kwds["docId"])

            logging.debug("Creating StaticAsset for obj: %s ", obj.get("path"))

            # Use update_or_create to avoid duplicates
            asset, created = StaticAsset.objects.update_or_create(
                document=doc,
                path=obj.get("path", ""),
                defaults={
                    'hash': obj.get("hash", ""),
                }
            )
    
    def createPage(self, obj: Any, *args: Any, **kwds: Any) -> types.NoneType:
        
        if kwds.get("docId"):
            doc = Document.objects.get(pk=kwds["docId"])

            # Get page name from context - could be 'pagename' or 'current_page_name'
            page_name = obj.get("current_page_name") or obj.get("pagename", "")
            
            # Skip if no page name
            if not page_name:
                logging.debug("No page name found in context, skipping page creation")
                return

            # Use update_or_create to avoid duplicates
            page, created = Page.objects.update_or_create(
                document=doc,
                current_page_name=page_name,
                defaults={
                    'title': obj.get("title", ""),
                    'context': obj.get("context", {}),
                }
            )

            if page:

                logging.debug("Created Page: %s ", page.current_page_name)

                # Create sections for the page
                sections = obj.get("section_list", [])
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
                            'content_block': content_block,
                        }
                    )

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




