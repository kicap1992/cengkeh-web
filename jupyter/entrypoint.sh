#!/bin/sh
set -e

if [ -z "$JUPYTER_PASSWORD" ]; then
    echo "❌ JUPYTER_PASSWORD not set. Using default 'cengkeh123'."
    JUPYTER_PASSWORD="cengkeh123"
fi

echo "🔐 Hashing password..."
HASH=$(python -c "
from jupyter_server.auth import passwd
print(passwd('$JUPYTER_PASSWORD'))
")

echo "🍀 Starting Jupyter Notebook on 0.0.0.0:8888"
exec jupyter notebook \
    --ip=0.0.0.0 \
    --port=8888 \
    --no-browser \
    --allow-root \
    --NotebookApp.password="$HASH" \
    --NotebookApp.token='' \
    --ServerApp.root_dir=/workspace