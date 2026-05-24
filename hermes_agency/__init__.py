"""
HermesAgency CLI package.

Public entry point: `agency` script (see `cli.py`). The CLI delegates
into framework subsystems for actual work — the package itself is a
thin command surface.
"""

from _framework import __version__

__all__ = ["__version__"]
