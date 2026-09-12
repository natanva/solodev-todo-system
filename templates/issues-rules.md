# Issue & changelog management (agent-neutral rules)

> Paste this file's content into your agent's instructions file — `CLAUDE.md`
> (Claude Code), `AGENTS.md` (Codex and other AGENTS.md-aware tools) — or keep
> it as `docs/issues-rules.md` and point your agent at it (Cursor rule,
> one-line reference). One copy is the source of truth; don't duplicate it
> per agent.

> **One single model: `issue`.** Bug, multi-phase plan, feature, chore — all of them are files in `docs/issues/`. What distinguishes them is the frontmatter `type:` field. What groups them is the `parent:` field. What tracks state is the directory (`open/` vs `done/`) + the `phases:` array for multi-phase work. Inspired by PEPs / KEPs / RFCs / ADRs.

## Structure

| Directory | Content |
|-----------|---------|
| `docs/issues/open/` | Open issues. Sub-divided by the frontmatter `status:` — not by subdirectory. |
| `docs/issues/sprints/` | **Sprints**, one file per sprint (`NNN-<slug>.md`) with `status: planned \| active \| closed` + `goal` + `includes` (committed slugs). **Only one `active`** (the renderer prints ⚠ if there are more); `planned` sprints are the queue of what comes next (the renderer paints them ⏭ and tags their issues); `closed` sprints stay as history. Full frontmatter and lifecycle in `docs/issues/sprints/README.md`. |
| `docs/issues/done/` | Closed issues (prefixed `YYYY-MM_`) |
| `docs/changelog.md` | Chronological narrative of significant changes |

**Filename**: `<type>-<slug>.md` in `open/`, `YYYY-MM_<type>-<slug>.md` in `done/`. Types: `bug`, `feature`, `chore`, `plan` (work with its own phases), `epic` (container grouping plans/bugs/chores via `parent:`).

## Frontmatter

```yaml
---
type: bug | feature | chore | plan | epic
status: active | ready | backlog              # commitment ONLY, orthogonal to priority
priority: ALTA | MEDIA | BAJA                 # importance/severity (high | medium | low)
created: YYYY-MM-DD
completed: YYYY-MM-DD          # only when closed, in issues/done/
parent: <slug-without-md>      # optional: grouping under an epic (or parent issue)
supersedes: <slug-without-md>  # optional: this issue replaces another
superseded_by: <slug>          # optional: this issue was made obsolete by another
blocked_by_closure_of: <slug>  # optional, ORTHOGONAL to status: depends on another issue closing
blocked_by: "<text>"           # optional, orthogonal: external gate not representable as an issue (cross-repo, third party)
frozen_by: "<decision>"        # optional, ONLY with backlog: frozen awaiting a decision; on an epic it is inherited by its children
external_refs:                  # optional: cross-repo references
  - "other-repo#bug-cpu-bound"
phases:                         # optional: for type=plan|epic with multiple phases
  - {id: F0, status: done, closed: YYYY-MM-DD}
  - {id: F1, status: active}
  - {id: F2, status: blocked, blocked_by: F1}
qa:                             # optional: an epic's closure QA (allowed on plan), one item per line
  - {id: Q1, text: "<what is tested>", status: pass, checked: YYYY-MM-DD}
  - {id: Q2, text: "<what is tested>", status: fail, checked: YYYY-MM-DD, issue: <slug-of-the-member-that-fixes-it>}
  - {id: Q3, text: "<what is tested>", status: pending}
---
```

**`status:` measures ONLY commitment** — 3 values. Dependencies and freezes are NOT statuses: they are orthogonal fields that can occur at any commitment level (e.g. A→B→C chained inside the same sprint, all three `ready`/`active`).
- `active` — work in progress right now. If there is an active sprint, it must belong to it (an include or a direct child of one).
- `ready` — committed, next in the queue. May have pending dependencies (`blocked_by_closure_of`) — it is still ready: the ⛓ chain shows the order, it does not downgrade the commitment.
- `backlog` — **future without commitment**: "I'll do this someday, when I decide to activate it". **Default for new issues.**

**Orthogonal gate/freeze fields** (the renderer prints and validates them):
- `blocked_by_closure_of: <slug>` — this issue waits for another one to close. Rendered `⛓ after <slug>` while the slug is still in `open/`; once it lands in `done/` the gate is satisfied and a cleanup warning is emitted. Pointing at a nonexistent slug is ⚠.
- `blocked_by: "<text>"` — external gate that is not an issue (cross-repo dependency, third-party verification). Rendered `⛓ gate: <text>`.
- `frozen_by: "<decision>"` — only meaningful in `backlog`: frozen awaiting a strategic decision (the unblocking trigger). On an `epic` it also freezes its backlog children (single source of truth: the field lives only on the epic). `frozen_by` on active/ready is a contradiction (⚠).

**`priority:` (severity/importance, orthogonal to status):** ALTA/MEDIA/BAJA (high/medium/low — these are frontmatter tokens). A plan can be `backlog + ALTA` (important but not now) or `active + BAJA` (in progress but low-stakes).

`phases[].status ∈ {done, active, blocked, pending, superseded}`. **Each phase's status is source of truth in the frontmatter, NOT in body prose.** The body describes what was done and why. Phase-level `blocked`/`blocked_by:` is the plan's internal vocabulary (it references phase IDs, e.g. `blocked_by: C1`) and does not collide with the issue-level fields (which reference slugs).

`qa[].status ∈ {pending, pass, fail}` — an epic's **closure QA**: the list of what you check by using the product to accept the epic. **Source of truth in the frontmatter, not a checklist in the body.** The renderer prints `QA n/m` next to the epic, `⚠` when a `fail` names no `issue:`, and a "QA pending" warning when every member is closed but the QA is not in pass. The cycle is explicit: QA `fail` » new member (referenced in `issue:`) » member closed » QA again » `pass` » epic closed. A "live test of …" chore as a member is no longer the pattern.

## Automatic rules (execute WITHOUT the user asking)

**When designing a new idea or receiving a bug**:
- `scripts/new-issue.sh <type> "<title>" [priority]` creates the file in `docs/issues/open/` with minimal scaffolding.
- Do not create loose `.md` tracking files in the repo root.

**When starting implementation**: the file is already in `open/` — it does not move between directories; raise its `status:` (backlog → ready when committing to it, ready → active when starting it) and, if there is an active sprint, add it to its `includes` in `docs/issues/sprints/`.

**Sprint lifecycle** (details in `docs/issues/sprints/README.md`): an issue that is decided but not for now goes into the `includes` of a `planned` sprint. A closed include is NOT removed from the sprint (it stays as the ✔ record). When every include of the active sprint is closed, the renderer tells you: review it, set `status: closed` + `closed: YYYY-MM-DD`, and activate the next `planned` one (`status: active` + `opened:`). Unfinished includes move explicitly (your decision) to the next sprint or back to backlog.

**When completing a phase**:
- Update `phases[].status: done` and `closed: YYYY-MM-DD` in the frontmatter.
- Do NOT write "Status: DONE" in the section body. Body = narrative prose (what, why, commits).

**When running an epic's QA**:
- Run it **in the target environment after deploy** (never local-only when the project has a production step — same rule as closing issues).
- Each item: `status: pass | fail` + `checked: YYYY-MM-DD`. A `fail` opens a new member (`parent: <epic>`) and references it in `issue:`; no patching on the spot.

**When closing a whole issue (move to `done/`)**:

> **DONE = objective evidence + user agreement.** Three conditions:
> 1. Verification passes in the target environment without failures (or the failure is diagnosed as a verifier bug, not a system bug).
> 2. Declared manual checks (in the verifier or the body) are covered — confirmed, or accepted as deferred to a new issue.
> 3. The user does not object when presented with the closure.
>
> No ritual phrase required. If verification is green and manual checks are covered, the agent proposes the concrete move (which issues, which changelog entries, which new issues for deferred items) and the user confirms with a generic OK or vetoes. Local-only verification never closes an issue when the project has a production/deploy step.

Closure steps:
1. `git mv docs/issues/open/<type>-<slug>.md docs/issues/done/YYYY-MM_<type>-<slug>.md`
2. Add `completed: YYYY-MM-DD` to the frontmatter.
3. If the issue had `phases:`, all of them must be `status: done` or `superseded` before the move.
4. **Sub-issues check**: if other issues in `open/` have `parent: <this>`, they are orphaned children — re-evaluate them (close too, reparent, or promote to top-level) before closing the parent.
5. **QA check (epics)**: an epic closes when every member is closed or reparented **and** every `qa:` item is in `pass`. While any item is not in pass, the renderer does not suggest closing it.
6. Add an entry to `docs/changelog.md`.

**When making a commit that advances or closes an issue**:
1. Update the issue's frontmatter (phase status, completed, etc.).
2. If the commit closes the issue, run the closure flow above.
3. Add an entry to `docs/changelog.md`.

## Changelog format

`docs/changelog.md` — newest entries on top:

```markdown
## [YYYY-MM-DD] Short title
**Issue:** `docs/issues/done/YYYY-MM_<type>-<slug>.md` (if applicable)
**Commits:** abc1234..def5678

Description of what was done and why.
- Change 1
- Change 2
```

## FORBIDDEN

- Creating loose `.md` files for work tracking in the repo root or ad-hoc folders. Always `docs/issues/`.
- Phase status in body prose (`**Status:** ✅ DONE`) — it duplicates the frontmatter and drifts. Body = what/why/commits; frontmatter = structured status.
- Closing an issue (`open/ → done/`) without updating `phases[].status` and `completed:` in the frontmatter.
- Closing an issue with orphaned sub-issues in `open/` (`parent:` pointing at something already in `done/`).
- Closing an epic with `qa:` items outside `pass`, or running a QA local-only instead of in the target environment.
- Closing an issue without the 3 closure conditions (green verification + manual checks covered + user agreement).
- Making commits that close features without updating the changelog.

## The status listing (any agent)

When the user asks for the issues status ("todo", "/todo", "status of the
issues"), run the deterministic renderer and show its output **complete and
verbatim** inside a single ``` block — never summarize, trim, reorder or
reformat it; each line exactly as printed:

```bash
python3 scripts/todo_status.py --full
```

(Path per install: `scripts/todo_status.py` in the generic install,
`.claude/hooks/todo_status.py` in the Claude Code install.) Options: `--lang
en|es`; a `todo.config.json` next to the script (`{"lang": "en", "name":
"<project>"}`) sets defaults. If it prints nothing, the repo has no
`docs/issues/` layout — say so and stop; do not rebuild the analysis by hand.
