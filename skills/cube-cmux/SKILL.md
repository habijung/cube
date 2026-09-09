---
name: cube-cmux
description: cmux 패널의 AI 에이전트 세션을 파일로 저장하고, cmux 세션 복원이 실패했을 때 누락된 세션의 재개 명령어를 안내합니다.
trigger:
  - /cube-cmux
  - 세션 저장
  - 세션 복구
  - cmux
argument-hint: "[list | save | status | restore [번호]]"
disable-model-invocation: false # Claude, User 모두 사용 가능
allowed-tools: Bash
compatibility: opencode, claude, gemini
---

# cmux Session Keeper

cmux는 종료 시 각 패널의 에이전트 세션 정보를 자체 파일에 기록하고 재시작할 때 복원합니다. 대부분 잘 동작하지만 **아주 가끔 일부 패널이 복원되지 않습니다.** 이 스킬은 그 상황에 대비해 세션 목록을 별도 파일로 남겨두고, 복원 실패 시 누락된 세션만 골라 재개 명령어를 안내합니다.

세션 데이터 자체는 각 에이전트가 이미 보관합니다. 이 스킬은 세션 ID와 작업 경로, 워크스페이스·패널 이름을 연결 정보로 저장합니다. 표준 재개 명령이 없는 에이전트는 복구에 필요한 실행 인자도 함께 저장합니다.

특히 **cmux가 자체 연동을 제공하지 않는 에이전트**(예: antigravity)는 cmux 스스로 복원하지 못하므로, 이 스킬이 유일한 복구 수단이 됩니다.

## 지원 에이전트

| 에이전트 | 재개 명령어 | 세션 데이터 확인 위치 |
| :------------ | :------------------------------ | :--------------------------------------------- |
| `claude` | `claude --resume <id>` | `~/.claude/projects/<슬러그>/<id>.jsonl` |
| `opencode` | `opencode --session <id>` | `~/.local/share/opencode/opencode.db` |
| `antigravity` | cmux가 기록한 실행 인자 재사용 | `~/.gemini/antigravity-cli/conversations/<id>.*` |
| 그 외 | 실행 인자에 세션 식별자가 있으면 재사용 | 확인 불가 (판정 보류) |

목록에 없는 에이전트라도 cmux가 기록한 실행 인자에 세션 식별자가 포함되어 있으면 그 인자를 그대로 재사용해 재개 명령어를 만듭니다. 식별자가 없으면 "재개 방법 미상"으로 표시하되, 작업 경로와 세션 ID는 남겨 수동 복구를 돕습니다.

## Usage

| 명령 | 동작 |
| :---------------------- | :------------------------------------------------- |
| `/cube-cmux list` | 현재 열린 에이전트 패널 목록 조회 (저장하지 않음) |
| `/cube-cmux save` | 현재 열린 모든 에이전트 패널을 저장 파일에 기록 |
| `/cube-cmux` | 저장 목록과 현재 패널을 대조 (기본값, `status`) |
| `/cube-cmux restore` | 누락된 세션 목록 출력 (1개면 클립보드 자동 복사) |
| `/cube-cmux restore 3` | 3번 세션의 명령어만 클립보드에 복사 |

## Instructions

`scripts/cmux_session.py`를 Bash로 실행하고, 그 출력을 사용자에게 그대로 전달하세요.

```sh
python3 "$SKILL_DIR/scripts/cmux_session.py" [list|save|status|restore] [번호]
```

- **Path Resolution:** `$SKILL_DIR`은 이 `SKILL.md`가 있는 디렉토리입니다. 환경에 따라 심볼릭 링크로 연결되어 있으므로, 경로를 하드코딩하지 말고 스킬 파일 기준 상대 경로로 실행하세요.
- **No Interpretation:** 스크립트 출력은 이미 사용자용으로 정리되어 있습니다. 요약하거나 재구성하지 말고 그대로 보여준 뒤, 필요한 경우에만 다음 행동을 한 줄로 덧붙이세요.
- **Argument Passing:** 사용자가 번호를 지정하면(`/cube-cmux restore 3`) 그대로 전달하세요.
- **Default Command:** 인자가 없으면 `status`를 실행합니다.

## Guidelines

- **No Auto Execution:** 재개 명령어를 대신 실행하지 마세요. 각 세션은 대화형 TUI라서 실행하면 그 패널을 점유합니다. 여러 개를 한 패널에서 순차 실행하면 두 번째부터는 첫 세션이 끝날 때까지 대기하게 됩니다. **명령어는 사용자가 각각 다른 패널에 붙여넣어야 합니다.**
- **Stable Numbering:** 번호는 저장 시점의 순서를 그대로 유지합니다. 복구가 하나씩 진행되어도 번호가 밀리지 않으므로, 처음 출력된 번호를 계속 사용하면 됩니다.
- **Stale List Warning:** `status`가 "저장 이후 새로 생긴 세션"을 보고하면 저장 파일이 낡은 것입니다. 사용자에게 `save`를 권하세요.
- **Session Count Drop:** `save` 실행 시 "직전 저장은 N개였습니다" 경고가 나오면, 복원 실패 상태에서 저장한 것입니다. 누락된 세션은 **이전 저장 파일에만** 남아 있으므로, 복구를 마칠 때까지 그 파일을 지우지 않도록 안내하세요.
- **Missing Session Data:** 목록에 `!` 표시가 붙거나 "세션 데이터 없음" 경고가 나오면, 에이전트 쪽 대화 기록이 이미 삭제된 것입니다. 명령어를 실행해도 빈 세션이 열릴 수 있음을 알려주세요. 단, 저장 위치를 모르는 에이전트는 판정을 보류하므로 `!`가 붙지 않습니다.
- **Unknown Agents:** cmux 연동이 없는 에이전트는 cmux 자체 복원이 동작하지 않으므로, 재시작 후 그 패널이 사라졌다면 이 스킬의 명령어가 유일한 복구 수단입니다. "재개 방법 미상"으로 표시된 경우에는 명령어 대신 작업 경로와 세션 ID를 근거로 수동 복구를 안내하세요.
- **Agent Independence:** 이 스크립트는 어느 에이전트에서 실행하든 동일하게 동작합니다. 훅에 연결하지 마세요 — 에이전트마다 훅 형식이 달라 호환성 부담만 늘어납니다.

## When to Save

수동 저장이므로 다음 시점에 실행하는 것이 좋습니다.

- PC 재시작이나 cmux 종료 **직전**
- 새 워크스페이스를 열어 작업을 시작한 **직후**
- 복구를 마친 **직후** (목록 갱신)

## Notes

- **저장 위치:** `~/Desktop/cmux-sessions-<YYMMDD-HHMM>.md` (디렉토리는 환경변수 `CUBE_CMUX_SAVE_DIR`로 변경 가능)
- **파일 선택:** `save`는 실행할 때마다 새 파일을 만들고, `status`와 `restore`는 **가장 최근 파일**을 자동으로 선택합니다.
- **파일 수명:** 복구를 마친 파일은 삭제해도 됩니다. 자동으로 지우지 않으므로 바탕화면 정리는 사용자가 직접 합니다.
- **읽는 파일:** 패널 목록은 `~/Library/Application Support/cmux/session-com.cmuxterm.app.json`에서 읽습니다. 세션 데이터 존재 여부(`!` 표시) 판정을 위해 `~/.claude/projects/`의 jsonl, `~/.local/share/opencode/opencode.db`, `~/.gemini/antigravity-cli/conversations/`도 조회합니다. **모두 읽기 전용이며 cmux나 에이전트 설정을 수정하지 않습니다.**
- **저장 내용:** 세션 ID, 작업 경로, 워크스페이스·패널 이름을 저장합니다. 표준 재개 명령이 없는 에이전트는 cmux가 기록한 실행 인자도 포함될 수 있으므로 자격 증명을 CLI 인자로 전달하지 마세요.
- **의존성:** python3 표준 라이브러리, macOS `pbcopy`
- **저장 파일 구조:** 사람이 읽는 목록과 `restore`가 파싱하는 JSON 블록이 한 파일에 함께 들어갑니다. JSON 블록은 직접 편집하지 마세요.

---

**Updated At:** 2026. 9. 8.
