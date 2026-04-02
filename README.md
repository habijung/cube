# Cube 🧊

**AI Agent Configuration System**

에이전트별로 산재된 설정과 지침(Instructions)을 통합하여 관리하고, 여러 프로젝트에 일관되게 적용하기 위한 범용 설정 시스템입니다.

## 📂 Directory Structure

- `skills/`: 모든 에이전트(Claude, Gemini, OpenCode 등)가 공유하는 통합 지침 (SKILL.md 포맷)
- `.config/opencode/`: OpenCode 전역 설정 템플릿
- `templates/AGENTS.md`: 개별 프로젝트 루트에 복사하여 사용하는 로컬 지침 템플릿
- `scripts/install.sh`: 설정 및 심볼릭 링크 자동화 스크립트
- `cube.zsh`: 에이전트 실행 단축 명령어(Alias) 모음

## 🚀 Getting Started

이 프로젝트를 로컬에 클론한 후, 다음 스크립트를 실행하여 설정을 적용합니다:

```zsh
source ./scripts/install.sh
```
