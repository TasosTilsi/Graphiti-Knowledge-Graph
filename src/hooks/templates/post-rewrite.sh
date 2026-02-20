#!/bin/sh
# GRAPHITI_HOOK_START
# Graphiti: trigger background index after rebase/amend to re-index rewritten commits
[ "$GRAPHITI_SKIP" = "1" ] && exit 0
command -v graphiti >/dev/null 2>&1 || exit 0
graphiti config get hooks.enabled 2>/dev/null | grep -q "true" || exit 0

# Background index — never block the rebase/amend operation
(graphiti index >/dev/null 2>&1) &

exit 0
# GRAPHITI_HOOK_END
