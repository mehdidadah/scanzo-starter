"""
Ensure the project root is on sys.path so that `import core` works when running pytest or
any scripts from within this repository, regardless of the current working directory.

Python automatically imports `site` on startup, which in turn tries to import
`sitecustomize` if available on sys.path (which includes the current working directory).
Placing this file at the repository root makes imports like `from core...` reliable.
"""
from __future__ import annotations
import os
import sys

# Determine the repository root as the directory where this file lives
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

# Prepend the repo root to sys.path if it's not already there
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
