#!/bin/sh
# Start Phoenix locally at http://127.0.0.1:6006. Traces are stored in .phoenix/
# (inside the repo, so a rehearsal run doubles as the offline backup).
cd "$(dirname "$0")/.." || exit 1
export PHOENIX_WORKING_DIR="$PWD/.phoenix" PHOENIX_HOST=127.0.0.1 PHOENIX_PORT=6006
# Runs in its own env (uvx): the server needs mcp>=2, the demo venv pins mcp<2.
exec uvx --from arize-phoenix==22.0.1 phoenix serve
