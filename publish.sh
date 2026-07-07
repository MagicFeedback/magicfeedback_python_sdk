#!/usr/bin/env bash
set -euo pipefail

# Ensure build tooling is present
python3 -m pip install --upgrade build twine

# Start from a clean slate so we never re-upload already-published versions.
# (twine uploads dist/* — stale wheels/sdists from old versions cause 400s.)
rm -rf dist/ build/ src/*.egg-info

# Build sdist + wheel for the current version only
python3 -m build

# Upload. --skip-existing is a safety net: PyPI rejects duplicate filenames
# with 400, so this quietly skips anything already published.
# Extra args (e.g. --verbose) are forwarded to twine.
python3 -m twine upload --repository pypi --skip-existing dist/* "$@"
