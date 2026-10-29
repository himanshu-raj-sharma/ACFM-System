"""Pytest configuration to ensure tests import the package from the repo checkout."""

import sys
from pathlib import Path

# Ensure the repository root is on sys.path so `import acfm_net` resolves
# to the local checkout, not an installed wheel (or empty namespace).
REPO_ROOT = Path(__file__).parent.resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))