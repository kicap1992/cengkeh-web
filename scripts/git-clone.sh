#!/usr/bin/env bash
#
# Clone the cengkeh-web repo if it doesn't exist yet.
#
set -euo pipefail

DEPLOY_DIR="${1:-$HOME/cengkeh-web}"
REPO_URL="${CENGKEH_REPO_URL:-https://gitea.kicap-karan.com/kicap/cengkeh-web.git}"

if [ -d "$DEPLOY_DIR/.git" ]; then
  echo "✅ Repo already exists at $DEPLOY_DIR — skipping clone."
else
  echo "📦 Cloning $REPO_URL → $DEPLOY_DIR"
  git clone "$REPO_URL" "$DEPLOY_DIR"
  echo "✅ Clone complete."
fi

cd "$DEPLOY_DIR"
echo "📁 Current directory: $(pwd)"
echo "🔖 Commit: $(git rev-parse --short HEAD)"
