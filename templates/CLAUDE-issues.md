# Issue & changelog management (paste into your CLAUDE.md)

> **One single model: `issue`.** Bug, multi-phase plan, feature, chore — all of them are files in `docs/issues/`. What distinguishes them is the frontmatter `type:` field. What groups them is the `parent:` field. What tracks state is the directory (`open/` vs `done/`) + the `phases:` array for multi-phase work. Inspired by PEPs / KEPs / RFCs / ADRs.

## Structure

| Directory | Content |
|-----------|---------|
| `docs/issues/open/` | Open issues. Sub-divided by the frontmatter `status:` — not by subdirectory. |
| `docs/issues/sprint.md` | **Current sprint** (a single one, not a history): `goal` + optional `ends` + `includes` (committed slugs). Source of truth for "what we are focused on now"; the renderer shows it above `/todo` and marks included issues 🎯. |
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

## Automatic rules (execute WITHOUT the user asking)

**When designing a new idea or receiving a bug**:
- `scripts/new-issue.sh <type> "<title>" [priority]` creates the file in `docs/issues/open/` with minimal scaffolding.
- Do not create loose `.md` tracking files in the repo root.

**When starting implementation**: the file is already in `open/` — it does not move between directories; raise its `status:` (backlog → ready when committing to it, ready → active when starting it) and, if there is a sprint, add it to `includes` in `sprint.md`.

**When completing a phase**:
- Update `phases[].status: done` and `closed: YYYY-MM-DD` in the frontmatter.
- Do NOT write "Status: DONE" in the section body. Body = narrative prose (what, why, commits).

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
5. Add an entry to `docs/changelog.md`.

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
- Closing an issue without the 3 closure conditions (green verification + manual checks covered + user agreement).
- Making commits that close features without updating the changelog.
