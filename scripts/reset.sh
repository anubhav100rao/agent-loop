#!/bin/sh
# Restore the planted bug and clear ticket comments.
cd "$(dirname "$0")/.." || exit 1
git checkout -q -- shop mock_mcp/comments.json
echo "reset: bug restored, comments cleared"
