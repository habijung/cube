#!/usr/bin/env bash

# Cube 🧊 - AI Agent Config Installer

# 현재 디렉토리가 cube 저장소 루트인지 확인
if [[ ! -f "cube.sh" ]]; then
  echo "❌ Error: Please run this script from the 'cube' root directory."
  exit 1
fi

CUBE_PATH="$(pwd)"
SKILLS_SRC="$CUBE_PATH/skills"

# 쉘 설정 파일 탐색
DETECTED_SHELL=$(basename "$SHELL")
if [[ "$DETECTED_SHELL" == "zsh" ]]; then
  RC_FILE="$HOME/.zshrc"
elif [[ "$DETECTED_SHELL" == "bash" ]]; then
  if [[ "$OSTYPE" == "darwin"* ]]; then
    RC_FILE="$HOME/.bash_profile"
  else
    RC_FILE="$HOME/.bashrc"
  fi
else
  RC_FILE="$HOME/.bashrc"
fi

# 진단 기능 (Check Mode)
check_installation() {
  echo "🔍 Diagnosing Cube Environment..."
  local errors=0

  # 1. Alias Check
  if grep -q "source $CUBE_PATH/cube.sh" "$RC_FILE" 2>/dev/null; then
    echo "✅ [Alias] cube.sh is correctly sourced in $RC_FILE"
  else
    echo "❌ [Alias] cube.sh is NOT sourced in $RC_FILE"
    errors=$((errors + 1))
  fi

  # 2. Agent Skills Check
  local agents_to_check=("claude" "gemini" "opencode")
  local missing_agents=()
  for agent in "${agents_to_check[@]}"; do
    case "$agent" in
      claude) DEST_BASE="$HOME/.claude" ;;
      gemini|opencode) DEST_BASE="$HOME/.agents" ;;
    esac

    local skills_dest="$DEST_BASE/skills"
    if [[ -d "$skills_dest" ]]; then
      echo "✅ [$agent] Skills directory exists: $skills_dest"
      local agent_error=false
      # 개별 스킬 심볼릭 링크 확인
      for skill_dir in "$SKILLS_SRC"/cube-*/; do
        skill_dir=${skill_dir%/}
        skill_name=$(basename "$skill_dir")
        dest="$skills_dest/$skill_name"
        if [[ -L "$dest" ]] && [[ "$(readlink "$dest")" == "$skill_dir" ]]; then
          echo "   - ✅ $skill_name: Symlinked correctly"
        else
          echo "   - ❌ $skill_name: Broken or missing link"
          errors=$((errors + 1))
          agent_error=true
        fi
      done
      [[ "$agent_error" == true ]] && missing_agents+=("$agent")
    else
      echo "⚠️  [$agent] Skills directory not found. Skipping check for this agent."
      missing_agents+=("$agent")
    fi

    # Gemini specific policy check
    if [[ "$agent" == "gemini" ]]; then
      local policies_src="$CUBE_PATH/agents/gemini/policies"
      local policies_dest="$HOME/.gemini/policies"
      if [[ -d "$policies_src" ]]; then
        for policy_file in "$policies_src"/*.toml; do
          [ -f "$policy_file" ] || continue
          local policy_name=$(basename "$policy_file")
          local dest="$policies_dest/$policy_name"
          if [[ -L "$dest" ]] && [[ "$(readlink "$dest")" == "$policy_file" ]]; then
            echo "   - ✅ Policy $policy_name: Symlinked correctly"
          else
            echo "   - ❌ Policy $policy_name: Broken or missing link"
            errors=$((errors + 1))
          fi
        done
      fi
    fi
    # Gemini specific permanent approval check
    if [[ "$agent" == "gemini" ]]; then
      local gemini_settings="$HOME/.gemini/settings.json"
      if [[ -f "$gemini_settings" ]]; then
        if ! node -e "const fs=require('fs'); try { const c=JSON.parse(fs.readFileSync('$gemini_settings','utf8')); process.exit(c?.security?.enablePermanentToolApproval ? 0 : 1); } catch(e) { process.exit(1); }" 2>/dev/null; then
          echo "⚠️  [Gemini] Permanent tool approval is NOT enabled in settings.json"
          # This is a recommendation, not a hard error that stops setup
        else
          echo "   - ✅ Permanent tool approval: Enabled"
        fi
      fi
    fi
  done

  # 3. Claude specific status line check
  local statusline_src="$CUBE_PATH/agents/claude/cube-status-line.sh"
  local statusline_dest="$HOME/.claude/cube-status-line.sh"
  if [[ -L "$statusline_dest" ]] && [[ "$(readlink "$statusline_dest")" == "$statusline_src" ]]; then
    echo "✅ [Claude] status-line script symlinked correctly"
  elif [[ -d "$HOME/.claude" ]]; then
    echo "❌ [Claude] status-line script link missing"
    errors=$((errors + 1))
    [[ ! " ${missing_agents[@]} " =~ " claude " ]] && missing_agents+=("claude")
  fi

  # 3b. Claude settings.json statusLine check
  local claude_settings="$HOME/.claude/settings.json"
  if [[ -f "$claude_settings" ]]; then
    if python3 -c "
import sys, json
try:
    c = json.load(open('$claude_settings'))
    sl = c.get('statusLine', {})
    sys.exit(0 if sl.get('type') == 'command' and 'cube-status-line.sh' in sl.get('command', '') else 1)
except Exception: sys.exit(1)
" 2>/dev/null; then
      echo "   - ✅ settings.json statusLine: Configured"
    elif python3 -c "
import sys, json
try:
    c = json.load(open('$claude_settings'))
    sl = c.get('statusLine', {})
    sys.exit(0 if sl.get('type') == 'command' and sl.get('command', '') else 1)
except Exception: sys.exit(1)
" 2>/dev/null; then
      echo "   - ℹ️  settings.json statusLine: 커스텀 설정 감지 — cube 설정 건너뜀"
    else
      echo "   - ⚠️  settings.json statusLine: Not configured"
    fi
  else
    echo "   - ⚠️  [Claude] settings.json not found. Run 'claude' CLI first."
  fi

  # 4. OpenCode specific plugins check
  local plugins_src="$CUBE_PATH/agents/opencode/plugins"
  local plugins_dest="$HOME/.config/opencode/plugins"
  if [[ -d "$plugins_dest" ]]; then
    local opencode_plugin_error=false
    for plugin_file in "$plugins_src"/*.js; do
      [ -f "$plugin_file" ] || continue
      local plugin_name
      plugin_name=$(basename "$plugin_file")
      local plugin_dest="$plugins_dest/$plugin_name"
      if [[ -L "$plugin_dest" ]] && [[ "$(readlink "$plugin_dest")" == "$plugin_file" ]]; then
        echo "✅ [OpenCode] $plugin_name plugin symlinked correctly"
      else
        echo "❌ [OpenCode] $plugin_name plugin link missing"
        errors=$((errors + 1))
        opencode_plugin_error=true
      fi
    done
    [[ "$opencode_plugin_error" == true ]] && [[ ! " ${missing_agents[@]} " =~ " opencode " ]] && missing_agents+=("opencode")
  elif [[ -d "$HOME/.config/opencode" ]]; then
    echo "⚠️  [OpenCode] Plugins directory not found. Skipping check."
    [[ ! " ${missing_agents[@]} " =~ " opencode " ]] && missing_agents+=("opencode")
  fi

  echo ""
  if [[ $errors -eq 0 && ${#missing_agents[@]} -eq 0 ]]; then
    echo "✨ All systems nominal! Cube is correctly configured."
  else
    [[ $errors -gt 0 ]] && echo "⚠️  Found $errors issue(s)."
    if [[ ${#missing_agents[@]} -gt 0 ]]; then
      echo "💡 Recommendation: run './scripts/install.sh ${missing_agents[*]}' to complete the setup."
    fi
  fi
  exit $errors
}

# 인자 처리
AGENTS=()
CHECK_MODE=false

for arg in "$@"; do
  if [[ "$arg" == "--check" ]]; then
    CHECK_MODE=true
  else
    AGENTS+=("$arg")
  fi
done

if [[ "$CHECK_MODE" == true ]]; then
  check_installation
fi

echo "📦 Cube detected at: $CUBE_PATH"

if [[ ${#AGENTS[@]} -eq 0 ]]; then
  echo "ℹ️  No agents specified. Defaulting to: claude, gemini, opencode"
  AGENTS=("claude" "gemini" "opencode")
fi

# 1. Alias 등록 (cube.sh)
if ! grep -q "source $CUBE_PATH/cube.sh" "$RC_FILE" 2>/dev/null; then
  echo "✨ Adding cube.sh to $RC_FILE..."
  echo "" >> "$RC_FILE"
  echo "# Cube AI Agent Alias" >> "$RC_FILE"
  echo "source $CUBE_PATH/cube.sh" >> "$RC_FILE"
  echo "✅ Successfully added the following to $RC_FILE:"
  echo "   source $CUBE_PATH/cube.sh"
  echo "📝 Please run 'source $RC_FILE' or restart your terminal to apply changes."
else
  echo "✅ cube.sh is already sourced in $RC_FILE."
fi

# 2. Claude Code status-line symlink
if [[ " ${AGENTS[@]} " =~ " claude " ]]; then
  echo "🔧 Setting up Claude Code specific configs..."
  STATUSLINE_SRC="$CUBE_PATH/agents/claude/cube-status-line.sh"
  STATUSLINE_DEST="$HOME/.claude/cube-status-line.sh"

  if [[ -L "$STATUSLINE_DEST" ]] && [[ "$(readlink "$STATUSLINE_DEST")" == "$STATUSLINE_SRC" ]]; then
    echo "✅ cube-status-line.sh is already symlinked."
    chmod +x "$STATUSLINE_SRC"
  elif [[ -f "$STATUSLINE_DEST" ]] && [[ ! -L "$STATUSLINE_DEST" ]]; then
    echo "⚠️  $STATUSLINE_DEST is a regular file. Please manually replace it with a symlink:"
    echo "    rm $STATUSLINE_DEST"
    echo "    ln -sf $STATUSLINE_SRC $STATUSLINE_DEST"
  else
    echo "✨ Creating symlink for cube-status-line.sh..."
    ln -sf "$STATUSLINE_SRC" "$STATUSLINE_DEST"
    chmod +x "$STATUSLINE_SRC"
    echo "✅ Symlinked: $STATUSLINE_DEST → $STATUSLINE_SRC"
  fi

  # Claude settings.json statusLine 자동 설정
  CLAUDE_SETTINGS="$HOME/.claude/settings.json"
  STATUSLINE_CMD="$HOME/.claude/cube-status-line.sh"

  if [[ -f "$CLAUDE_SETTINGS" ]]; then
    if python3 -c "
import sys, json
try:
    c = json.load(open('$CLAUDE_SETTINGS'))
    sl = c.get('statusLine', {})
    sys.exit(0 if sl.get('type') == 'command' and 'cube-status-line.sh' in sl.get('command', '') else 1)
except Exception: sys.exit(1)
" 2>/dev/null; then
      echo "✅ [Claude] statusLine is already configured in settings.json."
    elif python3 -c "
import sys, json
try:
    c = json.load(open('$CLAUDE_SETTINGS'))
    sl = c.get('statusLine', {})
    sys.exit(0 if sl.get('type') == 'command' and sl.get('command', '') else 1)
except Exception: sys.exit(1)
" 2>/dev/null; then
      existing_cmd=$(python3 -c "import json; c=json.load(open('$CLAUDE_SETTINGS')); print(c.get('statusLine',{}).get('command',''))" 2>/dev/null)
      echo "ℹ️  [Claude] 커스텀 statusLine 감지: $existing_cmd"
      if [[ ! -t 0 ]]; then
        echo "ℹ️  Non-interactive mode: 커스텀 설정을 유지합니다."
      else
        echo "   cube-status-line 표시 형식:"
        echo "   path | branch* | model | ctx% | 5H:X%(HH:MM) | 7D:X%(Day or HH:MM)"
        read -p "   cube-status-line.sh로 교체하시겠습니까? (y/N): " replace_statusline
        if [[ "$replace_statusline" =~ ^[Yy]$ ]]; then
          python3 -c "
import json
p = '$CLAUDE_SETTINGS'
try:
    c = json.load(open(p))
except:
    c = {}
c['statusLine'] = {'type': 'command', 'command': '$STATUSLINE_CMD'}
json.dump(c, open(p, 'w'), indent=2)
print('✅ [Claude] statusLine replaced with cube-status-line.sh.')
"
        else
          echo "ℹ️  커스텀 설정을 유지합니다."
        fi
      fi
    else
      echo "⚠️  [Claude] statusLine is not configured in settings.json."
      echo "   cube-status-line 표시 형식:"
      echo "   path | branch* | model | ctx% | 5H:X%(HH:MM) | 7D:X%(Day or HH:MM)"
      if [[ ! -t 0 ]]; then
        echo "ℹ️  Non-interactive mode: applying statusLine automatically."
        enable_statusline="y"
      else
        read -p "   cube-status-line.sh를 추가하시겠습니까? (y/n): " enable_statusline
      fi
      if [[ "$enable_statusline" =~ ^[Yy]$ ]]; then
        python3 -c "
import json
p = '$CLAUDE_SETTINGS'
try:
    c = json.load(open(p))
except:
    c = {}
c['statusLine'] = {'type': 'command', 'command': '$STATUSLINE_CMD'}
json.dump(c, open(p, 'w'), indent=2)
print('✅ [Claude] statusLine added to settings.json.')
"
      else
        echo "ℹ️  Skipped. Add manually:"
        echo '   "statusLine": { "type": "command", "command": "~/.claude/cube-status-line.sh" }'
      fi
    fi
  else
    echo "⚠️  [Claude] settings.json not found. Run 'claude' CLI first to generate it."
  fi
fi

# 2b. Gemini policies symlink
if [[ " ${AGENTS[@]} " =~ " gemini " ]]; then
  echo "🔧 Setting up Gemini specific policies..."
  POLICIES_SRC="$CUBE_PATH/agents/gemini/policies"
  POLICIES_DEST="$HOME/.gemini/policies"

  if [[ -d "$POLICIES_SRC" ]]; then
    mkdir -p "$POLICIES_DEST"
    for policy_file in "$POLICIES_SRC"/*.toml; do
      [ -f "$policy_file" ] || continue
      policy_name=$(basename "$policy_file")
      dest="$POLICIES_DEST/$policy_name"

      if [[ -L "$dest" ]] && [[ "$(readlink "$dest")" == "$policy_file" ]]; then
        echo "✅ [Gemini] $policy_name is already symlinked."
      else
        ln -sf "$policy_file" "$dest"
        echo "✅ [Gemini] Symlinked: $dest → $policy_file"
      fi
    done
  fi

  # Check and ask for permanent tool approval
  GEMINI_SETTINGS="$HOME/.gemini/settings.json"
  if [[ -f "$GEMINI_SETTINGS" ]]; then
    if node -e "const fs=require('fs'); try { const c=JSON.parse(fs.readFileSync('$GEMINI_SETTINGS','utf8')); process.exit(c?.security?.enablePermanentToolApproval ? 0 : 1); } catch(e) { process.exit(1); }" 2>/dev/null; then
      echo "✅ [Gemini] Permanent tool approval is already enabled."
    else
      echo "⚠️  [Gemini] Permanent tool approval (for auto-allowing skills) is not enabled."
      read -p "   Do you want to enable it now? (y/n): " enable_approval
      if [[ "$enable_approval" =~ ^[Yy]$ ]]; then
        node -e "const fs=require('fs'); const p='$GEMINI_SETTINGS'; try { const c=JSON.parse(fs.readFileSync(p,'utf8')); c.security = c.security || {}; c.security.enablePermanentToolApproval = true; fs.writeFileSync(p, JSON.stringify(c, null, 2), 'utf8'); console.log('✅ [Gemini] Enabled permanent tool approval.'); } catch(e) { console.error('❌ Failed to update settings.json', e); }"
      else
        echo "ℹ️  Skipped enabling permanent tool approval."
      fi
    fi
  else
    echo "⚠️  [Gemini] settings.json not found. Run gemini CLI first to generate default settings."
  fi
fi

# 2c. OpenCode plugins symlink
if [[ " ${AGENTS[@]} " =~ " opencode " ]]; then
  echo "🔧 Setting up OpenCode specific configs..."
  PLUGINS_SRC="$CUBE_PATH/agents/opencode/plugins"
  PLUGINS_DEST="$HOME/.config/opencode/plugins"

  mkdir -p "$PLUGINS_DEST"

  for plugin_file in "$PLUGINS_SRC"/*.js; do
    [ -f "$plugin_file" ] || continue
    plugin_name=$(basename "$plugin_file")
    dest="$PLUGINS_DEST/$plugin_name"

    if [[ -L "$dest" ]] && [[ "$(readlink "$dest")" == "$plugin_file" ]]; then
      echo "✅ [OpenCode] $plugin_name is already symlinked."
    elif [[ -f "$dest" ]] && [[ ! -L "$dest" ]]; then
      echo "⚠️  $dest is a regular file. Please manually replace it with a symlink:"
      echo "    rm $dest"
      echo "    ln -sf $plugin_file $dest"
    else
      echo "✨ Creating symlink for $plugin_name..."
      ln -sf "$plugin_file" "$dest"
      echo "✅ [OpenCode] Symlinked: $dest → $plugin_file"
    fi
  done
fi

# 3. Agent skills symlinks
echo "🔧 Setting up Agent Skills..."

# Cleanup old, conflicting paths if they exist
echo "🧹 Cleaning up old skill paths..."
for old_path in "$HOME/.gemini/skills" "$HOME/.config/opencode/skills"; do
  if [[ -d "$old_path" ]]; then
    for skill_dir in "$SKILLS_SRC"/cube-*/; do
      skill_dir=${skill_dir%/}
      skill_name=$(basename "$skill_dir")
      old_link="$old_path/$skill_name"
      if [[ -L "$old_link" ]]; then
        rm "$old_link"
        echo "   - Removed old link: $old_link"
      fi
    done
    # Remove directory ONLY if empty
    rmdir "$old_path" 2>/dev/null
  fi
done

for agent in "${AGENTS[@]}"; do
  case "$agent" in
    claude) DEST_BASE="$HOME/.claude" ;;
    gemini|opencode) DEST_BASE="$HOME/.agents" ;;
    *) echo "⚠️  Unknown agent: $agent. Skipping..."; continue ;;
  esac

  SKILLS_DEST="$DEST_BASE/skills"
  mkdir -p "$SKILLS_DEST"

  for skill_dir in "$SKILLS_SRC"/cube-*/; do
    skill_dir=${skill_dir%/}
    skill_name=$(basename "$skill_dir")
    dest="$SKILLS_DEST/$skill_name"

    if [[ -L "$dest" ]] && [[ "$(readlink "$dest")" == "$skill_dir" ]]; then
      echo "✅ [$agent] $skill_name is already symlinked."
    else
      ln -sf "$skill_dir" "$dest"
      echo "✅ [$agent] Symlinked: $dest → $skill_dir"
    fi
  done
done

echo "🏁 Setup complete!"
