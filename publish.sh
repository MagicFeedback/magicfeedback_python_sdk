#!/usr/bin/env bash
set -euo pipefail

# Ensure build tooling is present
python3 -m pip install --upgrade build twine

VERSION=$(grep -m1 '^version' pyproject.toml | cut -d'"' -f2)
if [ -z "$VERSION" ]; then
    echo "error: could not read version from pyproject.toml" >&2
    exit 1
fi
echo "==> publishing magicfeedback $VERSION"

# Fail early if this version is already on PyPI. Uploads are irreversible — a
# published filename can never be reused — so the fix is always to bump the
# version, never to retry. (This replaces the old --skip-existing flag, which
# hid exactly this mistake by silently doing nothing.)
if curl -sf "https://pypi.org/pypi/magicfeedback/$VERSION/json" >/dev/null; then
    echo "error: magicfeedback $VERSION is already published on PyPI." >&2
    echo "       Bump the version in pyproject.toml and setup.py first." >&2
    exit 1
fi

# Clear the intermediate build tree so no stale module sneaks into the wheel.
# dist/ is deliberately NOT wiped: we upload only this version's files (see
# below), so artifacts from previous builds can sit there harmlessly.
rm -rf build/ src/*.egg-info

python3 -m build

# Upload ONLY the files belonging to $VERSION. The previous `dist/*` wildcard
# uploaded whatever happened to be in the directory — stale versions,
# half-finished builds, or a version deliberately left unpublished.
SDIST="dist/magicfeedback-$VERSION.tar.gz"
shopt -s nullglob
WHEELS=(dist/magicfeedback-"$VERSION"-*.whl)
shopt -u nullglob

if [ ! -f "$SDIST" ]; then
    echo "error: expected sdist not found: $SDIST" >&2
    exit 1
fi
if [ "${#WHEELS[@]}" -ne 1 ]; then
    echo "error: expected exactly 1 wheel for $VERSION, found ${#WHEELS[@]}" >&2
    exit 1
fi

ARTIFACTS=("$SDIST" "${WHEELS[@]}")
echo "==> uploading:"
printf '    %s\n' "${ARTIFACTS[@]}"

# Extra args (e.g. --verbose) are forwarded to twine.
python3 -m twine upload --repository pypi "${ARTIFACTS[@]}" "$@"
