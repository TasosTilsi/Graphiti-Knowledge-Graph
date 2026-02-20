#!/bin/sh
# Graphiti Knowledge Graph - Pre-commit validation hook
# Scans staged files for secrets and checks repository size

# GRAPHITI_HOOK_START
# Skip if GRAPHITI_SKIP is set
[ "$GRAPHITI_SKIP" = "1" ] && exit 0

# Check if graphiti is available
command -v graphiti >/dev/null 2>&1 || exit 0

# Check if hooks are enabled
graphiti config get hooks.enabled 2>/dev/null | grep -q "true" || exit 0

# Scan staged files for secrets (blocks commit if secrets found)
python -c "
from pathlib import Path
from src.security.scanner import scan_staged_secrets
import sys
result = scan_staged_secrets(Path('.'))
if result:
    sys.exit(1)
sys.exit(0)
" 2>&1
SECRETS_EXIT=$?
[ "$SECRETS_EXIT" -ne 0 ] && exit "$SECRETS_EXIT"

# Check repository size (warns but does not block)
python -c "
from pathlib import Path
from src.security.scanner import check_graphiti_size
check_graphiti_size(Path('.'))
" 2>&1

exit 0
# GRAPHITI_HOOK_END
