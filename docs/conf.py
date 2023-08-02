# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('../src/'))
# sys.path.insert(0, '/Users/miket/Projects/005_MED-diagnostics/med-live_diagnostics/src')


# -- Project information -----------------------------------------------------

project = 'Model Live Diagnostics'
copyright = '2023, ACCESS-NRI'
author = 'ACCESS-NRI'

# The full version, including alpha/beta/rc tags
release = 'v0.0.1'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx_panels",
    "nbsphinx"
]

# autoapi directives
autoapi_dirs = ["../src/med_diagnostics"]
autodoc_typehints = 'description'
autoapi_ignore = ["*/*.ipynb_checkpoints"]
autoapi_add_toctree_entry = False

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# Config myst-nb
nb_execution_excludepatterns = ["examples/example_notebook.ipynb"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', "**.ipynb_checkpoints"]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# html_theme = 'sphinx_rtd_theme'
html_theme = "sphinx_book_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_theme_options = {
    "use_edit_page_button": False,
    "github_url": "https://github.com/ACCESS-NRI/MED-live-diagnostics",
    "logo": {
        "image_light": "_static/access_logo_rgb.svg",
        "image_dark": "_static/access_logo_rgb.svg",
    },
}
