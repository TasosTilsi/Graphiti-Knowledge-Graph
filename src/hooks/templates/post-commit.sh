#!/bin/sh
# === Graphiti Capture Hook ===
# Auto-installed by graphiti - captures commit hashes for background processing
# To disable: graphiti config set hooks.enabled false
# To remove: graphiti hooks uninstall

# GRAPHITI_HOOK_START
# Check if capture is enabled via config
if command -v graphiti >/dev/null 2>&1; then
  if ! graphiti config get hooks.enabled 2>/dev/null | grep -q "true"; then
    exit 0
  fi
else
  # graphiti not in PATH, skip silently
  exit 0
fi

# Append current commit hash to pending file
COMMIT_HASH=$(git rev-parse HEAD)
PENDING_FILE="${HOME}/.graphiti/pending_commits"

# Ensure directory exists
mkdir -p "$(dirname "$PENDING_FILE")"

# Atomic append (O_APPEND semantics for small writes)
echo "$COMMIT_HASH" >> "$PENDING_FILE"
# GRAPHITI_HOOK_END

exit 0
