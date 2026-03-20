"""
Root conftest.py: ensure the src/ layout takes precedence over the legacy
monolithic epub_translator.py that lives at the project root.
"""
import sys
from pathlib import Path

# Prepend src/ so that `import epub_translator` resolves to the package in
# src/epub_translator/, not to the legacy single-file epub_translator.py.
_src = str(Path(__file__).parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)
