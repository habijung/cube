---
task-id: install-uninstall-flag
status: done
branch: main
created: 2026-05-15
closed: 2026-05-22
final-commit: 9f3e2a1
---

# Plan Closeout: install-uninstall-flag — Add --uninstall flag to scripts/install.sh

> **EXAMPLE** — 이 문서는 `cube-plan --close` 스킬의 **closeout** 형식 예시입니다. 실제 작업 문서가 아닙니다. 원본 plan은 `examples/cube-plan.md` 참조.

## 1. Outcome

<!-- required: 1-paragraph summary, branch, final-commit -->

`scripts/install.sh`에 `--uninstall [agents...]` 플래그를 추가하여 `check_installation`(L29-178)이 진단하는 모든 항목을 역연산으로 안전하게 제거하는 기능을 구현했다. `cube_owned_symlink` 술어로 사용자 커스텀 파일 보존을 일관 보장하고, awk+mv 패턴으로 macOS/Linux 호환성을 확보했으며, Enumerate/Preview/Confirm/Execute 4단계 lifecycle로 부분 실패 시에도 본체(심볼릭)는 우선 정리되도록 설계했다. `--force` 옵션으로 CI/CD 비대화형 환경도 지원한다.

- **Result:** `--uninstall` 플래그 완전 구현. README/CLAUDE.md 문서 업데이트. 모든 AC ✅.
- **Branch:** `main`
- **Final Commit:** `9f3e2a1`

## 2. Changes Made

<!-- required: file list with commit refs (or commit-by-commit summary) -->

| File                                              | Change | Commit    |
| :------------------------------------------------ | :----- | :-------- |
| `scripts/install.sh` (헬퍼 3개 + 파서 case 확장)  | MODIFY | `7a2b8c4` |
| `scripts/install.sh` (`uninstall_installation()`) | MODIFY | `9f3e2a1` |
| `README.md` (`## Usage` 섹션)                     | MODIFY | `9f3e2a1` |
| `CLAUDE.md` (`### Key Commands` 항목)             | MODIFY | `9f3e2a1` |

헬퍼·인자 파서 추출(`7a2b8c4`)과 본체 + 문서(`9f3e2a1`)를 원자적 커밋 원칙으로 분리.

## 3. Decisions

<!-- preserved from plan §6 + any closeout-time additions -->

| #   | Date       | Decision                                              | Reason                                                     | Impact                              |
| :-- | :--------- | :---------------------------------------------------- | :--------------------------------------------------------- | :---------------------------------- |
| 1   | 2026-05-15 | `--force` 플래그 추가                                 | CI/CD 비대화형 환경 지원                                   | 파서 +1 옵션                        |
| 2   | 2026-05-15 | `--check`와 `--uninstall` 상호 배타                   | 동시 지정 시 의미 모호                                     | exit 2 즉시 거부                    |
| 3   | 2026-05-15 | `settings.json` 조건부 제거 (cube 소유 검증)          | 사용자 커스텀 statusLine 보존                              | python3 heredoc 추가                |
| 4   | 2026-05-15 | RC_FILE은 타임스탬프 백업 + awk + mv 패턴             | macOS/Linux 호환 + 복원 가능                               | `sed -i` 미사용                     |
| 5   | 2026-05-15 | `cube_owned_symlink` 술어로 모든 `rm` 가드            | TOCTOU 방어 + 사용자 파일 보존                             | 헬퍼 1개, 모든 단계 호출            |
| 6   | 2026-05-15 | 4단계 lifecycle (Enumerate/Preview/Confirm/Execute)   | `check_installation`과 미러링하여 유지보수성 확보          | `uninstall_installation()` 명확 분기 |
| 7   | 2026-05-22 | TOCTOU 재검증을 Execute 모든 op에 일괄 적용           | 단일 op 실패가 전체 흐름을 막지 않도록 isolated skip 처리  | skipped 카운터로 추적 가능          |

## 4. Known Issues & Follow-ups

<!-- limitations, deferred items, recommended follow-up plans -->

- **Limitation:** Gemini `enablePermanentToolApproval`은 원래 값으로 복원되지 않고 단순 키 삭제만 수행. install 흐름이 원래 값을 보존하지 않으므로 사용자 책임.
- **Limitation:** `--uninstall` 실패 시 자동 rollback 없음. counters(`failed`)와 skipped 항목으로 사용자 수동 확인. 멱등 재실행은 가능.
- **Follow-up:** install이 사용자 원래 값을 `.cube/install-state.json`에 저장하면 진짜 복원 가능. 별도 plan에서 다룬다.
- **Follow-up:** `--uninstall` BATS 테스트 스위트 도입 — install/uninstall 라운드트립 + edge case 자동화.
- **Follow-up:** `--dry-run` 옵션 검토 — Preview Phase만 실행 후 종료.

## 5. Verification Results

<!-- required: each Acceptance Criterion marked ✅/❌ with verification method -->

- ✅ **`--uninstall`, `--force`, `--help` 정상 인식 + `--check` 동시 지정 시 exit 2** — `bash ./scripts/install.sh --uninstall --check; echo $?` → `2` 확인.
- ✅ **`cube_owned_symlink`가 모든 `rm` 직전 호출** — `grep -B 2 "rm " scripts/install.sh | grep -c cube_owned_symlink`가 `rm` 호출 횟수와 일치.
- ✅ **4단계 lifecycle 흐름 준수** — `uninstall_installation()` 본체에 Enumerate/Preview/Confirm/Execute 주석과 명확한 분기 존재.
- ✅ **RC_FILE에서 cube source 라인 + 주석 함께 제거 + 백업 생성** — 테스트 RC로 awk 결과 검증, `ls ~/.zshrc.cube-uninstall.bak.*` 1개 확인.
- ✅ **Claude statusLine 조건부 제거** — `statusLine.command`를 `echo hi`로 변경한 케이스에서 `preserved` 출력 + 키 유지.
- ✅ **Gemini policies / OpenCode plugins / agent skills 소유 검증** — 각 항목 `noop` 케이스와 `removed` 케이스 모두 테스트.
- ✅ **`removed / skipped / failed` 카운터 출력** — `🏁 Uninstall complete: 8 removed, 2 skipped, 0 failed` 형식 확인.
- ✅ **두 번 연속 실행 시 멱등성** — 2회차에서 `✨ Nothing to uninstall` + exit 0.
- ✅ **비대화형 환경에서 `--force` 없이도 진행** — `bash ./scripts/install.sh --uninstall < /dev/null` 통과 확인.
- ✅ **README.md / CLAUDE.md 문서 업데이트** — `grep -c "uninstall" README.md CLAUDE.md` 모두 ≥ 1.
