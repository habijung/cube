---
task-id: example-agents-directory
status: done
branch: main
created: 2026-04-09
closed: 2026-04-09
final-commit: aa399d5
---

# Plan Closeout: example-agents-directory — 에이전트 전용 리소스 통합 관리

> **EXAMPLE** — 이 문서는 `cube-plan --close` 스킬의 **closeout** 형식 예시입니다. 실제 작업 문서가 아닙니다. 원본 plan은 `examples/active-plan.md` 참조.

## 1. Outcome
<!-- required: 1-paragraph summary, branch, final-commit -->

AI 에이전트 전용 리소스(Claude status-line, OpenCode 플러그인 등)를 cube 저장소 내 `agents/<agent>/` 하위로 통합하고, `install.sh`가 심볼릭 링크 생성과 진단을 자동화하도록 확장했다. 배포 대상 경로 미러링 구조 채택으로 새 에이전트 추가 시 디렉토리만 추가하면 되어 확장성이 확보되었으며, 외부에 흩어져 있던 원본 파일을 정리하여 cube 저장소가 single source of truth가 되었다.

- **Result:** `agents/` 디렉토리 도입 완료. install.sh가 Claude/OpenCode 자원의 symlink 생성·진단 자동 수행.
- **Branch:** `main`
- **Final Commit:** `aa399d5`

## 2. Changes Made
<!-- required: file list with commit refs (or commit-by-commit summary) -->

| File                                          | Change | Commit     |
| :-------------------------------------------- | :----- | :--------- |
| `agents/claude/claude-status-line.sh`         | NEW    | `2c45388`  |
| `scripts/claude-status-line.sh`               | DELETE | `2c45388`  |
| `scripts/install.sh` (Claude status-line 경로) | MODIFY | `2c45388`  |
| `CLAUDE.md` (`agents/` 디렉토리 설명 추가)    | MODIFY | `2c45388`  |
| `agents/opencode/plugins/cmux-notify.js`      | NEW    | `aa399d5`  |
| `scripts/install.sh` (OpenCode plugin 로직)   | MODIFY | `aa399d5`  |

원자적 커밋 원칙에 따라 리팩토링(`2c45388`)과 신규 기능(`aa399d5`) 두 개의 커밋으로 분리되었다.

## 3. Decisions
<!-- preserved from plan §6 + any closeout-time additions -->

| #   | Date       | Decision                                   | Reason                                                              | Impact                                    |
| :-- | :--------- | :----------------------------------------- | :------------------------------------------------------------------ | :---------------------------------------- |
| 1   | 2026-04-09 | 디렉토리명 `agents/` 채택                  | Claude, Gemini, OpenCode 모두 공식적으로 "agent"로 자칭             | 네이밍 일관성 확보                        |
| 2   | 2026-04-09 | 배포 대상 경로 미러링 구조 사용            | `plugins/opencode/`(타입 우선)보다 직관적, install.sh 유지보수 용이 | agents/opencode/plugins/ 형태로 구조화    |
| 3   | 2026-04-09 | `scripts/install.sh`와 `cube.sh` 위치 유지 | 성격이 다름: cube.sh는 쉘 source 설정, install.sh는 도구            | 기존 경로 유지로 하위 호환성 보장         |
| 4   | 2026-04-09 | 리팩토링과 신규 기능을 별도 커밋으로 분리  | 원자적 커밋 원칙 준수                                               | 2개 커밋으로 분리 (2c45388, aa399d5)      |
| 5   | 2026-04-09 | 기존 원본 파일 삭제 후 심볼릭 링크 교체    | 파일이 cube repo로 통합되어 원본 불필요                             | ~/.config/opencode/plugins/ 심볼릭 링크화 |

## 4. Known Issues & Follow-ups
<!-- limitations, deferred items, recommended follow-up plans -->

- **Limitation:** 기존 사용자가 `~/.claude/claude-status-line.sh` 심볼릭 링크를 수동으로 만들어 두었던 경우, 본 변경 후 깨질 수 있다. `install.sh --check`에서 안내 메시지로 감지하지만 자동 복구는 지원하지 않는다.
- **Limitation:** `agents/` 하위를 자동 스캔하여 install하는 동적 로직은 §5 Out of Scope에 따라 미구현. 새 에이전트 자원 추가 시 `install.sh`의 case 분기를 수동으로 수정해야 한다.
- **Follow-up:** Gemini CLI 자원이 `agents/gemini/` 하위로 추가될 때 동일 구조를 적용하는 별도 plan 작성 권장.
- **Follow-up:** OpenCode 플러그인 디렉토리(`~/.config/opencode/plugins/`)가 없는 신규 환경에서 install이 실패하지 않는지 회귀 테스트 자동화 검토.

## 5. Verification Results
<!-- required: each Acceptance Criterion marked ✅/❌ with verification method -->

- ✅ **모든 agent 전용 자원이 `agents/<agent>/` 하위에 배치됨** — `ls -R agents/`로 `agents/claude/claude-status-line.sh`, `agents/opencode/plugins/cmux-notify.js` 양쪽 존재 확인.
- ✅ **`install.sh`가 `agents/` 하위 자원의 symlink를 자동 생성함** — `bash ./scripts/install.sh opencode` 실행 후 `ls -l ~/.config/opencode/plugins/cmux-notify.js`가 cube 저장소 경로를 가리키는 심볼릭 링크임을 확인.
- ✅ **`install.sh --check`가 새 구조를 진단함** — `bash ./scripts/install.sh --check` 실행 시 Claude status-line, OpenCode plugin 양쪽 "OK" 출력 확인.
- ✅ **기존 외부 원본 파일이 정리되고 cube 저장소가 single source of truth임** — `~/.config/opencode/plugins/cmux-notify.js`가 정규 파일이 아닌 심볼릭 링크임을 `file` 명령으로 확인.
