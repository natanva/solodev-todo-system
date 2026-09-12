# Sprints

One file per sprint: `NNN-<slug>.md`. The numeric prefix is the queue order.
This directory IS the history: closed sprints stay here as the archive (the
renderer does not paint them).

## Frontmatter

```yaml
---
status: planned | active | closed
goal: "<the sprint goal, free text>"
opened: YYYY-MM-DD     # when activated
ends: YYYY-MM-DD       # estimated end, optional
closed: YYYY-MM-DD     # when closed
includes:              # slugs (without .md) of the committed issues
  - <slug>
---
```

Direct children of an included epic count as part of the sprint even if not
listed (the renderer marks them 🎯 too).

## Lifecycle

1. **Plan**: create `NNN-<slug>.md` with `status: planned` and its
   `includes`. An issue that is decided but not for now goes here (the
   renderer tags its line with `⏭ NNN-<slug>`). Several planned sprints can
   queue up.
2. **Activate**: `status: active` + `opened:`. **Only one can be active**
   (the renderer prints ⚠ if there are more). Its members get 🎯 and the
   issues you start move to `status: active` in their own frontmatter.
3. **Work**: a closed include is NOT removed from the sprint — it stays as
   the record of what the sprint shipped (✔ with `[n/m]` progress).
4. **Close**: when every include is closed (the renderer tells you), review
   the sprint, set `status: closed` + `closed:`, and activate the next
   planned one. An unfinished include moves **explicitly** (your decision)
   to the next sprint or back to backlog — never silently. A sprint that
   includes an epic does not close until the epic's `qa:` is in pass: the
   epic only moves to `done/` then (see the rules file).

## Invariants (the renderer watches these and prints ⚠)

- At most one `active` sprint.
- Every include of the active sprint exists in `open/` (as `active`/`ready`)
  or in `done/`; an include in `backlog` is a contradiction.
- With an active sprint, every `active` issue must belong to it.
- An include of a `planned` sprint may sit in `backlog` (planned IS the
  parking with a destination), but it cannot be already closed or missing.
