# /todo — a task manager for solo coders, native to Claude Code

> Markdown issues that live in your repo, a 4-letter command, and zero
> dependencies. The anti-overkill issue tracker. Born in Claude Code; works
> with Codex, Cursor and any AGENTS.md-aware agent
> ([Other agents](#other-agents-codex-cursor-anything-agentsmd-aware)).

Type `/todo` in Claude Code and get this:

```
═══════════════════════════════════════════════════════════
  demo — issues status
═══════════════════════════════════════════════════════════

🎯 Sprint 002-mvp-waitlist — Ship the MVP waitlist (until 2026-07-15)
   ✔ chore-set-up-analytics · epic-launch-mvp [1/2 ✔]
⏭ 003-post-launch-polish (planned) — Post-launch polish · 1 issue

Git: branch=main | working tree: clean

Issues (6 files in docs/issues/open/) — committed: 2 active · 1 ready | uncommitted: 2 backlog · 1 frozen

───────────────────────────────────────────────────────────
 🔨 Active — being worked on now (3)
───────────────────────────────────────────────────────────

  ▸ epic epic-launch-mvp [ALTA] · 1/3 done, F1 active, F2 blocked · QA 1/3 🎯
          Launch-ready MVP
    ├─ ▲ ALTA  [active]  plan-landing-page · 1/2 done, F1 active 🎯
    │                    Landing page + waitlist form
    └─ • MEDIA [ready]   plan-stripe-checkout · ⛓ after plan-landing-page 🎯
                         Stripe checkout + license activation

───────────────────────────────────────────────────────────
 💤 Backlog — future, no commitment (2)
───────────────────────────────────────────────────────────

    • MEDIA plan-dark-mode · ⏭ 003-post-launch-polish
            Dark mode for the dashboard
    · BAJA  bug-mobile-nav-overlap · ⛓ gate: needs a real iOS device to reproduce
            Mobile nav overlaps the header on iOS Safari

───────────────────────────────────────────────────────────
 ❄️ Frozen backlog — awaiting a decision (1)
───────────────────────────────────────────────────────────

    ▲ ALTA  plan-ai-summaries · frozen_by: pricing decision: bundle AI or sell as add-on
            AI-generated weekly summaries
```

Generated from the toy project in [`examples/demo/`](examples/demo/) — run it yourself:

```bash
echo "{\"cwd\":\"$PWD/examples/demo\"}" | python3 hooks/todo_status.py --full --lang en
```

(The `Git:` line shows the branch, working-tree state and last commits of the
enclosing git repo — in your project, yours.)

## What it is

Your issues are **markdown files with YAML frontmatter** inside your own repo
(`docs/issues/open/`, moved to `docs/issues/done/` when closed). A bug, a
multi-phase plan, an epic — all the same model, distinguished by a `type:`
field. Claude Code reads and maintains them following a set of rules you paste
into your `CLAUDE.md`; the `/todo` command renders the whole state
deterministically with a small Python script (stdlib only).

The core idea that makes the listing honest — and the reason this exists
instead of a generic todo list:

- **`status:` measures only commitment**, with 3 values:
  `active` (now) / `ready` (next in queue) / `backlog` (someday, no commitment).
- **Dependencies and freezes are orthogonal fields, not statuses.**
  `blocked_by_closure_of: <slug>` draws a ⛓ chain that disappears by itself when
  the other issue closes — a chained issue in a sprint is still *committed*.
  `frozen_by: "<decision>"` marks backlog items waiting on a strategic decision,
  inherited by an epic's children. No more "blocked" pile mixing *can't start*
  with *won't start yet* with *waiting for me to decide*.
- **Epics** (`type: epic`) group plans/bugs/chores via `parent:` and always
  render as one tree — every child nests under its epic with a `[status]` badge,
  never scattered across status groups. An epic carries its **closure QA** as
  `qa:` items (`pending | pass | fail`), rendered `QA n/m`: it closes when every
  member is closed *and* every item passes; a `fail` names the member that
  fixes it (⚠ if it doesn't), and "all members closed, QA not in pass" is a
  warning, not a closure hint.
- **Sprints open, run and close.** One file per sprint in `docs/issues/sprints/`
  (`NNN-<slug>.md`, `status: planned | active | closed`). Only one is active at
  a time (⚠ if more); its members get 🎯 and closed includes stay listed as the
  record of what it shipped (✔ with `[n/m]` progress). An issue that's decided
  but not for now goes into a `planned` sprint — the queue of what comes next —
  and its line gets a `⏭ <sprint>` tag. When every include is closed the
  renderer tells you: close the sprint, activate the next planned one. Closed
  sprint files stay in the directory as the history.
- The renderer **validates invariants** and prints ⚠ warnings: unknown statuses,
  gates pointing at closed or nonexistent issues, frozen items outside backlog,
  active issues that escaped the sprint, more than one active sprint, planned
  includes already closed.

The full frontmatter reference and the working rules (when to create, how
phases close, the DONE discipline, changelog format) live in
[`templates/issues-rules.md`](templates/issues-rules.md) — that file *is* the
system; the script just renders it.

## Usage

- **`/todo`** — the full listing above. That's it, 4 letters.
- **First run** asks two questions (output language: English/Español, and
  whether to auto-inject the compact status at every session start), writes
  `todo.config.json`, and never asks again.
- **Create an issue**: `scripts/new-issue.sh plan "GSC historical backfill" ALTA`
  — or just describe the task to Claude; the CLAUDE.md rules make it scaffold
  the file for you.
- **Work**: tell Claude "let's work on plan-landing-page". It reads that one
  file — the listing is cheap on context, the detail loads on demand.
- **Close**: when verification is green, Claude proposes the move to `done/`
  plus the changelog entry; you say "ok".

## Install: paste this to your agent

> Look at https://github.com/natanva/solodev-todo-system and set it up in this
> repo following its README install steps (the Claude Code path or the
> other-agents path, whichever fits you). Then show me the status.

That's the whole install for most people — you talk to an agent all day;
installing this is one more sentence. The sections below are the exact steps
your agent will follow, and the manual path if you'd rather copy the files
yourself.

## Install for Claude Code (manual, ~2 minutes)

1. Copy into your repo:
   - `commands/todo.md` → `.claude/commands/todo.md`
   - `hooks/todo_status.py` → `.claude/hooks/todo_status.py`
   - `templates/new-issue.sh` → `scripts/new-issue.sh` (`chmod +x`)
   - `templates/sprints/` → `docs/issues/sprints/` (README + first-sprint template)
2. `mkdir -p docs/issues/open docs/issues/done`
3. Paste [`templates/issues-rules.md`](templates/issues-rules.md) into your
   repo's `CLAUDE.md`.
4. Type `/todo`. Answer the two setup questions. Done.

The script has no hardcoded paths — it finds the repo by walking up from the
current directory until it sees `docs/issues/open/`. No `docs/issues/`? It
prints nothing and exits cleanly.

## Other agents (Codex, Cursor, anything AGENTS.md-aware)

The system is agent-neutral at its core: the issues are plain markdown, the
rules are plain markdown, and the renderer is stdlib Python you can run by
hand — `python3 scripts/todo_status.py --full` works anywhere (the Claude
Code hook plumbing is optional sugar).

1. Copy `hooks/todo_status.py` → `scripts/todo_status.py`, plus
   `templates/new-issue.sh` → `scripts/new-issue.sh` and
   `templates/sprints/` → `docs/issues/sprints/`, and create
   `docs/issues/open` + `docs/issues/done` (same as above).
2. Give your agent the rules — one copy, don't duplicate per agent:
   - **Codex / any AGENTS.md-aware tool**: paste
     [`templates/issues-rules.md`](templates/issues-rules.md) into your
     repo's `AGENTS.md` (or keep it as `docs/issues-rules.md` and add one
     line to `AGENTS.md`: *"Read and follow docs/issues-rules.md"*).
   - **Cursor**: keep the rules as `docs/issues-rules.md` and copy
     [`templates/cursor-issues.mdc`](templates/cursor-issues.mdc) →
     `.cursor/rules/issues.mdc` (an always-on rule that points at them).
3. `/todo` equivalent:
   - **Codex CLI**: copy
     [`templates/codex-todo-prompt.md`](templates/codex-todo-prompt.md) →
     `~/.codex/prompts/todo.md` and invoke it as `/todo`.
   - **Anything else**: the rules file already tells the agent to run the
     renderer and paste its output verbatim when you ask for the status —
     or just run `python3 scripts/todo_status.py --full` yourself.

Language for non-Claude installs: drop a `todo.config.json` next to the
script — `{"lang": "en", "name": "my-project"}` (the interactive first-run
setup is Claude Code-only).

## Why not GitHub Issues?

GitHub Issues + Projects is a fine default for a solo dev — free kanban, custom
fields, `Fixes #123` automation. The trade you make: your issues live in
GitHub's database, not in your repo. This system keeps them as files, which
means:

- **Versioned with the code.** A plan change reviews in the same diff as the
  code that implements it. `git log` is your audit trail.
- **Issues double as design docs.** A 200-line plan with phases, decisions and
  trade-offs is a normal markdown file here; as a GitHub Issue it's an
  unreadable scroll.
- **Agent-native.** Claude reads 40 frontmatters in one local call — no API,
  no MCP round-trips, works offline, zero vendor coupling.
- **Greppable.** `grep -l 'status: ready' docs/issues/open/*.md` is the whole
  query language.

If you want GitHub's kanban UI, nothing here stops you from mirroring later —
the data is just markdown.

## Why not Claude Code's built-in task list?

Claude Code ships native task tools (`TaskCreate`/`TaskUpdate`, Ctrl+T). They
solve a **different problem**: they are the agent's working memory for the
current job — "what am I doing right now, what's next *in this session's
work*". They live in `~/.claude/tasks/` (your home directory, not the repo),
have no priorities, no epics, no sprints, no design-doc bodies, and are
invisible to git.

Use both: the built-in list is scaffolding while executing one issue; this
system is the durable, versioned tracker of the project itself.

## Why not Backlog.md / Jira / Linear / …?

They're built for teams, and it shows: servers, accounts, boards, workflows,
sync. [Backlog.md](https://github.com/MrLesk/Backlog.md) is the closest
relative (markdown tasks in-repo, agent-friendly) and it's good — but it's a
full CLI with a kanban TUI, web UI and its own command surface. This is
deliberately less: **two files, stdlib Python, no CLI to learn, no server, no
account**. If you outgrow it, your data is markdown — migrate anywhere.

## Language

Output is English or Spanish (`todo.config.json`, `--lang`, or `$LANG` — in
that priority order). Display strings are fully translated; frontmatter tokens
(`active`/`ready`/`backlog`, field names, `ALTA`/`MEDIA`/`BAJA` priorities)
are syntax and never translate — the same way `git status` speaks your
language but the command is still `git status`.

> Note: priority tokens are currently `ALTA`/`MEDIA`/`BAJA` (Spanish for
> high/medium/low) — a legacy of the project this was extracted from. Open
> question before v1: keep, rename, or accept both.

## Repo layout

```
commands/todo.md          # the /todo slash command (instructions for Claude)
hooks/todo_status.py      # deterministic renderer — the only executable piece
templates/
  issues-rules.md         # the system's rules — CLAUDE.md / AGENTS.md / docs/
  cursor-issues.mdc       # Cursor always-on rule pointing at the rules file
  codex-todo-prompt.md    # /todo as a Codex CLI custom prompt
  new-issue.sh            # issue scaffolder
  sprints/                # sprints directory template (README + first sprint)
examples/demo/            # toy project used to generate the README output
```

## Status

Working and in daily use — extracted from a private production repo where it
tracks ~80 issues across epics, sprints and a changelog. MIT licensed.

---

If this system saves you time, a ⭐ on the repo helps other solo devs find it.
