#!/usr/bin/env bash
set -euo pipefail

# Usage: ./release.sh <version>
# Example: ./release.sh 0.2.0

VERSION="${1:?Usage: ./release.sh <version>}"

# Validate no uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "ERROR: Uncommitted changes. Commit or stash first."
    exit 1
fi

# Validate tag doesn't already exist
if git rev-parse "v${VERSION}" >/dev/null 2>&1; then
    echo "ERROR: Tag v${VERSION} already exists."
    exit 1
fi

# Bump version in all files
sed -i "s/^version = \".*\"/version = \"${VERSION}\"/" pyproject.toml
sed -i "s/^__version__ = \".*\"/__version__ = \"${VERSION}\"/" gptzero_mcp/__init__.py

# Verify each file was updated
grep -q "version = \"${VERSION}\"" pyproject.toml || { echo "ERROR: pyproject.toml not updated"; exit 1; }
grep -q "__version__ = \"${VERSION}\"" gptzero_mcp/__init__.py || { echo "ERROR: __init__.py not updated"; exit 1; }

# Check for server.json (MCP Registry)
if [ -f server.json ]; then
    sed -i "s/\"version\": \".*\"/\"version\": \"${VERSION}\"/" server.json
    grep -q "\"version\": \"${VERSION}\"" server.json || { echo "ERROR: server.json not updated"; exit 1; }
fi

echo "Version bumped to ${VERSION} in all files."

# Commit, tag, push
git add -A
git commit -m "release v${VERSION}"
git tag "v${VERSION}"
git push origin main
git push origin "v${VERSION}"

# Build GitHub release URL
REMOTE_URL=$(git remote get-url origin)
# Convert git@github.com:owner/repo.git or https://github.com/owner/repo.git to owner/repo
REPO=$(echo "${REMOTE_URL}" | sed -E 's#(git@github\.com:|https://github\.com/)##; s/\.git$//')
RELEASE_URL="https://github.com/${REPO}/releases/new?tag=v${VERSION}&title=v${VERSION}&generate-notes=true"

echo ""
echo "============================================"
echo "  Released v${VERSION} successfully!"
echo "============================================"
echo ""
echo "Create the GitHub release to trigger PyPI publish:"
echo "  ${RELEASE_URL}"
echo ""

# Open in browser if possible
if command -v xdg-open &>/dev/null; then
    xdg-open "${RELEASE_URL}" 2>/dev/null || true
elif command -v open &>/dev/null; then
    open "${RELEASE_URL}" 2>/dev/null || true
fi
