# Phase 06: Automatic Capture — Human Verification Guide

**Phase goal:** Confirm that automatic capture from git commits and conversations (R4.1, R4.2)
behaves correctly at runtime in a live environment.

**Status of automated verification:** All 7 observable truths verified through code analysis.
All code artifacts present and wired. This guide covers what automated verification cannot do:
measuring commit timing (<100ms), confirming no perceivable lag, end-to-end excluded file
verification, and confirming captured knowledge appears in search results.

**Requirements under test:**
- R4.1: Conversation-Based Capture — automatic knowledge capture from Claude Code conversations
- R4.2: Git Post-Commit Hook — commit context captured on each commit, hook non-blocking (<100ms)

---

## Prerequisites

Before running any tests, confirm the environment:

```bash
# 1. Virtual environment is active and graphiti CLI available
graphiti --version
# Expected: graphiti version X.Y.Z (not "command not found")
# If not found: source .venv/bin/activate && export PATH="$PATH:$(pwd)/.venv/bin"

# 2. Ollama is running (needed for LLM summarization in capture)
ollama list
# Expected: list of available models (nomic-embed-text, gemma2:9b or similar)
# If not running: ollama serve &

# 3. graphiti health check
graphiti health
# Expected: all checks show ok or warning (not error for storage/LLM)

# 4. Working directory is the project root
ls src/hooks/ src/capture/
# Expected: lists Python files in both directories
```

---

## Test 1: Git Hook Installation

**What this tests:** R4.2 — `graphiti hooks install` installs a working post-commit hook.

**Commands:**

```bash
# Step 1: Check current hook status
graphiti hooks status
# Note current state (installed or not installed)

# Step 2: Install hooks (idempotent — safe to run even if already installed)
graphiti hooks install
# Expected: success message about hooks installed

# Step 3: Confirm post-commit hook file exists
cat .git/hooks/post-commit
# Expected: file contains GRAPHITI_HOOK_START marker and echo "$COMMIT_HASH" logic

# Step 4: Check hook status shows installed
graphiti hooks status
```

**Expected output for step 2:**

```
Hooks installed successfully.
  git post-commit hook: installed
  Claude Code Stop hook: installed
```

**Expected output for step 3 (excerpt):**

```bash
#!/bin/sh
# GRAPHITI_HOOK_START
...
echo "$COMMIT_HASH" >> "$PENDING_FILE"
...
# GRAPHITI_HOOK_END
```

**Expected output for step 4:**

```
Hook Status
┌──────────────────────┬───────────┬─────────┐
│ Hook Type            │ Installed │ Enabled │
├──────────────────────┼───────────┼─────────┤
│ Git post-commit      │ yes       │ enabled │
│ Claude Code Stop     │ yes       │ enabled │
└──────────────────────┴───────────┴─────────┘
```

**Pass criteria:**
- `.git/hooks/post-commit` exists and contains `GRAPHITI_HOOK_START`
- `graphiti hooks status` shows both hooks as `yes` / `enabled`

---

## Test 2: Git Hook Timing (<100ms)

**What this tests:** R4.2 — Post-commit hook completes in under 100ms, commits are non-blocking.

**Setup:** Ensure hooks are installed (Test 1 must pass first).

**Commands:**

```bash
# Step 1: Create a temporary test file
echo "# test file for hook timing verification" > /tmp/graphiti_hook_test.py
cp /tmp/graphiti_hook_test.py ./graphiti_hook_timing_test.py
git add graphiti_hook_timing_test.py

# Step 2: Measure commit time
time git commit -m "test: hook timing verification (will revert)"
# Expected: commit completes, real time shown

# Step 3: Check that pending_commits file was updated
cat ~/.graphiti/pending_commits
# Expected: last line is the commit hash from step 2

# Step 4: Clean up the test commit
git revert HEAD --no-edit
git push   # only if on a branch you own — skip if on main
# Or just: git reset HEAD~1 --soft && git restore --staged graphiti_hook_timing_test.py
rm graphiti_hook_timing_test.py
git add graphiti_hook_timing_test.py
git commit -m "cleanup: remove hook timing test file"
```

**Expected output for step 2:**

```
[main abc1234] test: hook timing verification (will revert)
 1 file changed, 1 insertion(+)
 create mode 100644 graphiti_hook_timing_test.py

real    0m0.0XXs     <- must be < 0m0.100s
user    0m0.0XXs
sys     0m0.0XXs
```

**Expected output for step 3:**

```
abc1234def567...   <- full commit hash from the test commit
```

**Pass criteria:**
- `real` time in `time git commit` output is under `0m0.100s` (100ms)
- `~/.graphiti/pending_commits` contains the new commit hash after the commit
- No error output from git during or after the commit

**Note:** If `~/.graphiti/pending_commits` does not exist yet, create the directory:
```bash
mkdir -p ~/.graphiti
```
The hook creates the file on first commit.

---

## Test 3: Excluded Files Are Not Captured

**What this tests:** R4.2 — Security filtering in the end-to-end capture pipeline. Files matching
exclusion patterns (e.g., `.env`) must not have their content captured in the knowledge graph.

**Important:** This test requires background processing to run. Run `graphiti queue process` after
the commit to trigger processing immediately without waiting for the background worker.

**Commands:**

```bash
# Step 1: Create a fake .env file with a fake secret
cat > .env.test_verification << 'EOF'
# Verification test file — fake credentials, not real
FAKE_API_KEY=sk_test_THISSHOULDNOTAPPEARINGRAPH1234567890
FAKE_DB_URL=postgresql://user:password@localhost/testdb
EOF

# Step 2: Commit it to trigger the hook
git add .env.test_verification
git commit -m "test: add fake env file for exclusion verification (will remove)"

# Step 3: Note the commit hash
COMMIT_HASH=$(git rev-parse HEAD)
echo "Commit hash: $COMMIT_HASH"

# Step 4: Trigger queue processing immediately (don't wait for background worker)
graphiti queue process
# Wait for processing to complete (up to 60 seconds)

# Step 5: Search for the fake secret — it must NOT appear
echo ""
echo "=== Searching for excluded secret (should return nothing) ==="
graphiti search "THISSHOULDNOTAPPEARINGRAPH1234567890"
graphiti search "sk_test_THISSHOULDNOTAPPEARINGRAPH"

# Step 6: Search for the env file content — it must NOT appear
echo ""
echo "=== Searching for env file content (should return nothing) ==="
graphiti search ".env.test_verification"

# Step 7: Clean up — revert and remove the test commit
git rm .env.test_verification
git commit -m "cleanup: remove fake env file for exclusion verification"
```

**Expected output for step 5 and 6:**

```
No results found.
```
or
```
No entities matching "THISSHOULDNOTAPPEARINGRAPH1234567890"
```

The fake secret string `THISSHOULDNOTAPPEARINGRAPH1234567890` must not appear anywhere in search
results. If results do appear, the security filtering pipeline has a gap.

**Pass criteria:**
- Search for the fake secret returns 0 results
- Search for the fake API key prefix returns 0 results
- (Optional) Check audit log: `cat ~/.graphiti/audit.log | grep "file_excluded"` — should show the
  `.env.test_verification` file was excluded

---

## Test 4: Captured Knowledge Is Queryable

**What this tests:** R4.1 and R4.2 — After a meaningful commit, captured knowledge appears in
search results. This validates the full pipeline: hook → pending file → queue → LLM summarization
→ graph storage → search.

**Commands:**

```bash
# Step 1: Create a file with meaningful content (architectural decision)
cat > /tmp/test_arch_decision.py << 'EOF'
"""
Service layer pattern for user authentication.

This module extracts user authentication logic into a dedicated UserAuthService
to improve separation of concerns and enable independent testing.
The service validates JWT tokens, manages session state, and integrates
with the permission system for role-based access control.
"""

class UserAuthService:
    """Handles user authentication with JWT and RBAC."""

    def authenticate(self, token: str) -> bool:
        """Validate JWT token and check permissions."""
        pass
EOF

cp /tmp/test_arch_decision.py ./user_auth_service_test_capture.py
git add user_auth_service_test_capture.py

# Step 2: Commit with a meaningful message
git commit -m "refactor: extract UserAuthService for better separation of concerns"

# Note the commit hash
COMMIT_HASH=$(git rev-parse HEAD)
echo "Commit hash: $COMMIT_HASH"

# Step 3: Trigger queue processing immediately
graphiti queue process
# Wait for LLM processing (this may take 30-120 seconds with local models)
# Watch for completion:
graphiti queue status

# Step 4: Search for captured knowledge
echo ""
echo "=== Searching for captured architectural decision ==="
graphiti search "UserAuthService"
graphiti search "separation of concerns"
graphiti search "authentication service"

# Step 5: List recent entities to see what was captured
graphiti list --limit 5

# Step 6: Clean up
git rm user_auth_service_test_capture.py
git commit -m "cleanup: remove test capture file"
rm /tmp/test_arch_decision.py
```

**Expected output for step 4:**

At least one search should return a result. Example:

```
Results for "separation of concerns":
  1. UserAuthService — refactor: extract UserAuthService for better separation of concerns
     Source: git commit abc1234
     "...extracts user authentication logic into a dedicated UserAuthService
      to improve separation of concerns and enable independent testing..."
```

The entity content should reference the commit message or the file docstring, proving the
pipeline extracted meaningful knowledge from the commit.

**Pass criteria:**
- At least one of the three searches returns a non-empty result
- The result content is related to the commit (not noise)
- `graphiti list --limit 5` shows recently created entities

**Note on timing:** LLM summarization with local models (gemma2:9b) can take 30-120 seconds.
If queue processing times out, retry with:
```bash
graphiti queue process
graphiti queue status
```

---

## Test 5: Conversation Capture (Claude Code Session)

**What this tests:** R4.1 — Conversation capture runs without perceivable lag and entities from
the conversation appear in the knowledge graph.

**Note:** This test requires an active Claude Code session. If you are reading this inside Claude
Code, you are already in the correct environment.

**Commands — manual capture (run inside Claude Code terminal):**

```bash
# Step 1: Trigger manual capture of the current conversation
graphiti capture
# Expected: progress indicator, then success message with entity/edge counts
```

**Commands — check auto-capture is configured:**

```bash
# Step 2: Confirm the Claude Code Stop hook is configured
cat .claude/settings.json | python3 -m json.tool | grep -A 3 "Stop"
# Expected: shows graphiti capture --auto command in Stop hooks array
```

**Commands — verify captured entities:**

```bash
# Step 3: After capture, search for something from this conversation
graphiti search "human verification"
graphiti search "security filtering"
graphiti search "graphiti capture"
```

**Expected output for step 1:**

```
Capturing conversation...
  Entities created: X
  Edges created: Y
Capture complete.
```

**Expected output for step 2:**

```json
"Stop": [
  {
    "command": "graphiti capture --auto --transcript-path \"$transcript_path\" --session-id \"$session_id\"",
    "async": true,
    "timeout": 10
  }
]
```

**Expected output for step 3:**

At least one result related to this verification session.

**Pass criteria:**
- `graphiti capture` completes without error and reports entities/edges created
- `.claude/settings.json` contains the Stop hook with `graphiti capture --auto`
- At least one search returns a result from the current conversation context

**Lag assessment:** During normal conversation, if the Stop hook fires at session end, you should
observe no perceivable lag (the hook is async with 10-second timeout and runs in a background
process). If you notice the session taking more than 2 seconds to close after saying "stop" or
ending the session, flag this as a performance issue.

---

## Overall Pass Criteria

All 5 tests must pass:

| # | Test | Pass Condition |
|---|------|----------------|
| 1 | Hook installation | Both hooks installed and `enabled` in status |
| 2 | Hook timing | `time git commit` real time < 100ms; hash in `~/.graphiti/pending_commits` |
| 3 | Excluded files | Fake secret not found in any `graphiti search` result |
| 4 | Captured knowledge queryable | At least one search returns result from test commit |
| 5 | Conversation capture | `graphiti capture` succeeds; Stop hook configured in settings.json |

---

## Troubleshooting

**Hook not writing to pending_commits:**
```bash
# Check hook file is executable
ls -la .git/hooks/post-commit
# If not executable: chmod +x .git/hooks/post-commit

# Test hook manually
bash .git/hooks/post-commit
cat ~/.graphiti/pending_commits
```

**Queue processing fails:**
```bash
# Check queue status
graphiti queue status

# Check dead letter queue
graphiti queue status --dead-letter

# Check structlog output for errors
graphiti queue process 2>&1 | head -50
```

**LLM unavailable:**
```bash
# Check Ollama is running
ollama list
ollama ps

# If not running:
ollama serve &
sleep 2
graphiti health
```

**graphiti command not found:**
```bash
# Activate venv and use full path
source .venv/bin/activate
which graphiti
graphiti --version
```

---

## After Passing: Update VERIFICATION.md

Once all 5 tests pass, update the Phase 06 VERIFICATION.md status:

1. Open `.planning/phases/06-automatic-capture/06-VERIFICATION.md`

2. Change the frontmatter `status` field:
   ```yaml
   # Before:
   status: human_needed

   # After:
   status: passed
   ```

3. Add a `human_verified` date field:
   ```yaml
   verified: 2026-02-13T20:59:33Z
   human_verified: YYYY-MM-DDTHH:MM:SSZ   # today's date and time
   status: passed
   ```

4. At the bottom of the file, add a section:
   ```markdown
   ### Human Verification Result

   **Verified by:** [Your name or "Human tester"]
   **Date:** YYYY-MM-DD
   **All tests passed:** Yes

   | Test | Result |
   |------|--------|
   | Test 1: Hook installation | Both hooks installed and enabled |
   | Test 2: Hook timing | Commit time: Xms (< 100ms) — PASS |
   | Test 3: Excluded files | Secret not captured — PASS |
   | Test 4: Captured knowledge | Results found for "separation of concerns" — PASS |
   | Test 5: Conversation capture | X entities, Y edges captured — PASS |

   **Requirements closed:** R4.1, R4.2
   ```

5. Save the file. Phase 06 verification is now complete.

---

_Guide written: 2026-02-24_
_Phase: 06-automatic-capture_
_Requirements: R4.1, R4.2_
