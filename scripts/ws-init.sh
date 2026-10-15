#!/usr/bin/env bash
# Set up the workspace at vault/: clone an existing workspace repo, or scaffold a new one
# from workspace-template/. Idempotent: does nothing if vault/ already exists. Run from anywhere.
#
#   scripts/ws-init.sh <git-url>   clone that repo as vault/
#   scripts/ws-init.sh             scaffold an empty workspace and make it a git repo
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -e vault ]; then
  echo "vault/ already exists — nothing to do"
  exit 0
fi

if [ $# -ge 1 ]; then
  git clone "$1" vault
else
  cp -R workspace-template vault
  (cd vault && git init -q -b main && git add -A && git commit -q -m "workspace: scaffold from zen workspace-template")
  echo "scaffolded vault/ as a new git repo — add a private remote with: (cd vault && git remote add origin <url>)"
fi

(cd tools && uv run zen-index --vault ../vault)
