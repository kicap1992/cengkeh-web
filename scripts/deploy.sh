#!/usr/bin/env bash
#
# deploy.sh — Deploy cengkeh-web on a remote host.
#
# Intended to be run FROM another machine via:
#     ssh cowrie@<prod-host> 'bash -s' < scripts/deploy.sh
#
# IMPORTANT: All docker commands use `< /dev/null` to prevent them
# from consuming the piped stdin (the deploy script itself).
#
set -euo pipefail

DEPLOY_DIR="${1:-$HOME/cengkeh-web}"
REPO_URL="${CENGKEH_REPO_URL:-https://gitea.kicap-karan.com/kicap/cengkeh-web.git}"

log() { echo "[deploy] $*"; }
warn() { echo "[deploy] ⚠  $*" >&2; }
die() { echo "[deploy] ❌ $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# 1. Clone if missing, pull otherwise
# ---------------------------------------------------------------------------
if [ ! -d "$DEPLOY_DIR/.git" ]; then
  log "Cloning $REPO_URL → $DEPLOY_DIR"
  git clone "$REPO_URL" "$DEPLOY_DIR" < /dev/null || die "git clone failed"
else
  log "Pulling latest in $DEPLOY_DIR"
  git -C "$DEPLOY_DIR" fetch --all --tags < /dev/null || die "git fetch failed"
  git -C "$DEPLOY_DIR" pull --ff-only < /dev/null        || die "git pull failed"
fi

# ---------------------------------------------------------------------------
# 2. Enter the deploy dir
# ---------------------------------------------------------------------------
cd "$DEPLOY_DIR" || die "cannot cd to $DEPLOY_DIR"
log "Working directory: $(pwd)"
log "Commit: $(git rev-parse --short HEAD)"

# ---------------------------------------------------------------------------
# 3. Ensure .env exists
# ---------------------------------------------------------------------------
[ -f .env ] || die ".env not found in $DEPLOY_DIR — create it first"

# ---------------------------------------------------------------------------
# 4. Bring up the stack
# ---------------------------------------------------------------------------
log "Starting stack..."
sudo docker compose -f docker-compose.yml up -d --wait \
  < /dev/null || die "compose up failed"

# ---------------------------------------------------------------------------
# 5. Run migrations
# ---------------------------------------------------------------------------
log "Applying migrations..."
sudo docker compose -f docker-compose.yml --profile tools build dbmate \
  < /dev/null || die "dbmate build failed"

sudo docker compose -f docker-compose.yml --profile tools run --rm -T dbmate up \
  < /dev/null || die "dbmate up failed"

log "=== migrations step complete ==="

# ---------------------------------------------------------------------------
# 6. Sanity checks (with verbose output)
# ---------------------------------------------------------------------------
log "--- sanity checks ---"

PY_DIR="$DEPLOY_DIR/py-db-populate"
VENV_DIR="$PY_DIR/venv"
JSON_PATH="$DEPLOY_DIR/cengkeh-data.json"

log "  Checking py-db-populate/..."
if [ ! -d "$PY_DIR" ]; then
  log "    ❌ missing: $PY_DIR"
  log "    Contents of $DEPLOY_DIR:"
  ls -la "$DEPLOY_DIR" || true
  die "py-db-populate/ not found in $DEPLOY_DIR"
fi
log "    ✅ $PY_DIR"

log "  Checking requirements.txt..."
if [ ! -f "$PY_DIR/requirements.txt" ]; then
  log "    ❌ missing: $PY_DIR/requirements.txt"
  ls -la "$PY_DIR" || true
  die "requirements.txt not found"
fi
log "    ✅ $PY_DIR/requirements.txt"

log "  Checking cengkeh-data.json..."
if [ ! -f "$JSON_PATH" ]; then
  log "    ❌ missing: $JSON_PATH"
  log "    Contents of $DEPLOY_DIR:"
  ls -la "$DEPLOY_DIR" || true
  die "cengkeh-data.json not found in $DEPLOY_DIR"
fi
log "    ✅ $JSON_PATH"

# ---------------------------------------------------------------------------
# 7. Ensure Python venv exists
# ---------------------------------------------------------------------------
if [ ! -d "$VENV_DIR" ]; then
  log "Creating Python venv (first time)..."
  python3 -m venv "$VENV_DIR" || die "venv creation failed"
  "$VENV_DIR/bin/pip" install --quiet --upgrade pip || die "pip upgrade failed"
else
  log "Python venv already exists — reusing"
fi

log "Ensuring Python dependencies are installed..."
"$VENV_DIR/bin/pip" install --quiet -r "$PY_DIR/requirements.txt" \
  || die "pip install failed"

# ---------------------------------------------------------------------------
# 8. Populate the database from the JSON
# ---------------------------------------------------------------------------
log "Populating database..."
cd "$PY_DIR" || die "cannot cd to $PY_DIR"

for script in import_pertanyaan.py \
              import_variasi.py \
              import_keyword.py \
              import_relasi.py \
              import_pertanyaan_sumber.py \
              import_follow_up.py \
              import_follow_option.py \
              import_option_next_qa.py; do
  log "  Running $script..."
  "$VENV_DIR/bin/python" "$script" "$JSON_PATH" < /dev/null \
    || die "$script failed"
done

cd "$DEPLOY_DIR" || die "cannot cd back to $DEPLOY_DIR"

# ---------------------------------------------------------------------------
# 9. Status
# ---------------------------------------------------------------------------
log "✅ Deploy complete."
sudo docker compose -f docker-compose.yml ps < /dev/null