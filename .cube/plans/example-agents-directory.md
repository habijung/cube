# Plan: agents-directory

> **EXAMPLE** — 이 문서는 `cube-plan` 스킬의 출력 형식 예시입니다. 실제 작업 문서가 아닙니다.

## 1. Context

- **Repository:** cube (로컬)
- **Branch:** main
- **Tech Stack:** Bash, Zsh, JavaScript (Node.js)
- **Architecture & Conventions:**
  - AI 에이전트 전용 리소스(Claude status-line, OpenCode 플러그인 등) 중앙 관리
  - 배포 대상 경로 미러링 구조 (`agents/` 하위)
  - 스킬 네이밍 (`cube-` prefix), Conventional Commits (feat/fix/refactor/plan)
- **Key Commands:** Install: `bash ./scripts/install.sh [agents...]`, Diagnose: `bash ./scripts/install.sh --check`
- **Relevant Code:** `scripts/install.sh`, `agents/claude/claude-status-line.sh`, `agents/opencode/plugins/cmux-notify.js`
- **Recent Commits:**
  - `aa399d5` feat: Add OpenCode cmux notification plugin with install support
  - `2c45388` refactor: Introduce agents/ directory for agent-specific resources
  - `338a036` feat: Add --copy clipboard flag to cube-summary skill

## 2. Overview

에이전트 전용 리소스(Claude status-line, OpenCode 플러그인 등)를 cube 저장소 내에서 일관되게 관리하기 위해 `agents/` 디렉토리를 도입한다. 기존에는 `scripts/`에 혼재되어 있거나 외부에서 개별 관리되던 파일들을 배포 대상 경로를 미러링하는 구조로 통합한다.

`install.sh`를 확장하여 `agents/` 하위 리소스의 심볼릭 링크 생성과 진단(`--check`)을 자동화한다.

- **References:** `scripts/install.sh`, `agents/` 디렉토리 구조

## 3. Progress & Phases

- **Total:** 11/11 tasks
- **Done:** 11
- **Remaining:** 0

### Phase 1: 디렉토리 구조 도입 및 기존 리소스 이동

- [x] Task 1.1: `agents/claude/` 디렉토리 생성
- [x] Task 1.2: `scripts/claude-status-line.sh` → `agents/claude/claude-status-line.sh` 이동
- [x] Task 1.3: `install.sh`의 Claude status-line 경로를 `agents/claude/`로 변경
- [x] Task 1.4: CLAUDE.md에 `agents/` 디렉토리 설명 추가

### Phase 2: OpenCode 플러그인 통합

- [x] Task 2.1: `agents/opencode/plugins/` 디렉토리 생성
- [x] Task 2.2: `cmux-notify.js` 플러그인 파일 작성
- [x] Task 2.3: `install.sh`에 OpenCode 플러그인 심볼릭 링크 로직 추가
- [x] Task 2.4: `install.sh --check`에 OpenCode 플러그인 진단 로직 추가

### Phase 3: 검증 및 정리

- [x] Task 3.1: `install.sh --check` 실행하여 진단 로직 검증
- [x] Task 3.2: `install.sh opencode` 실행하여 심볼릭 링크 생성 확인
- [x] Task 3.3: 기존 원본 파일(`~/.config/opencode/plugins/cmux-notify.js`) 정리

### Unplanned

(없음)

## 4. Decisions

| #   | Date       | Decision                                   | Reason                                                              | Impact                                    |
| :-- | :--------- | :----------------------------------------- | :------------------------------------------------------------------ | :---------------------------------------- |
| 1   | 2026-04-09 | 디렉토리명 `agents/` 채택                  | Claude, Gemini, OpenCode 모두 공식적으로 "agent"로 자칭             | 네이밍 일관성 확보                        |
| 2   | 2026-04-09 | 배포 대상 경로 미러링 구조 사용            | `plugins/opencode/`(타입 우선)보다 직관적, install.sh 유지보수 용이 | agents/opencode/plugins/ 형태로 구조화    |
| 3   | 2026-04-09 | `scripts/install.sh`와 `cube.sh` 위치 유지 | 성격이 다름: cube.sh는 쉘 source 설정, install.sh는 도구            | 기존 경로 유지로 하위 호환성 보장         |
| 4   | 2026-04-09 | 리팩토링과 신규 기능을 별도 커밋으로 분리  | 원자적 커밋 원칙 준수                                               | 2개 커밋으로 분리 (2c45388, aa399d5)      |
| 5   | 2026-04-09 | 기존 원본 파일 삭제 후 심볼릭 링크 교체    | 파일이 cube repo로 통합되어 원본 불필요                             | ~/.config/opencode/plugins/ 심볼릭 링크화 |
