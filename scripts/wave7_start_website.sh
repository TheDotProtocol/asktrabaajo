#!/bin/zsh
# Public AskTrabaajo website — sibling repo, port 3001.
set -e
WEBSITE="${WAVE7_WEBSITE_DIR:-$(cd "$(dirname "$0")/../.." && pwd)/trabaajowebsite/frontend}"
if [ ! -d "$WEBSITE" ]; then
  echo "Website not found at $WEBSITE"
  echo "Clone https://github.com/TheDotProtocol/trabaajowebsite next to this repo."
  exit 1
fi
cd "$WEBSITE"
export PORT="${PORT:-3001}"
export WDS_SOCKET_PORT="${WDS_SOCKET_PORT:-3001}"
export REACT_APP_CANONICAL_APP_URL="${REACT_APP_CANONICAL_APP_URL:-http://localhost:3000}"
export ENABLE_HEALTH_CHECK=false
if [ ! -d node_modules ]; then
  echo "Installing website dependencies…"
  yarn install --frozen-lockfile || yarn install
fi
exec yarn start
