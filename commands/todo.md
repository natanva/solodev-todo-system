---
description: Short summary of open issues, grouped by status
allowed-tools: Bash, AskUserQuestion, Write, Read, Edit
---

Show a flat summary of open issues, grouped by `status:` and sorted by `priority:`. **This is NOT an analysis** — it is a listing. If the user then wants to dig into a specific issue, they ask in a separate prompt and only then is the file read.

## First run (only if the config is missing)

If `.claude/hooks/todo.config.json` does NOT exist, run the setup before executing (if it exists, ask nothing):

1. **One single AskUserQuestion call with two questions**:
   - *Listing language*: English / Español.
   - *Run automatically at the start of every session?*: Yes / No. In the option descriptions explain the trade-off: it injects the compact status into the model's context on every session — useful if all your sessions work on issues; wastes tokens if you alternate between control sessions and execution-only sessions (you can always see it on demand with `/todo`).
2. Write `.claude/hooks/todo.config.json` with the answers:
   `{"lang": "en"|"es", "name": "<project name>", "session_start": true|false}`
   (`name` = human-readable repo name, e.g. the directory basename).
3. If the user said **Yes** to auto-start, register the hook in the repo's `.claude/settings.json` — **merge**, never clobber existing hooks:

   ```json
   {"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/todo_status.py", "timeout": 10}]}]}}
   ```
4. Continue with normal execution.

## Execution

One single Bash call. The `todo_status.py` script parses the frontmatters in `docs/issues/open/*.md`, groups by status and emits the canonical format (language per `todo.config.json`):

```bash
echo "{\"cwd\":\"$PWD\"}" | python3 .claude/hooks/todo_status.py --full
```

The `--full` flag lists **every** issue inline (including MEDIA/BAJA backlog and frozen ones). Without it, the script emits the compact mode (meant for the optional SessionStart auto-inject).

**MANDATORY — show the output COMPLETE and VERBATIM:**
- Paste the **entire** output inside a single ``` block and nothing else. Character by character, exactly as the script emitted it.
- **FORBIDDEN**: summarizing, condensing, trimming, truncating, merging issues into one line, omitting rows, abbreviating descriptions, or changing the format in any way. Each issue goes on its own line with its description below, exactly as the script prints it.
- If the listing is long, show it long. Length is NOT a reason to trim — the user needs the whole listing on screen to decide.
- Do not add your own "readable" version of the listing or your own Markdown headings. The ``` block with the raw output is the only representation.

After the block, end with a brief question: *"Which one do you want to work on?"*.

## Rules

- **One single tool call** (except the config first run). No `Read changelog.md`, no opening individual issues, no massive `awk`, no drift detection or recommended-order. If the script fails or returns empty, report it and stop — do not rebuild the analysis by hand.
- If the user later asks for detail on an issue ("tell me more about X"), then yes: `Read docs/issues/open/<X>.md`.

## Installation (reference)

The package is 3 pieces: `todo.md` (this file, the command), `todo_status.py` (the deterministic renderer) and `todo.config.json` (preferences; created by the first run). **Portable by design**: the script has no hardcoded paths — it locates the repo by walking up from `cwd` until it finds `docs/issues/open/` (if none exists, it emits nothing). Installing in another repo = copying the pieces into its `.claude/` + adopting the `docs/issues/` convention (+ `scripts/new-issue.sh` and the "Issue management" section for `CLAUDE.md`, which are the rules that automate closing and changelog).

- **Config**: `{"lang": "en"|"es", "name": "<project>", "session_start": true|false}` in `todo.config.json`. `name` appears in the output title (fallback: repo directory name). Language priority: `--lang xx` flag → config → system `$LANG` → `en`. Frontmatter tokens (`active`/`ready`/`backlog`, field names, priorities) are never translated — they are syntax.
- **Session-start auto-inject**: asked by the first run (step 1) and, if the user accepts, registered as a SessionStart hook in `.claude/settings.json` (step 3 snippet). `session_start` in the config records the choice. To change your mind later: add or remove that `hooks.SessionStart` entry in `settings.json` (or delete `todo.config.json` to relaunch the full setup).
