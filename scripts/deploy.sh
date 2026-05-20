#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="sprintbox-2005int"
APP_DIR="/home/botdeploy/int2005bot"
SERVICE_NAME="int2005bot"
BRANCH="main"

cd "$(dirname "$0")/.."

if [[ -n "$(git status --porcelain)" ]]; then
  echo "There are uncommitted local changes. Commit them before deploy."
  git status --short
  exit 1
fi

git fetch origin "$BRANCH"

LOCAL_SHA="$(git rev-parse "$BRANCH")"
REMOTE_SHA="$(git rev-parse "origin/$BRANCH")"

if [[ "$LOCAL_SHA" != "$REMOTE_SHA" ]]; then
  echo "Local $BRANCH is not pushed to GitHub."
  echo "Run: git push origin $BRANCH"
  exit 1
fi

ssh "$REMOTE_HOST" "set -euo pipefail
  cd '$APP_DIR'
  git fetch origin '$BRANCH'
  git reset --hard 'origin/$BRANCH'
  .venv/bin/python -m pip install -r requirements.txt
  .venv/bin/python -m py_compile bot.py
  sudo systemctl restart '$SERVICE_NAME'
  sudo systemctl --no-pager --full status '$SERVICE_NAME'
"

echo "Deploy finished from GitHub commit $LOCAL_SHA."

