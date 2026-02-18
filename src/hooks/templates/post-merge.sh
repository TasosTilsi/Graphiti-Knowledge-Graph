#!/bin/bash
# Graphiti Knowledge Graph - Post-merge auto-heal hook
# Replays new journal entries after merge to sync local database

# GRAPHITI_HOOK_START
# Skip if GRAPHITI_SKIP is set
if [ "$GRAPHITI_SKIP" = "1" ]; then
    exit 0
fi

# Check if graphiti is available
if ! command -v graphiti &> /dev/null; then
    exit 0
fi

# Check if hooks are enabled
ENABLED=$(graphiti config get hooks.enabled 2>/dev/null)
if [ "$ENABLED" = "false" ]; then
    exit 0
fi

# Run auto-heal (incremental journal replay)
python -c "
from pathlib import Path
from src.gitops.autoheal import auto_heal
auto_heal(Path('.'))
" 2>&1

# Always exit 0 - never block merge
exit 0
# GRAPHITI_HOOK_END
