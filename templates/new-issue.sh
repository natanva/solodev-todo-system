#!/usr/bin/env bash
# new-issue.sh — scaffold a new issue file in docs/issues/open/
#
# Usage:
#   scripts/new-issue.sh <type> "<title>" [priority]
#
# type     : bug | feature | chore | plan | epic
# title    : free-text title (will be slugified for the filename)
# priority : ALTA | MEDIA | BAJA  (high | medium | low — frontmatter tokens; default MEDIA)
#
# Example:
#   scripts/new-issue.sh bug "Celery worker zombie after outage"
#   scripts/new-issue.sh plan "GSC historical backfill" ALTA

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPEN_DIR="${REPO_ROOT}/docs/issues/open"

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <type: bug|feature|chore|plan|epic> \"<title>\" [priority]" >&2
    exit 2
fi

TYPE="$1"
TITLE="$2"
PRIORITY="${3:-MEDIA}"

case "$TYPE" in
    bug|feature|chore|plan|epic) ;;
    *) echo "type must be one of: bug, feature, chore, plan, epic (got: $TYPE)" >&2; exit 2 ;;
esac

case "$PRIORITY" in
    ALTA|MEDIA|BAJA) ;;
    *) echo "priority must be one of: ALTA, MEDIA, BAJA (got: $PRIORITY)" >&2; exit 2 ;;
esac

SLUG="$(echo "$TITLE" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[áàä]/a/g; s/[éèë]/e/g; s/[íìï]/i/g; s/[óòö]/o/g; s/[úùü]/u/g; s/ñ/n/g' \
    | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g' \
    | cut -c1-60)"

FILENAME="${TYPE}-${SLUG}.md"
PATH_FULL="${OPEN_DIR}/${FILENAME}"

if [[ -e "$PATH_FULL" ]]; then
    echo "Already exists: $PATH_FULL" >&2
    exit 1
fi

TODAY="$(date +%Y-%m-%d)"

cat > "$PATH_FULL" <<EOF
---
type: ${TYPE}
status: backlog
priority: ${PRIORITY}
created: ${TODAY}
---

# ${TITLE}

## Summary

<one or two sentences about WHAT is happening or WHAT should be built>

## Motivation

<why it matters — incident, opportunity, debt>

## Implementation plan

<concrete steps, or "—" for a simple bug>

## Acceptance criteria

- [ ] criterion 1
- [ ] criterion 2
EOF

echo "Created: docs/issues/open/${FILENAME}"
