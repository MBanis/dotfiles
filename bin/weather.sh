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
# Requires: zellij and linecast >= 2.2 (`weather`, `sunshine`, `moon`,
# `tides`, `radar` were added across the 2.x line — run `linecast doctor`
# or `pip install -U linecast` if any of these commands are missing).

set -euo pipefail

SESSION="${SESSION:-dc-weather}"
LOCATION="38.9072,-77.0369"   # Washington, DC
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

mkdir -p "$LAYOUT_DIR"
cat >"$LAYOUT_FILE" <<EOF
layout {
    // Match Zellij's default chrome so the user's normal tab/status bars show.
    default_tab_template {
        pane size=1 borderless=true {
            plugin location="tab-bar"
        }
        children
        pane size=1 borderless=true {
            plugin location="status-bar"
        }
    }
    // new_tab_template is a full tab blueprint (not wrapped by default_tab_template),
    // so it must include the same chrome as a normal Zellij tab.
    new_tab_template {
        pane size=1 borderless=true {
            plugin location="tab-bar"
        }
        pane
        pane size=1 borderless=true {
            plugin location="status-bar"
        }
    }
    tab name="weather" split_direction="vertical" {
        pane size="55%" name="radar" focus=true command="linecast" {
            args "radar" "--location" "$LOCATION"
        }
        pane size="45%" split_direction="horizontal" {
            pane size="50%" name="temperature" command="linecast" {
                args "weather" "--location" "$LOCATION"
            }
            pane size="25%" split_direction="vertical" {
                pane name="sunshine" command="linecast" {
                    args "sunshine" "--location" "$LOCATION"
                }
                pane name="moon" command="linecast" {
                    args "moon" "--location" "$LOCATION"
                }
            }
            pane size="25%" name="tide" command="linecast" {
                args "tides" "--location" "$LOCATION"
            }
        }
    }
}
EOF

exec zellij --session "$SESSION" --new-session-with-layout "$LAYOUT_NAME"
