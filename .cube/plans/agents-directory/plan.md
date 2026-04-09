# Plan: agents-directory

## Overview

에이전트 전용 리소스(Claude status-line, OpenCode 플러그인 등)를 cube 저장소 내에서 일관되게 관리하기 위해 `agents/` 디렉토리를 도입한다. 기존에는 `scripts/`에 혼재되어 있거나 외부에서 개별 관리되던 파일들을 배포 대상 경로를 미러링하는 구조로 통합한다.

`install.sh`를 확장하여 `agents/` 하위 리소스의 심볼릭 링크 생성과 진단(`--check`)을 자동화한다.

## Phases

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

## References

- `agents/claude/claude-status-line.sh` — Claude Code 상태줄 스크립트
- `agents/opencode/plugins/cmux-notify.js` — OpenCode cmux 알림 플러그인
- `scripts/install.sh` — 설치 및 진단 스크립트
