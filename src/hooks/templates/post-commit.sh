#!/bin/sh
# === Graphiti Capture Hook ===
# Auto-installed by graphiti - captures commit hashes for background processing
# To remove: graphiti hooks uninstall

# GRAPHITI_HOOK_START
# Append current commit hash to pending file
# Tries multiple ways to locate graphiti: venv, PATH, direct location
COMMIT_HASH=$(git rev-parse HEAD)
PENDING_FILE="${HOME}/.graphiti/pending_commits"

# Ensure directory exists
mkdir -p "$(dirname "$PENDING_FILE")"

# Atomic append (O_APPEND semantics for small writes)
echo "$COMMIT_HASH" >> "$PENDING_FILE"
# GRAPHITI_HOOK_END

exit 0
