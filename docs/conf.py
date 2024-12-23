# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Pyaptly'
copyright = 'Adfinis AG'
author = 'Adfinis AG'
release = '2.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'myst_parser',
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.autodoc',
]
myst_enable_extensions = [
    "linkify",
    "replacements",
    "smartquotes",
]

# For autodoc
import sys
from pathlib import Path
sys.path.insert(0, str(Path('..').resolve()))

autosectionlabel_prefix_document = True

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', 'sphinx-template']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'adsy'
html_theme_path = ['sphinx-template/html']
html_title = project
html_static_path = ['sphinx-template/html/adsy/static/']

# Output file base name for HTML help builder.
#htmlhelp_basename = 'test1234'

