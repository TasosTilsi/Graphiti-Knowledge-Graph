#!/bin/bash
# Graphiti Knowledge Graph - Pre-commit validation hook
# Auto-stages journal entries, validates schemas, scans for secrets

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

# Run pre-commit validation (auto-stage, schema check, secret scan, size check)
python -c "
from pathlib import Path
from src.gitops.hooks import run_precommit_validation
import sys
sys.exit(run_precommit_validation(Path('.')))
" 2>&1
exit $?
# GRAPHITI_HOOK_END
