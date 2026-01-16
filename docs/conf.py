import os
import sys

sys.path.insert(0, os.path.abspath(".."))
from django.conf import settings  # noqa

settings.configure()

project = "spienx-hub"
copyright = "2026, SPIE Automation GmbH"


extensions = [
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.napoleon",
    "sphinxcontrib.spelling",
    "auto_pytabs.sphinx_ext",
    "sphinx_autodoc_typehints",
    "sphinx_rtd_theme",
    "myst_parser",
    "autodoc2",
]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "django": ("https://docs.djangoproject.com/en/5.0/", None),
    "grpc": ("https://grpc.github.io/grpc/python/", None),
    "rest_framework": ("https://www.django-rest-framework.org/", None),
}