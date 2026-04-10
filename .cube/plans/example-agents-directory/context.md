# Context: agents-directory

> **EXAMPLE** — 이 문서는 `cube-plan` 스킬의 출력 형식 예시입니다. 실제 작업 문서가 아닙니다.

## Project

- **Repository:** cube (로컬)
- **Branch:** main
- **Recent Commits:**
  - `aa399d5` feat: Add OpenCode cmux notification plugin with install support
  - `2c45388` refactor: Introduce agents/ directory for agent-specific resources
  - `338a036` feat: Add --copy clipboard flag to cube-summary skill

## Tech Stack

- **Languages:** Bash, Zsh, JavaScript (Node.js)
- **Frameworks:** N/A (쉘 스크립트 기반 도구)
- **Database:** N/A

## Architecture

Cube는 AI 에이전트(Claude Code, Gemini CLI, OpenCode)의 설정과 스킬을 중앙에서 관리하는 시스템이다.

```text
cube/
├── agents/       ← 에이전트 전용 리소스 (배포 대상 경로 미러링)
├── scripts/      ← cube 자체 유틸리티 (install.sh)
├── skills/       ← 에이전트 공유 스킬 (cube-* prefix)
├── templates/    ← 프로젝트 템플릿
└── cube.sh       ← 쉘 alias 모음 (source용)
```

## Conventions

- **스킬 네이밍:** `cube-` prefix 필수
- **커밋 컨벤션:** Conventional Commits (feat/fix/refactor/plan)
- **크로스 쉘:** Bash/Zsh 모두 호환
- **원자적 커밋:** 리팩토링과 신규 기능은 별도 커밋

## Key Commands

- **Install:** `bash ./scripts/install.sh [agents...]`
- **Diagnose:** `bash ./scripts/install.sh --check`
- **Alias 적용:** `source ~/.zshrc`

## Relevant Code

- `scripts/install.sh` — 심볼릭 링크 생성 및 환경 진단의 핵심 스크립트
- `agents/claude/claude-status-line.sh` — Claude Code 상태줄 (기존 scripts/에서 이동)
- `agents/opencode/plugins/cmux-notify.js` — OpenCode tmux 세션 알림 플러그인 (신규)
