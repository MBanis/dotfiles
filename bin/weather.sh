#!/usr/bin/env bash
#
# weather.sh — DC weather dashboard (linecast + zellij)
#
# Opens a Zellij session with a DC-area weather dashboard built entirely on
# linecast (https://github.com/ashuttl/linecast, v2.2+):
#
#   +----------------------+-----------------+
#   |                      |  temperature    |
#   |                      |   (weather)     |
#   |                      |     ~50%        |
#   |        RADAR         +--------+--------+
#   |     (left, >=50%)    |  sun   |  moon  |
#   |                      +--------+--------+
#   |                      |      tide       |
#   |                      |    (tides)      |
#   +----------------------+-----------------+
#
# Right column: temperature on top at half the height; sun/moon and tide
# share the rest (~25% each). Sun and moon sit side by side so both
# linecast live commands have a terminal.
#
# Layout source: config/zellij/layouts/dc-weather.kdl (linked by install.py).
#
# Requires: zellij and linecast >= 2.2 (`weather`, `sunshine`, `moon`,
# `tides`, `radar` were added across the 2.x line — run `linecast doctor`
# or `pip install -U linecast` if any of these commands are missing).

set -euo pipefail

SESSION="${SESSION:-dc-weather}"
LAYOUT_DIR="${HOME}/.config/zellij/layouts"
LAYOUT_NAME="dc-weather"
LAYOUT_FILE="${LAYOUT_DIR}/${LAYOUT_NAME}.kdl"

# Attach only to a live session. kill-session leaves an EXITED serialized
# corpse that would otherwise resurrect with every pane "waiting to run".
if zellij list-sessions -n 2>/dev/null | grep -E "^${SESSION} " | grep -qv 'EXITED'; then
  echo "Session '$SESSION' already exists — attaching."
  exec zellij attach "$SESSION"
fi

if zellij list-sessions -ns 2>/dev/null | grep -qx "$SESSION"; then
  zellij delete-session --force "$SESSION"
fi

if [[ ! -r "$LAYOUT_FILE" ]]; then
  echo "Missing layout: $LAYOUT_FILE" >&2
  echo "Run: python3 install.py --configs" >&2
  exit 1
fi

exec zellij --session "$SESSION" --new-session-with-layout "$LAYOUT_NAME"
