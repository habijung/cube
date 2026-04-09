> **EXAMPLE** — 이 문서는 `cube-plan` 스킬의 출력 형식 예시입니다. 실제 작업 문서가 아닙니다.

# Progress: agents-directory

## Summary

- **Total:** 11/11 tasks
- **Done:** 11
- **Remaining:** 0

## Phase 1: 디렉토리 구조 도입 및 기존 리소스 이동

- [x] Task 1.1: `agents/claude/` 디렉토리 생성
- [x] Task 1.2: `scripts/claude-status-line.sh` → `agents/claude/claude-status-line.sh` 이동
- [x] Task 1.3: `install.sh`의 Claude status-line 경로를 `agents/claude/`로 변경
- [x] Task 1.4: CLAUDE.md에 `agents/` 디렉토리 설명 추가

## Phase 2: OpenCode 플러그인 통합

- [x] Task 2.1: `agents/opencode/plugins/` 디렉토리 생성
- [x] Task 2.2: `cmux-notify.js` 플러그인 파일 작성
- [x] Task 2.3: `install.sh`에 OpenCode 플러그인 심볼릭 링크 로직 추가
- [x] Task 2.4: `install.sh --check`에 OpenCode 플러그인 진단 로직 추가

## Phase 3: 검증 및 정리

- [x] Task 3.1: `install.sh --check` 실행하여 진단 로직 검증
- [x] Task 3.2: `install.sh opencode` 실행하여 심볼릭 링크 생성 확인
- [x] Task 3.3: 기존 원본 파일 정리

### Unplanned

(없음)
