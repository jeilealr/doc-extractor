"""Sphinx configuration for the doc-extractor documentation (built locally)."""

from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from doc_extractor import __version__  # noqa: E402
from doc_extractor.cli import make_parser  # noqa: E402

project = "doc-extractor"
author = "doc-extractor contributors"
copyright = "2026, doc-extractor contributors"
version = release = __version__

extensions = [
    "myst_parser",
    "sphinx_design",
    "sphinx_copybutton",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]
myst_enable_extensions = ["colon_fence", "deflist", "fieldlist"]
myst_heading_anchors = 3
source_suffix = {".md": "markdown", ".rst": "restructuredtext"}
exclude_patterns = ["_build", "**/private/**"]
templates_path = []

autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_default_options = {"members": True, "undoc-members": False}
napoleon_numpy_docstring = True
napoleon_google_docstring = False

html_theme = "pydata_sphinx_theme"
html_title = f"doc-extractor {release}"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_theme_options = {
    "secondary_sidebar_items": ["page-toc"],
    "navigation_with_keys": False,
    "show_toc_level": 2,
    "footer_start": ["copyright"],
    "footer_end": ["sphinx-version"],
}
html_context = {"default_mode": "auto"}


def _write_cli_help() -> None:
    """Render `--help` of every command so the CLI page can never drift from the code."""
    out = HERE / "_generated"
    out.mkdir(exist_ok=True)
    commands = {
        "main": [],
        "inspect": ["inspect"],
        "extract": ["extract"],
        "profiles": ["profiles"],
        "profiles-list": ["profiles", "list"],
        "profiles-validate": ["profiles", "validate"],
        "profiles-explain": ["profiles", "explain"],
    }
    for name, argv in commands.items():
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), contextlib.suppress(SystemExit):
            make_parser().parse_args([*argv, "--help"])
        (out / f"cli-{name}.txt").write_text(buffer.getvalue(), encoding="utf-8")


_write_cli_help()
