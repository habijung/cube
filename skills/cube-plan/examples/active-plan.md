---
task-id: example-agents-directory
status: active
branch: main
created: 2026-04-09
---

# Plan: example-agents-directory — 에이전트 전용 리소스 통합 관리

> **EXAMPLE** — 이 문서는 `cube-plan` 스킬의 **활성 plan** 형식 예시입니다. 실제 작업 문서가 아닙니다. close 후 형식은 `examples/closeout.md` 참조.

## 1. Context

- **Repository:** cube (로컬)
- **Branch:** main
- **Tech Stack:** Bash, Zsh, JavaScript (Node.js)
- **Architecture & Conventions:**
  - AI 에이전트 전용 리소스(Claude status-line, OpenCode 플러그인 등) 중앙 관리
  - 배포 대상 경로 미러링 구조 (`agents/` 하위)
  - 스킬 네이밍 (`cube-` prefix), Conventional Commits (feat/fix/refactor/plan)
- **Key Commands:** Install: `bash ./scripts/install.sh [agents...]`, Diagnose: `bash ./scripts/install.sh --check`
- **Relevant Code:** `scripts/install.sh`, `~/.config/opencode/plugins/`, `~/.claude/`
- **Recent Commits:**
  - `aa399d5` feat: Add OpenCode cmux notification plugin with install support
  - `2c45388` refactor: Introduce agents/ directory for agent-specific resources
  - `338a036` feat: Add --copy clipboard flag to cube-summary skill

## 2. Overview

에이전트 전용 리소스(Claude status-line, OpenCode 플러그인 등)를 cube 저장소 내에서 일관되게 관리하기 위해 `agents/` 디렉토리를 도입한다. 기존에는 `scripts/`에 혼재되어 있거나 외부에서 개별 관리되던 파일들을 배포 대상 경로를 미러링하는 구조로 통합한다.

`install.sh`를 확장하여 `agents/` 하위 리소스의 심볼릭 링크 생성과 진단(`--check`)을 자동화한다.

- **References:** `scripts/install.sh`, `agents/` 디렉토리 구조

## 3. Implementation Strategy

### 3.1 Approach

배포 대상 경로(`~/.claude/`, `~/.config/opencode/`)의 구조를 cube 저장소 내 `agents/<agent>/` 하위에 그대로 미러링한다. 이 방식은 (a) `plugins/<agent>/`처럼 타입 우선 구조보다 직관적이고, (b) `install.sh` 유지보수가 간단하며, (c) 새 에이전트 추가 시 디렉토리만 추가하면 되어 확장성이 좋다.

기존 원본 파일은 삭제 후 심볼릭 링크로 교체하여 cube 저장소가 유일한 원본(single source of truth)이 되도록 한다.

### 3.2 Files Affected

| Path                                          | Change | Why                                              |
| :-------------------------------------------- | :----- | :----------------------------------------------- |
| `agents/claude/claude-status-line.sh`         | NEW    | `scripts/`에서 이동 (배포 경로 미러링)           |
| `scripts/claude-status-line.sh`               | DELETE | 위 이동에 따른 정리                              |
| `agents/opencode/plugins/cmux-notify.js`      | NEW    | OpenCode tmux 알림 플러그인 통합                 |
| `scripts/install.sh`                          | MODIFY | agents/ 하위 자원의 symlink 생성·진단 로직 추가  |
| `CLAUDE.md`                                   | MODIFY | `agents/` 디렉토리 설명 추가                     |

### 3.3 Risks & Mitigations

- **Risk:** 기존 사용자의 `~/.claude/claude-status-line.sh` 심볼릭 링크가 깨짐 → **Mitigation:** `install.sh --check`에서 구 경로 감지 시 안내 메시지 출력
- **Risk:** OpenCode 플러그인 디렉토리가 없는 환경에서 install 실패 → **Mitigation:** 디렉토리 자동 생성 후 symlink 생성
- **Risk:** 외부에 흩어진 원본 파일 삭제로 데이터 손실 → **Mitigation:** symlink 교체 전 파일 내용을 cube 저장소로 먼저 복사하고 commit, 검증 후 삭제

### 3.4 Verification

- `bash ./scripts/install.sh --check` 실행 → 모든 agent 자원이 "OK"로 표시되는지 확인
- `bash ./scripts/install.sh opencode` 실행 → `~/.config/opencode/plugins/cmux-notify.js`가 cube 저장소를 가리키는 symlink인지 `ls -l`로 확인
- `~/.claude/claude-status-line.sh`가 `agents/claude/claude-status-line.sh`를 가리키는지 확인
- Claude Code 재시작 후 status-line이 정상 표시되는지 확인

### 3.5 Acceptance Criteria

- [x] 모든 agent 전용 자원이 `agents/<agent>/` 하위에 배치됨
- [x] `install.sh`가 `agents/` 하위 자원의 symlink를 자동 생성함
- [x] `install.sh --check`가 새 구조를 진단함
- [x] 기존 외부 원본 파일이 정리되고 cube 저장소가 single source of truth임

## 4. Progress & Phases

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

## 5. Out of Scope

- **`scripts/install.sh`와 `cube.sh` 자체의 위치 변경:** 두 파일은 성격이 다름 — `cube.sh`는 쉘 source 설정, `install.sh`는 도구. 기존 경로 유지로 하위 호환성 보장.
- **Gemini CLI 자원 통합:** 본 작업은 Claude/OpenCode에 집중. Gemini CLI 자원이 추가될 때 동일 구조(`agents/gemini/`)로 별도 plan에서 다룬다.
- **다른 에이전트 자원의 자동 발견 로직:** `agents/` 하위를 자동 스캔하여 install하는 동적 로직은 복잡도 대비 이점이 작음 — 명시적 case-by-case로 유지.

## 6. Decisions

| #   | Date       | Decision                                   | Reason                                                              | Impact                                    |
| :-- | :--------- | :----------------------------------------- | :------------------------------------------------------------------ | :---------------------------------------- |
| 1   | 2026-04-09 | 디렉토리명 `agents/` 채택                  | Claude, Gemini, OpenCode 모두 공식적으로 "agent"로 자칭             | 네이밍 일관성 확보                        |
| 2   | 2026-04-09 | 배포 대상 경로 미러링 구조 사용            | `plugins/opencode/`(타입 우선)보다 직관적, install.sh 유지보수 용이 | agents/opencode/plugins/ 형태로 구조화    |
| 3   | 2026-04-09 | `scripts/install.sh`와 `cube.sh` 위치 유지 | 성격이 다름: cube.sh는 쉘 source 설정, install.sh는 도구            | 기존 경로 유지로 하위 호환성 보장         |
| 4   | 2026-04-09 | 리팩토링과 신규 기능을 별도 커밋으로 분리  | 원자적 커밋 원칙 준수                                               | 2개 커밋으로 분리 (2c45388, aa399d5)      |
| 5   | 2026-04-09 | 기존 원본 파일 삭제 후 심볼릭 링크 교체    | 파일이 cube repo로 통합되어 원본 불필요                             | ~/.config/opencode/plugins/ 심볼릭 링크화 |
