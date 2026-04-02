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

# 2. 에이전트별 스킬/명령어 심볼릭 링크 (추후 구현)
echo "🔧 Future tasks: Linking skills and commands to agent config directories..."

echo "🏁 Setup complete!"
