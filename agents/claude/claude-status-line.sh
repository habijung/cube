#!/bin/sh
# Claude Code Custom Statusline
# Format: short_path [| branch*] | model | ctx% | 5H:X%(HH:MM) | 7D:X%(Day or HH:MM) [| EX:X%($Y.YY)]
#
# Requires: jq, python3, curl, git (all standard on macOS)
# Usage: add to ~/.claude/settings.json:
#   "statusLine": { "type": "command", "command": "bash ~/.claude/claude-status-line.sh" }
# Debug: STATUSLINE_DEBUG=1 dumps stdin JSON to /tmp/claude_statusline_input.log

input=$(cat)
OS=$(uname -s 2>/dev/null)

# Use macOS /bin/date and /usr/bin/stat even if GNU coreutils is in PATH
if [ "$OS" = "Darwin" ]; then
    DATE="/bin/date"
    STAT="/usr/bin/stat"
else
    DATE="date"
    STAT="stat"
fi

# ---------------------------------------------------------------------------
# CWD → Fish-style short path
# ---------------------------------------------------------------------------
cwd=$(printf '%s' "$input" | jq -r '.cwd // ""')

short_path="$cwd"
if [ -n "$cwd" ]; then
    case "$cwd" in
        "$HOME") short_path="~" ;;
        # Windows backslash path (e.g. C:\Users\foo\bar)
        *\\*)    short_path="${cwd##*\\}" ;;
        # Unix path
        *)       short_path="${cwd##*/}" ;;
    esac
fi

# ---------------------------------------------------------------------------
# Git branch + dirty indicator
# ---------------------------------------------------------------------------
branch_segment=""
if [ -n "$cwd" ]; then
    branch=$(git -C "$cwd" branch --show-current 2>/dev/null)
    if [ -n "$branch" ]; then
        dirty=$(git -C "$cwd" status --porcelain 2>/dev/null)
        [ -n "$dirty" ] && branch="${branch}*"
        branch_segment="$branch"
    fi
fi

# ---------------------------------------------------------------------------
# Model name (strip "Claude " prefix for brevity)
# ---------------------------------------------------------------------------
model=$(printf '%s' "$input" | jq -r '.model.display_name // "Unknown"' | sed 's/^Claude //; s/^\([A-Za-z]\)[a-z]* /\1/')

# ---------------------------------------------------------------------------
# Context percentage
#   Trust stdin's .context_window.used_percentage as the source of truth —
#   Claude Code knows the actual context limit (200K vs 1M) and computes it
#   correctly. JSONL-based calculation is only used as a fallback when stdin
#   omits the field (older versions, edge cases).
#   Optional: STATUSLINE_DEBUG=1 dumps stdin JSON to /tmp for diagnosis.
# ---------------------------------------------------------------------------
[ -n "$STATUSLINE_DEBUG" ] && printf '%s\n---\n' "$input" >> /tmp/claude_statusline_input.log

ctx_raw=$(printf '%s' "$input" | jq -r '.context_window.used_percentage // empty')
if [ -n "$ctx_raw" ]; then
    ctx=$(printf '%s' "$ctx_raw" | awk '{printf "%.0f", $1}')
else
    # Fallback: derive from JSONL last assistant usage entry
    ctx=""
    transcript=$(printf '%s' "$input" | jq -r '.transcript_path // empty')
    session_id=$(printf '%s' "$input" | jq -r '.session_id // empty')
    model_id=$(printf '%s' "$input" | jq -r '.model.id // empty')

    if [ -z "$transcript" ] && [ -n "$session_id" ] && [ -n "$cwd" ]; then
        sanitized=$(printf '%s' "$cwd" | sed 's|[/.]|-|g')
        candidate="$HOME/.claude/projects/${sanitized}/${session_id}.jsonl"
        [ -f "$candidate" ] && transcript="$candidate"
    fi

    if [ -n "$transcript" ] && [ -f "$transcript" ]; then
        last_usage_line=$(awk '/"cache_read_input_tokens"/{last=$0} END{print last}' "$transcript")
        if [ -n "$last_usage_line" ]; then
            tokens=$(printf '%s' "$last_usage_line" | jq -r '
                (.message.usage // .usage // null) as $u |
                if $u then
                    (($u.input_tokens // 0)
                      + ($u.cache_creation_input_tokens // 0)
                      + ($u.cache_read_input_tokens // 0))
                else empty end
            ' 2>/dev/null)
            if [ -n "$tokens" ] && [ "$tokens" -gt 0 ] 2>/dev/null; then
                case "$model_id" in
                    *1m*|*-1m-*) limit=1000000 ;;
                    *)           limit=200000  ;;
                esac
                ctx=$(awk -v u="$tokens" -v l="$limit" 'BEGIN{printf "%.0f", u*100/l}')
            fi
        fi
    fi

    [ -z "$ctx" ] && ctx=0
fi

# ---------------------------------------------------------------------------
# 5h / 7d usage via Anthropic OAuth API (cached in /tmp)
# ---------------------------------------------------------------------------
CACHE_FILE="/tmp/claude_usage_cache.json"
CACHE_TTL=90    # seconds (1.5 min)
LOCK_DIR="/tmp/claude_usage_cache.lock"
LOCK_STALE=30   # seconds — treat as stale if lock dir is older than this

usage_json=""

# Check if cache is fresh
# Error responses (rate limit etc.) use the same 10 min TTL
if [ -f "$CACHE_FILE" ]; then
    if [ "$OS" = "Darwin" ]; then
        cache_mtime=$($STAT -f "%m" "$CACHE_FILE" 2>/dev/null || echo 0)
    else
        cache_mtime=$($STAT -c %Y "$CACHE_FILE" 2>/dev/null || echo 0)
    fi
    age=$(( $(date +%s) - cache_mtime ))
    cached=$(cat "$CACHE_FILE")
    is_error=$(printf '%s' "$cached" | jq -r '.error // empty' 2>/dev/null)
    ttl=$CACHE_TTL
    [ -n "$is_error" ] && ttl=600
    if [ "$age" -lt "$ttl" ]; then
        usage_json="$cached"
        # Invalidate cache if 5h or 7d reset time has already passed
        _check_reset_passed() {
            _reset_raw=$(printf '%s' "$usage_json" | jq -r "$1" 2>/dev/null)
            [ -z "$_reset_raw" ] && return 1
            _reset_norm=$(printf '%s' "$_reset_raw" | sed 's/\.[0-9]*//; s/[+-][0-9][0-9]:[0-9][0-9]$/Z/')
            if [ "$OS" = "Darwin" ]; then
                _reset_epoch=$($DATE -j -u -f "%Y-%m-%dT%H:%M:%SZ" "$_reset_norm" "+%s" 2>/dev/null)
            else
                _reset_epoch=$($DATE -d "$_reset_norm" +%s 2>/dev/null)
            fi
            [ -n "$_reset_epoch" ] && [ "$_reset_epoch" -le "$($DATE +%s)" ]
        }
        if _check_reset_passed '.five_hour.resets_at // empty' || \
           _check_reset_passed '.seven_day.resets_at // empty'; then
            usage_json=""  # Force refetch — reset has passed, cache is stale
        fi
    fi
fi

# Fetch from API if cache is stale
if [ -z "$usage_json" ]; then
    # Clean up stale lock (in case of crash)
    if [ -d "$LOCK_DIR" ]; then
        if [ "$OS" = "Darwin" ]; then
            lock_mtime=$($STAT -f "%m" "$LOCK_DIR" 2>/dev/null || echo 0)
        else
            lock_mtime=$($STAT -c %Y "$LOCK_DIR" 2>/dev/null || echo 0)
        fi
        lock_age=$(( $(date +%s) - lock_mtime ))
        [ "$lock_age" -gt "$LOCK_STALE" ] && rmdir "$LOCK_DIR" 2>/dev/null
    fi

    # Try to acquire lock (mkdir is atomic on POSIX — only one process succeeds)
    if mkdir "$LOCK_DIR" 2>/dev/null; then
        # Lock acquired — fetch from API
        # Try to get access token from macOS Keychain (macOS only)
        if [ "$OS" = "Darwin" ]; then
            keychain_raw=$(security find-generic-password -s "Claude Code-credentials" -w 2>/dev/null)
            if [ -n "$keychain_raw" ]; then
                token=$(printf '%s' "$keychain_raw" | python3 -c \
                    "import sys, json; d=json.load(sys.stdin); print(d.get('claudeAiOauth',{}).get('accessToken',''))" \
                    2>/dev/null)
            fi
        fi

        # Fallback: credentials file
        if [ -z "$token" ]; then
            creds_file="$HOME/.claude/.credentials.json"
            if [ -f "$creds_file" ]; then
                token=$(jq -r '.claudeAiOauth.accessToken // ""' "$creds_file" 2>/dev/null)
            fi
        fi

        if [ -n "$token" ]; then
            # -s only (no -f): capture body even on HTTP errors (429, etc.)
            fetched=$(curl -s --max-time 5 \
                -H "Authorization: Bearer $token" \
                -H "anthropic-beta: oauth-2025-04-20" \
                -H "User-Agent: claude-code/2.1" \
                "https://api.anthropic.com/api/oauth/usage" 2>/dev/null)
            if [ -n "$fetched" ]; then
                usage_json="$fetched"
                printf '%s' "$usage_json" > "$CACHE_FILE"
            fi
        fi

        rmdir "$LOCK_DIR" 2>/dev/null  # Release lock
    else
        # Lock held by another process — use stale cache or last_good
        if [ -f "$CACHE_FILE" ]; then
            usage_json=$(cat "$CACHE_FILE")
        elif [ -f "$CACHE_FILE.last_good" ]; then
            usage_json=$(cat "$CACHE_FILE.last_good")
        fi
    fi
fi

# Load last-good cache on rate limit / API error
if [ -n "$usage_json" ]; then
    err=$(printf '%s' "$usage_json" | jq -r '.error.type // empty' 2>/dev/null)
    if [ -n "$err" ]; then
        LAST_GOOD="$CACHE_FILE.last_good"
        [ -f "$LAST_GOOD" ] && usage_json=$(cat "$LAST_GOOD") || usage_json=""
    else
        # Save last known good response
        printf '%s' "$usage_json" > "$CACHE_FILE.last_good"
    fi
fi

# ---------------------------------------------------------------------------
# Parse usage data
# ---------------------------------------------------------------------------
format_reset_time() {
    resets_at="$1"
    if [ -z "$resets_at" ] || [ "$resets_at" = "null" ]; then
        printf '%s' '--'; return
    fi
    # Normalize to "...T00:00:00Z": strip sub-seconds, convert +HH:MM offset → Z
    resets_at=$(printf '%s' "$resets_at" | sed 's/\.[0-9]*//; s/[+-][0-9][0-9]:[0-9][0-9]$/Z/')
    if [ "$OS" = "Darwin" ]; then
        reset_epoch=$($DATE -j -u -f "%Y-%m-%dT%H:%M:%SZ" "$resets_at" "+%s" 2>/dev/null)
    else
        reset_epoch=$($DATE -d "$resets_at" +%s 2>/dev/null)
    fi
    [ -z "$reset_epoch" ] && { printf '%s' '--'; return; }

    now=$($DATE +%s)
    diff=$(( reset_epoch - now ))
    [ "$diff" -le 0 ] && { printf '%s' 'now'; return; }

    if [ "$OS" = "Darwin" ]; then
        reset_time=$($DATE -r "$reset_epoch" "+%H:%M")
        reset_dow=$($DATE  -r "$reset_epoch" "+%a")
        reset_day=$($DATE -r "$reset_epoch" "+%d" | sed 's/^0//')
        reset_mon=$($DATE  -r "$reset_epoch" "+%b")
    else
        reset_time=$($DATE -d "@$reset_epoch" "+%H:%M")
        reset_dow=$($DATE  -d "@$reset_epoch" "+%a")
        reset_day=$($DATE -d "@$reset_epoch" "+%d" | sed 's/^0//')
        reset_mon=$($DATE  -d "@$reset_epoch" "+%b")
    fi

    if [ "$diff" -lt 86400 ]; then
        # Within 24h (same day or next-day midnight) → show local HH:MM
        printf '%s' "$reset_time"
    elif [ "$diff" -lt 604800 ]; then
        # Within 7 days → show day-of-week abbreviation (Mon, Tue, …)
        printf '%s' "$reset_dow"
    else
        # Beyond 7 days → show "Apr 5"
        printf '%s' "${reset_mon} ${reset_day}"
    fi
}

five_h_pct="--"
five_h_at="--"
seven_d_pct="--"
seven_d_at="--"
extra_segment=""

if [ -n "$usage_json" ]; then
    five_h_util=$(printf '%s' "$usage_json" | jq -r '.five_hour.utilization // empty' 2>/dev/null)
    five_h_reset=$(printf '%s' "$usage_json" | jq -r '.five_hour.resets_at // empty' 2>/dev/null)
    seven_d_util=$(printf '%s' "$usage_json" | jq -r '.seven_day.utilization // empty' 2>/dev/null)
    seven_d_reset=$(printf '%s' "$usage_json" | jq -r '.seven_day.resets_at // empty' 2>/dev/null)

    # Return 0 if resets_at is in the past (reset occurred but API not yet updated)
    _pct_or_zero() {
        _util="$1"; _reset_raw="$2"
        _pct=$(printf '%s' "$_util" | awk '{printf "%d", $1}')
        if [ -n "$_reset_raw" ] && [ "$_reset_raw" != "null" ]; then
            _norm=$(printf '%s' "$_reset_raw" | sed 's/\.[0-9]*//; s/[+-][0-9][0-9]:[0-9][0-9]$/Z/')
            if [ "$OS" = "Darwin" ]; then
                _epoch=$($DATE -j -u -f "%Y-%m-%dT%H:%M:%SZ" "$_norm" "+%s" 2>/dev/null)
            else
                _epoch=$($DATE -d "$_norm" +%s 2>/dev/null)
            fi
            if [ -n "$_epoch" ] && [ "$_epoch" -le "$($DATE +%s)" ]; then
                _pct=0
            fi
        fi
        printf '%s' "$_pct"
    }

    if [ -n "$five_h_util" ]; then
        five_h_pct=$(_pct_or_zero "$five_h_util" "$five_h_reset")
        five_h_at=$(format_reset_time "$five_h_reset")
    fi
    if [ -n "$seven_d_util" ]; then
        seven_d_pct=$(_pct_or_zero "$seven_d_util" "$seven_d_reset")
        seven_d_at=$(format_reset_time "$seven_d_reset")
    fi

    # Extra usage — shown only when is_enabled: true
    extra_enabled=$(printf '%s' "$usage_json" | jq -r '.extra_usage.is_enabled // false' 2>/dev/null)
    if [ "$extra_enabled" = "true" ]; then
        extra_util=$(printf '%s' "$usage_json" | jq -r '.extra_usage.utilization // 0' 2>/dev/null)
        extra_credits=$(printf '%s' "$usage_json" | jq -r '.extra_usage.used_credits // 0' 2>/dev/null)
        extra_pct=$(printf '%s' "$extra_util" | awk '{printf "%d", $1}')
        extra_dollars=$(printf '%s' "$extra_credits" | awk '{printf "$%.2f", $1 / 100}')
        extra_segment="EX:${extra_pct}%(${extra_dollars})"
    fi
fi

# ---------------------------------------------------------------------------
# Assemble output
# ---------------------------------------------------------------------------
out="$short_path"
[ -n "$branch_segment" ] && out="${out} | ${branch_segment}"
out="${out} | ${model} | ${ctx}% | 5H:${five_h_pct}%(${five_h_at}) | 7D:${seven_d_pct}%(${seven_d_at})"
[ -n "$extra_segment" ] && out="${out} | ${extra_segment}"

printf '%s\n' "$out"
