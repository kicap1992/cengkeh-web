#!/usr/bin/env bash
#
# deploy.sh — Deploy cengkeh-web on a remote host.
#
# Intended to be run FROM another machine via:
#     ssh cowrie@<prod-host> 'bash -s' < scripts/deploy.sh
#
# Or from CI:
#     - run: ssh cowrie@<prod-host> 'bash -s' < scripts/deploy.sh
#
set -euo pipefail

DEPLOY_DIR="${1:-$HOME/cengkeh-web}"
REPO_URL="${CENGKEH_REPO_URL:-https://gitea.kicap-karan.com/kicap/cengkeh-web.git}"

log() { echo "[deploy] $*"; }
die() { echo "[deploy] ❌ $*" >&2; exit 1; }

# 1. Clone if missing, pull otherwise
if [ ! -d "$DEPLOY_DIR/.git" ]; then
  log "Cloning $REPO_URL → $DEPLOY_DIR"
  git clone "$REPO_URL" "$DEPLOY_DIR" || die "git clone failed"
else
  log "Pulling latest in $DEPLOY_DIR"
  git -C "$DEPLOY_DIR" fetch --all --tags || die "git fetch failed"
  git -C "$DEPLOY_DIR" pull --ff-only        || die "git pull failed"
fi

# 2. Enter the deploy dir
cd "$DEPLOY_DIR" || die "cannot cd to $DEPLOY_DIR"
log "Working directory: $(pwd)"
log "Commit: $(git rev-parse --short HEAD)"

# 3. Ensure .env exists
[ -f .env ] || die ".env not found in $DEPLOY_DIR — create it first"

# 4. Bring up the stack
log "Starting stack..."
docker compose -f docker-compose.yml up -d --wait || die "compose up failed"

# 5. Run migrations
log "Applying migrations..."
docker compose -f docker-compose.yml --profile tools run --rm dbmate up \
  || die "dbmate up failed"

# 6. Status
log "✅ Deploy complete."
docker compose -f docker-compose.yml ps
