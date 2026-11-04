#!/usr/bin/env bash
set -euo pipefail

# Publishes the `deepdots` bridge distribution (packages/deepdots), NOT the SDK
# itself. The SDK is published by ./publish.sh.
#
# The bridge only declares a dependency on magicfeedback, so it rarely needs
# republishing — only when its own metadata changes, or when the minimum SDK
# version it requires moves.

BRIDGE_DIR="packages/deepdots"

python3 -m pip install --upgrade build twine

VERSION=$(grep -m1 '^version' "$BRIDGE_DIR/pyproject.toml" | cut -d'"' -f2)
if [ -z "$VERSION" ]; then
    echo "error: could not read version from $BRIDGE_DIR/pyproject.toml" >&2
    exit 1
fi
echo "==> publishing deepdots $VERSION (bridge -> magicfeedback)"

# Namespaced so it never collides with the SDK's own vX.Y.Z tags: the bridge
# and the SDK are versioned independently.
TAG="deepdots-v$VERSION"

if [ -n "$(git status --porcelain)" ]; then
    echo "error: the working tree has uncommitted changes." >&2
    echo "       Commit them first — the $TAG tag must match what is published." >&2
    exit 1
fi

if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null 2>&1 \
   || git ls-remote --exit-code --tags origin "$TAG" >/dev/null 2>&1; then
    echo "error: tag $TAG already exists locally or on origin." >&2
    exit 1
fi

# Fail early if already published: uploads are irreversible, so the fix is
# always to bump the version rather than retry.
if curl -sf "https://pypi.org/pypi/deepdots/$VERSION/json" >/dev/null; then
    echo "error: deepdots $VERSION is already published on PyPI." >&2
    echo "       Bump the version in $BRIDGE_DIR/pyproject.toml first." >&2
    exit 1
fi

rm -rf "$BRIDGE_DIR/build" "$BRIDGE_DIR"/*.egg-info

python3 -m build --outdir "$BRIDGE_DIR/dist" "$BRIDGE_DIR"

SDIST="$BRIDGE_DIR/dist/deepdots-$VERSION.tar.gz"
shopt -s nullglob
WHEELS=("$BRIDGE_DIR/dist/deepdots-$VERSION-"*.whl)
shopt -u nullglob

if [ ! -f "$SDIST" ]; then
    echo "error: expected sdist not found: $SDIST" >&2
    exit 1
fi
if [ "${#WHEELS[@]}" -ne 1 ]; then
    echo "error: expected exactly 1 wheel for $VERSION, found ${#WHEELS[@]}" >&2
    exit 1
fi

# A bridge that ships modules would shadow the real ones. Guard against it.
if python3 -c "
import sys, zipfile
names = zipfile.ZipFile('${WHEELS[0]}').namelist()
mods = [n for n in names if n.endswith('.py')]
sys.exit(1 if mods else 0)
"; then
    :
else
    echo "error: the bridge wheel contains Python modules; it must be metadata-only." >&2
    exit 1
fi

ARTIFACTS=("$SDIST" "${WHEELS[@]}")
echo "==> uploading:"
printf '    %s\n' "${ARTIFACTS[@]}"

python3 -m twine upload --repository pypi "${ARTIFACTS[@]}" "$@"

git tag -a "$TAG" -m "deepdots bridge $VERSION"
# Pushed as refs/tags/... explicitly: version branches share their name with
# the release tag (branch v1.0.20, tag v1.0.20), and a bare name would be
# ambiguous — git refuses with "matches more than one".
if git push origin "refs/tags/$TAG"; then
    echo "==> tagged $TAG"
else
    echo "warning: $VERSION is published but pushing tag $TAG failed." >&2
    echo "         Retry with: git push origin refs/tags/$TAG" >&2
fi
