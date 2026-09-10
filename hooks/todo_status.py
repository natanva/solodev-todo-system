#!/usr/bin/env python3
"""todo_status.py — issue status renderer for the /todo command.

Reads docs/issues/open/*.md frontmatter + docs/issues/sprint.md + recent git
log and writes a status block grouped by `status:`. Consumed by the /todo
slash command (`--full`). It can OPTIONALLY be registered as a SessionStart
hook (compact mode, no flags) to auto-inject the status into the model's
context on every session — see the install notes in .claude/commands/todo.md;
it is a per-user choice because it spends tokens on sessions that may not
need it.

Model (2026-07-02): `status:` measures ONLY commitment — 3 values:

- active  — being worked on now (if a sprint exists, must belong to it).
- ready   — committed, next in the queue. May have pending dependencies.
- backlog — future, no commitment. Default.

Dependencies and freezes are fields ORTHOGONAL to status, not statuses:

- blocked_by_closure_of: <slug> — depends on another issue closing. Rendered as
  a chain `⛓ after <slug>` while the slug is still in open/; once it lands in
  done/ the gate is satisfied and a cleanup warning is emitted.
- blocked_by: "<text>" — external gate not representable as an issue
  (cross-repo, third party).
- frozen_by: "<decision>" — only with status backlog: frozen awaiting a
  decision. On an epic it is inherited by its backlog children. Splits the
  backlog into two sub-groups in the render.

Epics: `type: epic` (explicit, no longer inferred from `parent:`). An epic
groups plans/bugs/chores via `parent:` and renders as `▸ epic` with its
children nested. An epic always renders as ONE piece: every child nests under
the epic header in the EPIC's group, whatever the child's own `status:` — a
`[status]` badge on each child carries what the group no longer implies.
Children of an epic never render in their own status group.

The sprint (sprint.md) shows as a banner on top and its members (includes +
direct children of an included epic) are marked 🎯. Invariants are validated
and rendered as ⚠ (unknown status, frozen_by outside backlog, broken or
already-closed gates, sprint includes in backlog, active outside the sprint).

Language: display strings live in MESSAGES (en/es). Frontmatter tokens
(active/ready/backlog, field names, phase statuses, priorities) are syntax
and are never translated. Resolution order: `--lang xx` flag → "lang" in
todo.config.json (next to this script) → $LANG env var → en.

Failure mode: any parse/git error → exit 0 silently. A broken status block
must never break /todo or session start.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Resolved at runtime from the payload's cwd (find_repo) — no hardcoded paths,
# so the same script works in any repo that follows the docs/issues/ layout.
REPO: Path | None = None
ISSUES_OPEN: Path | None = None
ISSUES_DONE: Path | None = None
SPRINT_FILE: Path | None = None
PROJECT_NAME = ""
CONFIG_FILE = Path(__file__).resolve().parent / "todo.config.json"


def find_repo(cwd: str) -> Path | None:
    """Walk up from cwd to the first directory containing docs/issues/open/."""
    try:
        p = Path(cwd).resolve()
    except Exception:
        return None
    for cand in (p, *p.parents):
        if (cand / "docs/issues/open").is_dir():
            return cand
    return None

PRIORITY_ORDER = {"ALTA": 0, "MEDIA": 1, "BAJA": 2, "": 3}
STATUS_ORDER = {"active": 0, "ready": 1, "backlog": 2}
KNOWN_STATUSES = ("active", "ready", "backlog")
GROUP_ORDER = ("active", "ready", "backlog", "frozen", "unknown")
SPRINT_MARK = "🎯"
CHAIN_MARK = "⛓"
FRAME = "═" * 59
RULE = "─" * 59
# Priority glyphs: shape+density convey rank in any monospace terminal
# (▲ jumps out, · sinks). The token text stays — it is frontmatter syntax.
PRIO_GLYPH = {"ALTA": "▲", "MEDIA": "•", "BAJA": "·"}

MESSAGES = {
    "en": {
        "title": "{name} — issues status",
        "git_line": "Git: branch={branch} | working tree: {status}",
        "tree_clean": "clean",
        "files_modified": "{n} files modified",
        "last_commits": "Last commits:",
        "sprint_head": "🎯 Current sprint",
        "sprint_until": " (until {ends})",
        "counts_line": "Issues ({n} files in docs/issues/open/) — {parts}",
        "counts_committed": "committed: {s}",
        "counts_uncommitted": "uncommitted: {s}",
        "counts_unclassified": "⚠ {n} unclassified",
        "count_active": "active",
        "count_ready": "ready",
        "count_backlog": "backlog",
        "count_frozen": "frozen",
        "group_active": "🔨 Active — being worked on now",
        "group_ready": "⏭ Ready — committed, next in the queue",
        "group_backlog": "💤 Backlog — future, no commitment",
        "group_frozen": "❄️ Frozen backlog — awaiting a decision",
        "group_unknown": "⚠️ Unknown status (use active | ready | backlog)",
        "chain_after": "⛓ after {slug}",
        "chain_gate": "⛓ gate: {text}",
        "no_epic_group": "  (no epic in this group):",
        "more_media": "    + {n} MEDIA (/todo to list them)",
        "more_baja": "    + {n} BAJA",
        "frozen_children": " (+{n} children)",
        "frozen_rest": "    + {n} standalone (/todo to list them)",
        "inconsistencies": "  ⚠ Inconsistencies:",
        "warn_gate_done": "{name}: gate '{tgt}' is already in done/ — clean up blocked_by_closure_of",
        "warn_gate_unknown": "{name}: blocked_by_closure_of points to unknown slug '{tgt}'",
        "warn_frozen_status": "{name}: frozen_by with status '{st}' — frozen only applies to backlog",
        "warn_parent_missing": "{name}: parent '{p}' does not exist in open/ — reparent or close",
        "warn_unknown_status": "{name}: unknown status '{st}' — use active|ready|backlog",
        "warn_sprint_missing": "sprint: include '{slug}' exists in neither open/ nor done/ — typo? update sprint.md",
        "sprint_complete": "   ✔ every include is closed — sprint complete: review it, then write the next one in sprint.md",
        "warn_sprint_backlog": "sprint: include '{slug}' is in backlog — promote to ready/active or drop it from the sprint",
        "warn_active_no_sprint": "{name}: active but outside the sprint — include it or demote to ready",
        "warn_backlog_progress": "{name}: {n} phase(s) done but status backlog — work has started; promote to ready/active or supersede the remaining phases",
        "files_of_record": "Files of record: docs/issues/open/, docs/issues/sprint.md, docs/issues/done/, docs/changelog.md",
        "dig_deeper": "To dig deeper: read the issue file. `ls docs/issues/open/` is the index; `grep -l 'status: ready' docs/issues/open/*.md` to filter.",
    },
    "es": {
        "title": "{name} — estado de issues",
        "git_line": "Git: rama={branch} | árbol de trabajo: {status}",
        "tree_clean": "limpio",
        "files_modified": "{n} archivos modificados",
        "last_commits": "Últimos commits:",
        "sprint_head": "🎯 Sprint actual",
        "sprint_until": " (hasta {ends})",
        "counts_line": "Issues ({n} archivos en docs/issues/open/) — {parts}",
        "counts_committed": "comprometidos: {s}",
        "counts_uncommitted": "sin compromiso: {s}",
        "counts_unclassified": "⚠ {n} sin clasificar",
        "count_active": "activos",
        "count_ready": "listos",
        "count_backlog": "en backlog",
        "count_frozen": "congelados",
        "group_active": "🔨 Activos — en trabajo ahora",
        "group_ready": "⏭ Listos — comprometidos, siguientes en la cola",
        "group_backlog": "💤 Backlog — futuro sin compromiso",
        "group_frozen": "❄️ Backlog congelado — esperando una decisión",
        "group_unknown": "⚠️ Status desconocido (usa active | ready | backlog)",
        "chain_after": "⛓ tras {slug}",
        "chain_gate": "⛓ bloqueado por: {text}",
        "no_epic_group": "  (sin epic en este grupo):",
        "more_media": "    + {n} MEDIA (/todo para verlos)",
        "more_baja": "    + {n} BAJA",
        "frozen_children": " (+{n} hijos)",
        "frozen_rest": "    + {n} sueltos (/todo para verlos)",
        "inconsistencies": "  ⚠ Inconsistencias:",
        "warn_gate_done": "{name}: el gate '{tgt}' ya está en done/ — limpia blocked_by_closure_of",
        "warn_gate_unknown": "{name}: blocked_by_closure_of apunta a un slug inexistente '{tgt}'",
        "warn_frozen_status": "{name}: frozen_by con status '{st}' — frozen solo aplica a backlog",
        "warn_parent_missing": "{name}: el parent '{p}' no existe en open/ — reparentar o cerrar",
        "warn_unknown_status": "{name}: status desconocido '{st}' — usa active|ready|backlog",
        "warn_sprint_missing": "sprint: el include '{slug}' no existe ni en open/ ni en done/ — ¿typo? actualiza sprint.md",
        "sprint_complete": "   ✔ todos los includes están cerrados — sprint completo: repásalo y escribe el siguiente en sprint.md",
        "warn_sprint_backlog": "sprint: el include '{slug}' está en backlog — súbelo a ready/active o sácalo del sprint",
        "warn_active_no_sprint": "{name}: activo pero fuera del sprint — inclúyelo o bájalo a ready",
        "warn_backlog_progress": "{name}: {n} fase(s) done pero status backlog — hay trabajo empezado; súbelo a ready/active o marca superseded lo que quede",
        "files_of_record": "Archivos de referencia: docs/issues/open/, docs/issues/sprint.md, docs/issues/done/, docs/changelog.md",
        "dig_deeper": "Para profundizar: lee el archivo del issue. `ls docs/issues/open/` es el índice; `grep -l 'status: ready' docs/issues/open/*.md` para filtrar.",
    },
}


def read_config() -> dict:
    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def resolve_lang(argv: list[str], cfg: dict) -> str:
    """--lang flag → todo.config.json → $LANG → en."""
    for i, a in enumerate(argv):
        if a == "--lang" and i + 1 < len(argv):
            return argv[i + 1] if argv[i + 1] in MESSAGES else "en"
        if a.startswith("--lang="):
            v = a.split("=", 1)[1]
            return v if v in MESSAGES else "en"
    v = cfg.get("lang", "")
    if v in MESSAGES:
        return v
    env = os.environ.get("LANG", "")
    if env.lower().startswith("es"):
        return "es"
    return "en"


LANG = "en"


def t(key: str, **kw) -> str:
    msg = MESSAGES.get(LANG, MESSAGES["en"]).get(key) or MESSAGES["en"][key]
    return msg.format(**kw) if kw else msg


def parse_frontmatter(text: str) -> dict | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    block = text[4:end]
    fields: dict[str, str | list] = {}
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line or line.startswith("#"):
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if val == "" and i + 1 < len(lines) and lines[i + 1].lstrip().startswith("-"):
            items: list[str] = []
            j = i + 1
            while j < len(lines) and lines[j].lstrip().startswith("-"):
                items.append(lines[j].lstrip()[1:].strip())
                j += 1
            fields[key] = items
            i = j
            continue
        fields[key] = val
        i += 1
    return fields


PHASE_STATUS_RE = re.compile(r"\bstatus:\s*(done|active|blocked|pending|superseded)\b")


def summarize_phases(phases_raw: list[str] | str | None) -> tuple[str, int]:
    """(human summary, done-phase count) from the `phases:` frontmatter list."""
    if not phases_raw or isinstance(phases_raw, str):
        return "", 0
    counts = {"done": 0, "active": 0, "blocked": 0, "pending": 0, "superseded": 0}
    active_ids: list[str] = []
    blocked_ids: list[str] = []
    for item in phases_raw:
        m = PHASE_STATUS_RE.search(item)
        st = m.group(1) if m else "pending"
        counts[st] = counts.get(st, 0) + 1
        id_m = re.search(r"\bid:\s*([A-Za-z0-9.]+)", item)
        pid = id_m.group(1) if id_m else "?"
        if st == "active":
            active_ids.append(pid)
        elif st == "blocked":
            blocked_ids.append(pid)
    total = sum(counts.values())
    if total == 0:
        return "", 0
    # Phase statuses are frontmatter tokens — never translated.
    parts = [f"{counts['done']}/{total} done"]
    if active_ids:
        parts.append(f"{','.join(active_ids)} active")
    if blocked_ids:
        parts.append(f"{','.join(blocked_ids)} blocked")
    return ", ".join(parts), counts["done"]


def extract_h1(text: str) -> str:
    """First `# Heading` line after the frontmatter, truncated to 90 chars."""
    body_start = text.find("\n---", 4)
    if body_start < 0:
        return ""
    body = text[body_start + 4:]
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("# "):
            h1 = line[2:].strip()
            return h1 if len(h1) <= 90 else h1[:87].rstrip() + "..."
    return ""


def _str_field(fm: dict, key: str) -> str:
    val = fm.get(key)
    if not isinstance(val, str):
        return ""
    return val.strip().strip('"').strip("'")


def read_issue(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    fm = parse_frontmatter(text)
    if not fm:
        return None
    phases_summary, phases_done = summarize_phases(fm.get("phases"))
    return {
        "name": path.stem,
        "type": _str_field(fm, "type") or "plan",
        "status": _str_field(fm, "status") or "backlog",
        "priority": _str_field(fm, "priority") or "MEDIA",
        "phases_summary": phases_summary,
        "phases_done": phases_done,
        "parent": _str_field(fm, "parent"),
        "blocked_by_closure_of": _str_field(fm, "blocked_by_closure_of"),
        "blocked_by": _str_field(fm, "blocked_by"),
        "frozen_by": _str_field(fm, "frozen_by"),
        "h1": extract_h1(text),
    }


def collect_open_issues() -> list[dict]:
    if not ISSUES_OPEN.is_dir():
        return []
    out = []
    for p in sorted(ISSUES_OPEN.glob("*.md")):
        info = read_issue(p)
        if info:
            out.append(info)
    return out


def closed_in_done(slug: str) -> bool:
    """True if the slug's file exists in done/ (with its YYYY-MM_ prefix)."""
    try:
        return any(ISSUES_DONE.glob(f"*_{slug}.md"))
    except Exception:
        return False


def read_sprint() -> dict | None:
    """Parse docs/issues/sprint.md → {goal, ends, includes:set}. None if absent."""
    try:
        text = SPRINT_FILE.read_text(encoding="utf-8")
    except Exception:
        return None
    fm = parse_frontmatter(text) or {}
    inc = fm.get("includes") or []
    if isinstance(inc, str):
        inc = [inc] if inc.strip() else []
    includes = {i.strip().strip('"').strip("'") for i in inc if i.strip()}
    goal = fm.get("goal") if isinstance(fm.get("goal"), str) else ""
    ends = fm.get("ends") if isinstance(fm.get("ends"), str) else ""
    goal = goal.strip().strip('"').strip("'")
    ends = ends.strip().strip('"').strip("'")
    if not (includes or goal):
        return None
    return {"goal": goal, "ends": ends, "includes": includes}


def git_snapshot() -> tuple[str, str, list[str]]:
    try:
        branch = subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=3,
        ).stdout.strip()
    except Exception:
        branch = "?"
    try:
        status = subprocess.run(
            ["git", "-C", str(REPO), "status", "--short"],
            capture_output=True, text=True, timeout=3,
        ).stdout.strip()
        dirty = len([l for l in status.splitlines() if l.strip()])
        status_summary = t("files_modified", n=dirty) if dirty else t("tree_clean")
    except Exception:
        status_summary = "?"
    try:
        log = subprocess.run(
            ["git", "-C", str(REPO), "log", "--oneline", "-5"],
            capture_output=True, text=True, timeout=3,
        ).stdout.strip().splitlines()
    except Exception:
        log = []
    return branch, status_summary, log


def annotate(issues: list[dict], sprint: dict | None) -> tuple[list[str], set[str]]:
    """Compute per-issue render annotations + invariant warnings.

    Sets on each issue: `chain` (⛓ markers), `frozen_eff` (own or inherited
    frozen_by), `group` (render bucket). Returns (warnings, sprint_slugs) where
    sprint_slugs = includes ∪ direct children of included epics.
    """
    warnings: list[str] = []
    open_slugs = {it["name"] for it in issues}
    by_name = {it["name"]: it for it in issues}

    for it in issues:
        chain: list[str] = []
        tgt = it["blocked_by_closure_of"]
        if tgt:
            if tgt in open_slugs:
                chain.append(t("chain_after", slug=tgt))
            elif closed_in_done(tgt):
                warnings.append(t("warn_gate_done", name=it["name"], tgt=tgt))
            else:
                warnings.append(t("warn_gate_unknown", name=it["name"], tgt=tgt))
        if it["blocked_by"]:
            chain.append(t("chain_gate", text=it["blocked_by"]))
        it["chain"] = chain

        frozen = it["frozen_by"]
        if not frozen and it["parent"]:
            parent = by_name.get(it["parent"])
            if parent:
                frozen = parent["frozen_by"]
        it["frozen_eff"] = frozen if it["status"] == "backlog" else ""

        if it["frozen_by"] and it["status"] != "backlog":
            warnings.append(t("warn_frozen_status", name=it["name"], st=it["status"]))
        if it["parent"] and it["parent"] not in open_slugs:
            warnings.append(t("warn_parent_missing", name=it["name"], p=it["parent"]))

        if it["status"] not in KNOWN_STATUSES:
            it["group"] = "unknown"
            warnings.append(t("warn_unknown_status", name=it["name"], st=it["status"]))
        elif it["frozen_eff"]:
            it["group"] = "frozen"
        else:
            it["group"] = it["status"]

        # Started work parked without commitment is a contradiction: done
        # phases mean the plan is in motion. (frozen is exempt — that park
        # is a deliberate decision.)
        if it["group"] == "backlog" and it["phases_done"]:
            warnings.append(t("warn_backlog_progress", name=it["name"], n=it["phases_done"]))

    sprint_slugs: set[str] = set()
    if sprint:
        sprint_slugs = set(sprint["includes"])
        for it in issues:
            if it["parent"] in sprint["includes"]:
                sprint_slugs.add(it["name"])
        for slug in sprint["includes"]:
            if slug not in open_slugs:
                # A closed include stays in sprint.md as the record of what the
                # sprint shipped (banner paints it ✔); warn only on a slug that
                # exists nowhere.
                if not closed_in_done(slug):
                    warnings.append(t("warn_sprint_missing", slug=slug))
            elif by_name[slug]["status"] == "backlog":
                warnings.append(t("warn_sprint_backlog", slug=slug))
        for it in issues:
            if it["status"] == "active" and it["name"] not in sprint_slugs:
                warnings.append(t("warn_active_no_sprint", name=it["name"]))

    return warnings, sprint_slugs


def render_item(it: dict, connector: str | None = None,
                sprint: set | None = None, show_status: bool = False) -> str:
    """One issue line: priority glyph, slug, extras (phases/chains/frozen/parent), h1.

    `connector` is set for children rendered beneath their epic header
    ("mid"/"last" tree branch); it also suppresses the `parent:` extra — the
    header already conveys it. `show_status` prefixes the child's own
    `[status]` badge: children render under their epic whatever their status,
    so the surrounding group no longer implies it.
    """
    extras = []
    if it["phases_summary"]:
        extras.append(it["phases_summary"])
    extras.extend(it.get("chain", []))
    if it["frozen_by"]:
        extras.append(f"frozen_by: {it['frozen_by']}")
    if it["parent"] and connector is None:
        extras.append(f"parent: {it['parent']}")
    extra_str = " · " + " · ".join(extras) if extras else ""
    mark = f" {SPRINT_MARK}" if sprint and it["name"] in sprint else ""
    prio = f"{PRIO_GLYPH.get(it['priority'], '•')} {it['priority']:<5}"
    badge = f"[{it['status']}]".ljust(10) if show_status else ""
    if connector == "mid":
        head, cont = "    ├─ ", "    │          "
    elif connector == "last":
        head, cont = "    └─ ", "               "
    else:
        head, cont = "    ", "            "
    if badge:
        cont += " " * 10
    line1 = f"{head}{prio} {badge}{it['name']}{extra_str}{mark}"
    if it.get("h1"):
        return line1 + f"\n{cont}{it['h1']}"
    return line1


def render_epic_header(it: dict, sprint: set | None = None) -> str:
    """Header line for a `type: epic` issue: `  ▸ epic <slug> [PRIO] · extras`."""
    extras = []
    if it["phases_summary"]:
        extras.append(it["phases_summary"])
    extras.extend(it.get("chain", []))
    if it["frozen_by"]:
        extras.append(f"frozen_by: {it['frozen_by']}")
    extra_str = " · " + " · ".join(extras) if extras else ""
    tag = f" [{it['priority']}]" if it["priority"] else ""
    mark = f" {SPRINT_MARK}" if sprint and it["name"] in sprint else ""
    line1 = f"  ▸ epic {it['name']}{tag}{extra_str}{mark}"
    if it.get("h1"):
        return line1 + f"\n          {it['h1']}"
    return line1


def ksort(lst: list[dict]) -> list[dict]:
    """Children under an epic: queue order — status first, then priority."""
    return sorted(lst, key=lambda x: (STATUS_ORDER.get(x["status"], 9),
                                      PRIORITY_ORDER.get(x["priority"], 9), x["name"]))


def render_section(items: list[dict], kids_of: dict[str, list[dict]],
                   sprint: set | None = None) -> list[str]:
    """Render one group section. `items` are the section's ROOTS (epics whose
    own status lands here + parentless/non-epic-parented issues), pre-sorted.

    An epic renders as one piece: ALL its children nest beneath its header,
    whatever each child's own status — the `[status]` badge carries it.
    """
    lines: list[str] = []
    epic_block = False
    for it in items:
        if it["type"] != "epic":
            continue
        if lines:
            lines.append("")
        lines.append(render_epic_header(it, sprint))
        epic_block = True
        kids = ksort(kids_of.get(it["name"], []))
        for i, ch in enumerate(kids):
            conn = "last" if i == len(kids) - 1 else "mid"
            lines.append(render_item(ch, connector=conn, sprint=sprint, show_status=True))

    plain = [it for it in items if it["type"] != "epic"]
    if epic_block and plain:
        lines.append("")
        lines.append(t("no_epic_group"))
    for it in plain:
        lines.append(render_item(it, sprint=sprint))

    return lines


def render_sprint_banner(sprint: dict | None) -> list[str]:
    if not sprint:
        return []
    head = t("sprint_head")
    if sprint["goal"]:
        head += f" — {sprint['goal']}"
    if sprint["ends"]:
        head += t("sprint_until", ends=sprint["ends"])
    lines = [head]
    if sprint["includes"]:
        done = {s for s in sprint["includes"] if closed_in_done(s)}
        marked = [("✔ " + s) if s in done else s for s in sorted(sprint["includes"])]
        progress = f" [{len(done)}/{len(sprint['includes'])} ✔]" if done else ""
        lines.append("   " + " · ".join(marked) + progress)
        if len(done) == len(sprint["includes"]):
            lines.append(t("sprint_complete"))
    return lines


def group_header(g: str, n: int) -> list[str]:
    """Group banner: blank line, rule, ` <emoji label> (n)`, rule, blank line."""
    return ["", RULE, f" {t('group_' + g)} ({n})", RULE, ""]


def render(issues: list[dict], branch: str, status: str, log: list[str],
           sprint: dict | None = None, full: bool = False) -> str:
    lines = [FRAME, f"  {t('title', name=PROJECT_NAME)}", FRAME]

    banner = render_sprint_banner(sprint)
    if banner:
        lines.append("")
        lines.extend(banner)

    lines.append("\n" + t("git_line", branch=branch, status=status))
    if log:
        lines.append(t("last_commits"))
        for entry in log:
            lines.append(f"  {entry}")

    warnings, sprint_slugs = annotate(issues, sprint)

    groups: dict[str, list[dict]] = {g: [] for g in GROUP_ORDER}
    for it in issues:
        groups[it["group"]].append(it)
    for g in groups:
        groups[g].sort(key=lambda x: (PRIORITY_ORDER.get(x["priority"], 9), x["name"]))

    # Render homes: the status groups above are the COUNT truth; for display,
    # a child of a live epic always renders under that epic (in the epic's
    # group), so the epic shows as one piece. Everything else roots in its own
    # group.
    by_name = {it["name"]: it for it in issues}
    kids_of: dict[str, list[dict]] = {}
    roots: dict[str, list[dict]] = {g: [] for g in GROUP_ORDER}
    for it in issues:
        parent = by_name.get(it["parent"]) if it["parent"] else None
        if parent is not None and parent["type"] == "epic":
            kids_of.setdefault(parent["name"], []).append(it)
        else:
            roots[it["group"]].append(it)
    for g in roots:
        roots[g].sort(key=lambda x: (PRIORITY_ORDER.get(x["priority"], 9), x["name"]))

    def section_size(items: list[dict]) -> int:
        return len(items) + sum(
            len(kids_of.get(it["name"], [])) for it in items if it["type"] == "epic"
        )

    committed = " · ".join(
        f"{len(groups[g])} {t('count_' + g)}" for g in ("active", "ready") if groups[g]
    )
    parked = " · ".join(
        f"{len(groups[g])} {t('count_' + g)}" for g in ("backlog", "frozen") if groups[g]
    )
    parts = []
    if committed:
        parts.append(t("counts_committed", s=committed))
    if parked:
        parts.append(t("counts_uncommitted", s=parked))
    if groups["unknown"]:
        parts.append(t("counts_unclassified", n=len(groups["unknown"])))
    lines.append("\n" + t("counts_line", n=len(issues), parts=" | ".join(parts)))

    if warnings:
        lines.append("\n" + t("inconsistencies"))
        for w in warnings:
            lines.append(f"    - {w}")

    if full:
        for g in GROUP_ORDER:
            items = roots[g]
            if not items:
                continue
            lines.extend(group_header(g, section_size(items)))
            lines.extend(render_section(items, kids_of, sprint_slugs))
    else:
        # Compact (SessionStart auto-inject): active+ready full (epic subtrees
        # included); backlog collapses to ALTA-inline + counts; frozen
        # collapses to its epics + counts.
        for g in ("active", "ready"):
            items = roots[g]
            if not items:
                continue
            lines.extend(group_header(g, section_size(items)))
            lines.extend(render_section(items, kids_of, sprint=sprint_slugs))

        items = roots["backlog"]
        if items:
            by_prio: dict[str, list[dict]] = {"ALTA": [], "MEDIA": [], "BAJA": []}
            for it in items:
                by_prio.setdefault(it["priority"], []).append(it)
            lines.extend(group_header("backlog", section_size(items)))
            for it in by_prio.get("ALTA", []):
                lines.append(render_item(it, sprint=sprint_slugs))
            if by_prio.get("MEDIA"):
                lines.append(t("more_media", n=len(by_prio["MEDIA"])))
            if by_prio.get("BAJA"):
                lines.append(t("more_baja", n=len(by_prio["BAJA"])))

        items = roots["frozen"]
        if items:
            lines.extend(group_header("frozen", section_size(items)))
            rest = 0
            for it in items:
                if it["type"] == "epic":
                    kids = len(kids_of.get(it["name"], []))
                    lines.append(
                        f"  ▸ epic {it['name']} [{it['priority']}]"
                        + t("frozen_children", n=kids)
                        + f" · frozen_by: {it['frozen_by']}"
                    )
                else:
                    rest += 1
            if rest > 0:
                lines.append(t("frozen_rest", n=rest))

        items = roots["unknown"]
        if items:
            lines.extend(group_header("unknown", len(items)))
            for it in items:
                lines.append(render_item(it, sprint=sprint_slugs))

    lines.append("")
    lines.append(t("files_of_record"))
    lines.append(t("dig_deeper"))
    return "\n".join(lines)


def main() -> int:
    global LANG, REPO, ISSUES_OPEN, ISSUES_DONE, SPRINT_FILE, PROJECT_NAME
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    repo = find_repo(payload.get("cwd") or "")
    if repo is None:
        return 0
    REPO = repo
    ISSUES_OPEN = repo / "docs/issues/open"
    ISSUES_DONE = repo / "docs/issues/done"
    SPRINT_FILE = repo / "docs/issues/sprint.md"
    cfg = read_config()
    PROJECT_NAME = str(cfg.get("name") or repo.name)
    LANG = resolve_lang(sys.argv[1:], cfg)
    full = "--full" in sys.argv[1:]
    try:
        issues = collect_open_issues()
        sprint = read_sprint()
        branch, status, log = git_snapshot()
        sys.stdout.write(render(issues, branch, status, log, sprint=sprint, full=full))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
