#!/bin/sh
# Graphiti Knowledge Graph - Pre-commit validation hook
# Scans staged files for secrets and checks repository size

# GRAPHITI_HOOK_START
# Skip if GRAPHITI_SKIP is set
[ "$GRAPHITI_SKIP" = "1" ] && exit 0

# Locate graphiti binary; derive venv python from same directory
GRAPHITI_BIN=$(command -v graphiti 2>/dev/null)
[ -z "$GRAPHITI_BIN" ] && exit 0
VENV_PYTHON="$(dirname "$GRAPHITI_BIN")/python"
[ ! -x "$VENV_PYTHON" ] && exit 0

# Check if hooks are enabled (use --get flag; exit 0 if key missing or false)
"$GRAPHITI_BIN" config --get hooks.enabled 2>/dev/null | grep -q "true" || exit 0

# Scan staged files for secrets (blocks commit if secrets found)
"$VENV_PYTHON" -c "
from pathlib import Path
from src.gitops.hooks import scan_staged_secrets
import sys
result = scan_staged_secrets(Path('.'))
if result:
    sys.exit(1)
sys.exit(0)
" 2>&1
SECRETS_EXIT=$?
[ "$SECRETS_EXIT" -ne 0 ] && exit "$SECRETS_EXIT"

# Check repository size (warns but does not block)
"$VENV_PYTHON" -c "
from pathlib import Path
from src.gitops.hooks import check_graphiti_size
check_graphiti_size(Path('.'))
" 2>&1

exit 0
# GRAPHITI_HOOK_END
