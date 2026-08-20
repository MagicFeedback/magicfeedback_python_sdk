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

TAG="v$VERSION"

# The release tag must point at the code that actually goes to PyPI, so refuse
# to publish from a tree with uncommitted changes.
if [ -n "$(git status --porcelain)" ]; then
    echo "error: the working tree has uncommitted changes." >&2
    echo "       Commit them first — the $TAG tag must match what is published." >&2
    exit 1
fi

# Check the tag up front rather than after an irreversible upload.
if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null 2>&1 \
   || git ls-remote --exit-code --tags origin "$TAG" >/dev/null 2>&1; then
    echo "error: tag $TAG already exists locally or on origin." >&2
    exit 1
fi

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

# Tag only now: the upload is the irreversible step, so the tag records what
# genuinely shipped. Branches move; a tag does not, which is why the tag rather
# than the branch is the durable record of a release.
git tag -a "$TAG" -m "magicfeedback $VERSION"
if git push origin "$TAG"; then
    echo "==> tagged $TAG"
else
    echo "warning: $VERSION is published but pushing tag $TAG failed." >&2
    echo "         Retry with: git push origin $TAG" >&2
fi
