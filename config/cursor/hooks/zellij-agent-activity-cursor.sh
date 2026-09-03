#!/usr/bin/env bash
set -euo pipefail

read_payload() {
  cat
}

payload="$(read_payload)"

if [[ -z "${ZELLIJ_SESSION_NAME:-}" || -z "${ZELLIJ_PANE_ID:-}" ]]; then
  exit 0
fi

if ! command -v jq >/dev/null 2>&1 || ! command -v zellij >/dev/null 2>&1; then
  exit 0
fi

hook_event="$(jq -r '.hook_event_name // empty' <<<"$payload")"
tool_name="$(jq -r '.tool_name // empty' <<<"$payload")"
ts_ms="$(python3 - <<'PY'
import time
print(int(time.time() * 1000))
PY
)"

wire_event=""
wire_tool=""
wire_notification=""

case "$hook_event" in
  sessionStart)
    wire_event="SessionStart"
    ;;
  sessionEnd)
    wire_event="SessionEnd"
    ;;
  beforeSubmitPrompt)
    wire_event="UserPromptSubmit"
    ;;
  stop)
    wire_event="Stop"
    ;;
  preToolUse)
    wire_event="PreToolUse"
    case "$tool_name" in
      Shell) wire_tool="Bash" ;;
      Write|Edit|MultiEdit|ApplyPatch) wire_tool="Edit" ;;
      Read|Glob|Grep) wire_tool="$tool_name" ;;
      Task|Agent) wire_tool="Agent" ;;
      WebSearch|WebFetch) wire_tool="$tool_name" ;;
      MCP:*) wire_tool="MCP" ;;
      *) wire_tool="$tool_name" ;;
    esac
    ;;
  postToolUse|postToolUseFailure|afterShellExecution|afterFileEdit)
    wire_event="PostToolUse"
    ;;
  beforeShellExecution)
    wire_event="PreToolUse"
    wire_tool="Bash"
    ;;
  beforeReadFile)
    wire_event="PreToolUse"
    wire_tool="Read"
    ;;
esac

if [[ -z "$wire_event" ]]; then
  exit 0
fi

args="pane_id=${ZELLIJ_PANE_ID},hook_event=${wire_event},tool_name=${wire_tool},ts_ms=${ts_ms}"
if [[ -n "$wire_notification" ]]; then
  args="${args},notification=${wire_notification}"
fi

if [[ -n "${ZELLIJ_AGENT_ACTIVITY_LOG:-}" ]]; then
  mkdir -p "$(dirname "$ZELLIJ_AGENT_ACTIVITY_LOG")"
  jq -cn \
    --arg hook_event "$hook_event" \
    --arg tool_name "$tool_name" \
    --arg wire_event "$wire_event" \
    --arg wire_tool "$wire_tool" \
    --arg pane_id "${ZELLIJ_PANE_ID}" \
    --arg args "$args" \
    --argjson ts_ms "$ts_ms" \
    '{ts_ms:$ts_ms,pane_id:$pane_id,hook_event:$hook_event,tool_name:$tool_name,wire_event:$wire_event,wire_tool:$wire_tool,args:$args}' \
    >>"$ZELLIJ_AGENT_ACTIVITY_LOG" || true
fi

if [[ -n "${ZELLIJ_AGENT_ACTIVITY_DRY_RUN:-}" ]]; then
  printf '%s\n' "$args"
  exit 0
fi

zellij pipe --name agent_activity.v1 --args "$args" </dev/null >/dev/null 2>&1 &
pipe_pid=$!
(
  sleep 5
  kill "$pipe_pid" >/dev/null 2>&1 || true
) &
watchdog_pid=$!
wait "$pipe_pid" >/dev/null 2>&1 || true
kill "$watchdog_pid" >/dev/null 2>&1 || true
