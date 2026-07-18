"""
Alakoro FiberSense — Configuração Sphinx
Sphinx Configuration

Autor/Author: Luiz Paulo Colombiano
Licença/License: MIT
"""

import os
import sys
sys.path.insert(0, os.path.abspath('../../..'))

# ─── Informações do projeto / Project information ───
project = 'Alakoro FiberSense'
copyright = '2026, Luiz Paulo Colombiano'
author = 'Luiz Paulo Colombiano'
release = '2.2.1'
version = '2.2.1'

# ─── Extensões / Extensions ───
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx.ext.mathjax',
    'sphinx.ext.todo',
    'sphinx_copybutton',
    'myst_parser',
]

# ─── Templates / Templates ───
templates_path = ['_templates']

# ─── Fontes / Sources ───
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

master_doc = 'index'
language = 'pt_BR'

# ─── Exclusões / Exclusions ───
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# ─── Tema / Theme ───
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
# html_logo = '_static/logo.png'
# html_favicon = '_static/favicon.ico'

# ─── Opções do tema / Theme options ───
html_theme_options = {
    'canonical_url': '',
    'analytics_id': '',
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': True,
    'vcs_pageview_mode': '',
    'style_nav_header_background': '#2c3e50',
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False,
}

html_context = {
    'display_github': True,
    'github_user': 'Colombiano',
    'github_repo': 'Alakoro_FiberSense',
    'github_version': 'main',
    'conf_py_path': '/docs/sphinx/source/',
}

# ─── Autodoc / Autodoc ───
autodoc_member_order = 'bysource'
autodoc_typehints = 'description'

# ─── Napoleon (Google/NumPy docstrings) ───
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_type_aliases = None

# ─── Intersphinx / Intersphinx ───
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'scipy': ('https://docs.scipy.org/doc/scipy/', None),
    'matplotlib': ('https://matplotlib.org/stable/', None),
}

# ─── TODO / TODO ───
todo_include_todos = True

# ─── Copy button / Copy button ───
copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True
