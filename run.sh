#!/bin/bash

# Version input
read -p "Enter version (e.g. 1.0.1): " VERSION

# Check empty
if [ -z "$VERSION" ]; then
  echo "❌ Version required"
  exit 1
fi

# Update version in pyproject.toml
sed -i "s/^version = .*/version = \"$VERSION\"/" pyproject.toml

# Git commit
git add .
git commit -m "release v$VERSION"

# Create tag
git tag v$VERSION

# Push code + tag
git push origin main
git push origin v$VERSION

echo "🚀 Released v$VERSION (GitHub Action will publish to PyPI)"
