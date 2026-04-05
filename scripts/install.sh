#!/usr/bin/env bash

# Cube 🧊 - AI Agent Config Installer

# 현재 디렉토리가 cube 저장소 루트인지 확인
if [[ ! -f "cube.sh" ]]; then
  echo "❌ Error: Please run this script from the 'cube' root directory."
  exit 1
fi

CUBE_PATH="$(pwd)"
echo "📦 Cube detected at: $CUBE_PATH"

# 인자 처리
AGENTS=("$@")
if [[ ${#AGENTS[@]} -eq 0 ]]; then
  echo "ℹ️  No agents specified. Defaulting to: claude, gemini, opencode"
  AGENTS=("claude" "gemini" "opencode")
fi

# 1. Alias 등록 (cube.sh)
# 사용자의 쉘을 확인하여 ~/.bashrc 또는 ~/.zshrc 에 source 구문 추가
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
  echo "⚠️  Unsupported shell: $DETECTED_SHELL. Defaulting to ~/.bashrc"
  RC_FILE="$HOME/.bashrc"
fi

if ! grep -q "source $CUBE_PATH/cube.sh" "$RC_FILE" 2>/dev/null; then
  echo "✨ Adding cube.sh to $RC_FILE..."
  # echo "source $CUBE_PATH/cube.sh" >> "$RC_FILE"
  echo "⚠️  [Dry Run] $RC_FILE 에 다음 줄을 추가하세요: source $CUBE_PATH/cube.sh"
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
    echo "⚠️  [Dry Run] $STATUSLINE_DEST 는 일반 파일입니다. 수동으로 symlink로 교체하세요:"
    echo "    rm $STATUSLINE_DEST"
    echo "    ln -sf $STATUSLINE_SRC $STATUSLINE_DEST"
  else
    echo "✨ Creating symlink for claude-status-line.sh..."
    ln -sf "$STATUSLINE_SRC" "$STATUSLINE_DEST"
    echo "✅ Symlinked: $STATUSLINE_DEST → $STATUSLINE_SRC"
    echo "📝 ~/.claude/settings.json 에 다음 항목을 추가하세요:"
    echo '   "statusLine": { "type": "command", "command": "bash ~/.claude/claude-status-line.sh" }'
  fi
fi

# 3. Agent skills symlinks
echo "🔧 Setting up Agent Skills..."
SKILLS_SRC="$CUBE_PATH/skills"

for agent in "${AGENTS[@]}"; do
  case "$agent" in
    claude) DEST_BASE="$HOME/.claude" ;;
    gemini) DEST_BASE="$HOME/.gemini" ;;
    opencode) DEST_BASE="$HOME/.config/opencode" ;;
    *) echo "⚠️  Unknown agent: $agent. Skipping..."; continue ;;
  esac

  SKILLS_DEST="$DEST_BASE/skills"
  mkdir -p "$SKILLS_DEST"

  # cube-* 패턴에 일치하는 폴더 검색
  for skill_dir in "$SKILLS_SRC"/cube-*/; do
    # 마지막 슬래시 제거
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