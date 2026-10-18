#!/usr/bin/env bash
# Copy workspace-template/90_wiki/SCHEMA.md into vault/90_wiki/SCHEMA.md when it changed.
#   scripts/ws-sync-schema.sh            sync (refuses if the workspace SCHEMA has uncommitted edits)
#   scripts/ws-sync-schema.sh --check    exit 1 with a diff if they differ; changes nothing
#   scripts/ws-sync-schema.sh --force    overwrite even with uncommitted edits
set -euo pipefail
cd "$(dirname "$0")/.."
exec uv run --project tools zen-sync-schema --vault "$PWD/vault" --template "$PWD/workspace-template/90_wiki/SCHEMA.md" "$@"
