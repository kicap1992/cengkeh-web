# Deploy Scripts

## `deploy.sh`

Deploys cengkeh-web to a remote host.

### What it does

1. Clones the repo (or pulls if it exists)
2. Brings up the Docker stack
3. Applies database migrations
4. Bootstraps the Python venv (first time only)
5. Imports the knowledge base JSON into the DB

### Usage

From any machine that can SSH to the target host:

    ssh cowrie@<host> 'bash -s' < scripts/deploy.sh

Or from CI (Gitea Actions), on tag push:

    ssh cowrie@<host> 'bash -s' < scripts/deploy.sh

### Requirements

The target host must have:
- Docker (and `cowrie` in the `docker` group)
- Python 3.11+ with `python3-venv`
- The `cengkeh-data.json` file in the repo
- A `.env` file with database credentials (created manually, once)

### Idempotency

Safe to run repeatedly:
- Migrations use dbmate's tracking table
- Imports use `ON DUPLICATE KEY UPDATE`

### Logs

Every step is logged with `[deploy]` prefix.
Errors go to stderr and exit non-zero.