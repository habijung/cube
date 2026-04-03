#!/usr/bin/env zsh

# Cube 🧊 - AI Agent Config Installer

# 현재 디렉토리가 cube 저장소 루트인지 확인
if [[ ! -f "cube.zsh" ]]; then
  echo "❌ Error: Please run this script from the 'cube' root directory."
  exit 1
fi

CUBE_PATH="$(pwd)"
echo "📦 Cube detected at: $CUBE_PATH"

# 1. Alias 등록 (cube.zsh)
# ~/.zshrc 에 source 구문이 있는지 확인 후 추가
if ! grep -q "source $CUBE_PATH/cube.zsh" ~/.zshrc; then
  echo "✨ Adding cube.zsh to ~/.zshrc..."
  # echo "source $CUBE_PATH/cube.zsh" >> ~/.zshrc
  echo "⚠️  [Dry Run] ~/.zshrc 에 다음 줄을 추가하세요: source $CUBE_PATH/cube.zsh"
else
  echo "✅ cube.zsh is already sourced in ~/.zshrc."
fi

# 2. Claude Code status-line symlink
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

# 3. Claude Code skills symlinks
SKILLS_SRC="$CUBE_PATH/skills"
SKILLS_DEST="$HOME/.claude/skills"

mkdir -p "$SKILLS_DEST"

for skill_dir in "$SKILLS_SRC"/cube:*/; do
  skill_name=$(basename "$skill_dir")
  dest="$SKILLS_DEST/$skill_name"

  if [[ -L "$dest" ]] && [[ "$(readlink "$dest")" == "$skill_dir" ]]; then
    echo "✅ $skill_name is already symlinked."
  else
    ln -sf "$skill_dir" "$dest"
    echo "✅ Symlinked: $dest → $skill_dir"
  fi
done

# 4. 추가 에이전트 심볼릭 링크 (Gemini CLI, OpenCode 등 추후 구현)
# echo "🔧 Future: Linking skills and configs for other agents..."

echo "🏁 Setup complete!"
