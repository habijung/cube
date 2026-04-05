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
  local agents=("claude" "gemini" "opencode")
  for agent in "${agents[@]}"; do
    case "$agent" in
      claude) DEST_BASE="$HOME/.claude" ;;
      gemini) DEST_BASE="$HOME/.gemini" ;;
      opencode) DEST_BASE="$HOME/.config/opencode" ;;
    esac

    local skills_dest="$DEST_BASE/skills"
    if [[ -d "$skills_dest" ]]; then
      echo "✅ [$agent] Skills directory exists: $skills_dest"
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
        fi
      done
    else
      echo "⚠️  [$agent] Skills directory not found. Skipping check for this agent."
    fi
  done

  # 3. Claude specific status line check
  local statusline_src="$CUBE_PATH/scripts/claude-status-line.sh"
  local statusline_dest="$HOME/.claude/claude-status-line.sh"
  if [[ -L "$statusline_dest" ]] && [[ "$(readlink "$statusline_dest")" == "$statusline_src" ]]; then
    echo "✅ [Claude] status-line script symlinked correctly"
  elif [[ -d "$HOME/.claude" ]]; then
    echo "❌ [Claude] status-line script link missing"
    errors=$((errors + 1))
  fi

  echo ""
  if [[ $errors -eq 0 ]]; then
    echo "✨ All systems nominal! Cube is correctly configured."
  else
    echo "⚠️  Found $errors issue(s). Run './scripts/install.sh' to fix them."
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
  STATUSLINE_SRC="$CUBE_PATH/scripts/claude-status-line.sh"
  STATUSLINE_DEST="$HOME/.claude/claude-status-line.sh"

  if [[ -L "$STATUSLINE_DEST" ]] && [[ "$(readlink "$STATUSLINE_DEST")" == "$STATUSLINE_SRC" ]]; then
    echo "✅ claude-status-line.sh is already symlinked."
  elif [[ -f "$STATUSLINE_DEST" ]] && [[ ! -L "$STATUSLINE_DEST" ]]; then
    echo "⚠️  $STATUSLINE_DEST is a regular file. Please manually replace it with a symlink:"
    echo "    rm $STATUSLINE_DEST"
    echo "    ln -sf $STATUSLINE_SRC $STATUSLINE_DEST"
  else
    echo "✨ Creating symlink for claude-status-line.sh..."
    ln -sf "$STATUSLINE_SRC" "$STATUSLINE_DEST"
    echo "✅ Symlinked: $STATUSLINE_DEST → $STATUSLINE_SRC"
    echo "📝 Add the following to ~/.claude/settings.json:"
    echo '   "statusLine": { "type": "command", "command": "bash ~/.claude/claude-status-line.sh" }'
  fi
fi

# 3. Agent skills symlinks
echo "🔧 Setting up Agent Skills..."

for agent in "${AGENTS[@]}"; do
  case "$agent" in
    claude) DEST_BASE="$HOME/.claude" ;;
    gemini) DEST_BASE="$HOME/.gemini" ;;
    opencode) DEST_BASE="$HOME/.config/opencode" ;;
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
