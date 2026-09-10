---
goal:
ends:
includes:
---
# Current sprint

> No active sprint. Fill in `goal` + `includes` (+ optional `ends`) to start one;
> the `todo_status.py` renderer shows it as a banner on top of `/todo` and marks
> the included issues with 🎯.
>
> There is only **one** sprint at a time — this file is not a history. Closed
> includes stay listed as the record of what the sprint shipped (the renderer
> paints them ✔ and counts progress `[n/m]`). When every include is closed the
> sprint is complete: review it, then write the next one over this file. The
> between-sprints history lives in your changelog and in
> `git log docs/issues/sprint.md`.

## Fields

- **`goal`** — the sprint goal (free text).
- **`ends`** — estimated end date `YYYY-MM-DD`. Optional.
- **`includes`** — slugs (without `.md`) of the committed **issues**: plans, epics,
  bugs or chores. Direct children of an included epic count as part of the sprint
  even if not listed (the renderer marks them 🎯 too).

## Invariants (the renderer watches these and prints ⚠)

- Every include must exist in `open/` (as `active`/`ready`) or in `done/` — an
  include in `backlog` is a contradiction: promote it or drop it from the sprint.
- **A closed include is NOT removed from the sprint**: it stays as the record of
  what the sprint shipped (the renderer paints it ✔ and counts progress). The
  sprint completes when every include is closed; then you review it and write
  the next one (this file keeps no history between sprints — the review lives
  in the changelog and `git log docs/issues/sprint.md`).
- With an active sprint, every `active` issue must belong to the sprint (an
  include or a direct child of one); otherwise demote it to `ready` or include it.
