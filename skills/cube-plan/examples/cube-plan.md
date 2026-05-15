---
task-id: install-uninstall-flag
status: active
branch: main
created: 2026-05-15
---

# Plan: install-uninstall-flag — Add --uninstall flag to scripts/install.sh

> **EXAMPLE** — 이 문서는 `cube-plan` 스킬의 **활성 plan** 형식 예시입니다. 실제 작업 문서가 아닙니다. close 후 형식은 `examples/cube-plan-dev.md` 참조.

## 1. Context

- **Repository:** cube (로컬)
- **Branch:** main
- **Tech Stack:** Bash, Zsh, Python 3, Node.js
- **Architecture & Conventions:**
  - `scripts/install.sh`가 cube 저장소 → agent 홈 디렉토리로 심볼릭 링크 생성 + RC 파일 alias + settings.json 수정
  - 진단(`--check`)과 설치(`[agents...]`) 2개 모드 제공
  - 스킬 네이밍 (`cube-` prefix), Conventional Commits (feat/fix/refactor/plan)
- **Key Commands:** Install: `bash ./scripts/install.sh [agents...]`, Diagnose: `bash ./scripts/install.sh --check`
- **Relevant Code:** `scripts/install.sh:check_installation` (L29-178), `scripts/install.sh` 인자 파서 (L180-194)
- **Recent Commits:**
  - `6d9321f` fix: Improve statusLine setup robustness in install.sh
  - `32c1b2b` fix: Sync check_installation with renamed cube-status-line.sh
  - `c7929e2` fix: Ensure cube-status-line.sh is executable after git clone

## 2. Overview

`scripts/install.sh`는 현재 설치와 진단(`--check`)만 지원하며, 정리하려면 사용자가 수동으로 심볼릭 링크 / RC 라인 / settings.json 항목을 찾아 제거해야 한다. **`--uninstall` 플래그를 추가**하여 `check_installation`(L29-178)이 진단하는 모든 항목을 **역연산으로 안전하게 제거**한다.

설계 원칙: 역연산 대칭(`check_installation`과 1:1) · 소유권 검증(cube가 만든 심볼릭과 cube가 추가한 라인만 제거) · 선택적 범위(`--uninstall claude` 등) · `--force`로 비대화형 우회.

- **References:** `scripts/install.sh:check_installation`, `agents/claude/cube-status-line.sh`, `agents/gemini/policies/`, `agents/opencode/plugins/`

## 3. Implementation Strategy

### 3.1 Approach

`check_installation`의 단계별 진단 로직을 역순으로 미러링하되, 모든 `rm` 직전 `cube_owned_symlink` 술어로 소유권 검증을 일관 보장한다 (`[[ -L "$path" ]] && [[ "$(readlink "$path")" == "$expected" ]]` 형식). 인자 파서를 `case`로 확장하고, 메인 로직은 헬퍼 함수 3개 + `uninstall_installation()` 본체로 구성. 본체는 **Enumerate → Preview → Confirm → Execute & Report** 4단계 lifecycle을 따른다.

**트레이드오프**:

| 접근 | 장점 | 단점 |
| :--- | :--- | :--- |
| **A. 순수 제거** | 단순·예측 가능 | 사용자 데이터 유실 위험 |
| **B. 백업 후 제거** | 안전 | 디스크 사용·복잡도↑ |
| **C. 대화형 확인 + `--force`** ⭐ | 사용자 제어 + 자동화 양립 | UX 복잡도 미세 증가 |

**채택**: A + C 조합. RC_FILE은 타임스탬프 백업 자동 생성. settings.json은 cube 소유 검증 통과 시만 수정.

#### 3.1.1 인자 파서 확장 (L180-194 교체)

```bash
AGENTS=()
CHECK_MODE=false; UNINSTALL_MODE=false; FORCE_MODE=false

for arg in "$@"; do
  case "$arg" in
    --check)     CHECK_MODE=true ;;
    --uninstall) UNINSTALL_MODE=true ;;
    --force|-f)  FORCE_MODE=true ;;
    --help|-h)   print_help; exit 0 ;;
    --*)         echo "❌ Unknown option: $arg"; exit 2 ;;
    *)           AGENTS+=("$arg") ;;
  esac
done

[[ "$CHECK_MODE" == true && "$UNINSTALL_MODE" == true ]] && {
  echo "❌ --check and --uninstall are mutually exclusive."; exit 2; }

[[ "$CHECK_MODE" == true ]] && check_installation
[[ "$UNINSTALL_MODE" == true ]] && uninstall_installation
```

#### 3.1.2 RC_FILE alias 제거 (macOS/Linux 호환)

`install.sh`는 RC_FILE에 정확히 3줄을 append한다 (L206-208). `sed -i`는 BSD/GNU 비호환이므로 **awk + mv 패턴**을 사용하고, 변경 전 타임스탬프 백업을 생성한다.

```bash
remove_rc_alias() {
  local rc="$RC_FILE"
  [[ -f "$rc" ]] || return 0
  grep -q "^source $CUBE_PATH/cube.sh$" "$rc" || return 0

  cp "$rc" "$rc.cube-uninstall.bak.$(date +%Y%m%d%H%M%S)"
  local tmp
  tmp=$(mktemp "${TMPDIR:-/tmp}/cube-rc.XXXXXX")
  awk -v cube="$CUBE_PATH" '
    /^source / && $2 == "$cube/cube.sh" { skip=1; if (prev_comment) lines[--n]=""; next }
    /^# Cube AI Agent Alias$/ { prev_comment=1; lines[n++]=$0; next }
    { prev_comment=0; lines[n++]=$0 }
    END { for (i=0; i<n; i++) print lines[i] }
  ' "$rc" > "$tmp" && mv "$tmp" "$rc"
}
```

#### 3.1.3 Claude `settings.json` statusLine 조건부 제거

`install.sh` L119-126의 검사 패턴을 재사용하되, 인자 전달은 `'$VAR'` 보간이 아닌 `sys.argv` 사용 (경로 안전).

```bash
json_strip_claude_statusline() {
  local settings="$1"
  [[ -f "$settings" ]] || return 0
  python3 - "$settings" <<'PY'
import sys, json
p = sys.argv[1]
try: c = json.load(open(p))
except Exception: sys.exit(2)
sl = c.get('statusLine', {})
if sl.get('type') == 'command' and 'cube-status-line.sh' in sl.get('command', ''):
    c.pop('statusLine', None)
    json.dump(c, open(p, 'w'), indent=2)
    print("removed")
else:
    print("preserved")
PY
}
```

Gemini `enablePermanentToolApproval`도 동일 패턴(Node heredoc)으로 제거 — `security.enablePermanentToolApproval` 키 삭제, `security` 객체가 비면 함께 삭제.

#### 3.1.4 `uninstall_installation()` 4단계 흐름

- **Enumerate**: `TARGET_AGENTS` 결정 (미지정이면 `(claude gemini opencode)` + `REMOVE_ALIAS=true`). `check_installation` 순서대로 순회하며 `PLAN_OPS` 배열에 `tag|path|expected` 형식으로 enqueue. `cube_owned_symlink` 실패 항목은 `noop` 태그.
- **Preview**: 빈 계획이면 `✨ Nothing to uninstall` 후 `exit 0`. 그 외 번호 매겨 출력.
- **Confirm**: `FORCE_MODE != true` && `[[ -t 0 ]]`이면 `read -p "Proceed? (y/N): "`. 비대화형은 안내 출력 후 진행.
- **Execute & Report**: 각 op 실행 직전 `cube_owned_symlink` 재검증(TOCTOU 방어). 카운터(`removed / skipped / failed`) 출력 후 `exit $failed`. `REMOVE_ALIAS=true`였으면 `source $RC_FILE` 안내.

**제거 순서**는 "중요도 역순": status-line → Claude statusLine JSON → Gemini policies → Gemini approval JSON → OpenCode plugins → Skills + `rmdir` → **RC_FILE alias (마지막)**. 중간 중단 시 본체(심볼릭)는 우선 정리되고 alias만 남음.

### 3.2 Files Affected

| Path                 | Change | Reuse                                                          | Why                                                                       |
| :------------------- | :----- | :------------------------------------------------------------- | :------------------------------------------------------------------------ |
| `scripts/install.sh` | MODIFY | `scripts/install.sh:check_installation` (L29-178, 순서 미러링) | L180-194 파서 교체 + 헬퍼 3개 + `uninstall_installation` 신규 (≈+250/-15) |
| `README.md`          | MODIFY | -                                                              | `## Usage` 섹션에 `--uninstall [agents...]`, `--force` 문서화             |
| `CLAUDE.md`          | MODIFY | -                                                              | `### Key Commands`에 uninstall 명령어 항목 추가                           |

### 3.3 Risks & Mitigations

- **Risk:** TOCTOU — Enumerate와 Execute 사이 심볼릭 변경 → **Mitigation:** Execute 직전 `cube_owned_symlink` 재검증, 실패 시 skipped 카운트.
- **Risk:** RC_FILE에 cube 외 텍스트가 같은 라인에 있음 → **Mitigation:** `^source $CUBE_PATH/cube.sh$` 정확 일치만 사용.
- **Risk:** `settings.json` 파싱 실패 → **Mitigation:** python3 exit 2로 graceful degradation, 전체 흐름은 진행.
- **Risk:** macOS BSD vs GNU `sed -i` 비호환 → **Mitigation:** `sed -i` 사용 금지, awk + mv로 통일.
- **Risk:** 잘못된 agent명(`--uninstall unknown`) → **Mitigation:** `install.sh` L407 패턴 미러링, `⚠️ Unknown agent` 후 skip.

### 3.4 Verification

```bash
# 설치 → 진단 → 제거 → 재진단 라운드트립
bash ./scripts/install.sh
bash ./scripts/install.sh --check          # 모든 항목 ✅ 기대
bash ./scripts/install.sh --uninstall --force
bash ./scripts/install.sh --check          # 모든 항목 ❌/⚠️ 기대
bash ./scripts/install.sh --uninstall      # "✨ Nothing to uninstall" (멱등)
bash ./scripts/install.sh --uninstall --check  # exit 2 (상호 배타)
```

**수동 시나리오**:

1. **사용자 소유 보존**: `~/.claude/cube-status-line.sh`를 일반 파일로 교체 → `--uninstall claude` 시 `SKIP (not ours)` 출력, 파일 보존.
2. **커스텀 statusLine 보존**: `~/.claude/settings.json`의 `statusLine.command`를 `echo hi`로 변경 → `preserved` 출력, 키 유지.
3. **백업 파일**: `~/.zshrc.cube-uninstall.bak.*` 생성 확인, `mv`로 원복 가능.

**Self-Contained Check**: 약한 모델 implementor가 본 plan만으로 구현 가능한가? → ✅ 헬퍼 3개 코드 + 4단계 흐름 자연어 + 파서 코드로 self-contained.

### 3.5 Acceptance Criteria

- [ ] `--uninstall`, `--force`, `--help` 플래그가 정상 인식되고 `--check`와 동시 지정 시 exit 2
- [ ] `cube_owned_symlink` 술어가 모든 `rm` 직전 호출되어 cube 소유 검증
- [ ] `uninstall_installation()`이 Enumerate/Preview/Confirm/Execute 4단계 준수
- [ ] RC_FILE에서 cube source 라인 + 주석 라인 함께 제거 + 타임스탬프 백업 생성
- [ ] Claude statusLine 키가 cube-status-line.sh 참조 시에만 제거 (사용자 커스텀 보존)
- [ ] Gemini policies / OpenCode plugins / agent skills 심볼릭이 cube 소유일 때만 제거
- [ ] 종료 시 `removed / skipped / failed` 카운터 출력
- [ ] 두 번 연속 실행 시 2회차는 `✨ Nothing to uninstall` 출력
- [ ] 비대화형 환경에서 `--force` 없이도 진행 (이미 `--uninstall`로 opt-in)
- [ ] README.md / CLAUDE.md 문서 업데이트 완료

## 4. Progress & Phases

- **Total:** 0/9 tasks
- **Done:** 0
- **Remaining:** 9

### Phase 1: 헬퍼 및 인자 파서

- [ ] Task 1.1: 인자 파서를 `case` 기반으로 확장 (`--uninstall`, `--force`, `--help`)
- [ ] Task 1.2: `cube_owned_symlink` + `remove_rc_alias` 헬퍼 작성
- [ ] Task 1.3: `json_strip_claude_statusline` (Python) + Gemini approval Node heredoc 작성

### Phase 2: 본체 4단계 흐름

- [ ] Task 2.1: `uninstall_installation()` Enumerate + Preview
- [ ] Task 2.2: Confirm 분기 (대화형/비대화형/--force)
- [ ] Task 2.3: Execute & Report (TOCTOU 재검증 + 카운터)

### Phase 3: 문서화 + 검증

- [ ] Task 3.1: README.md `## Usage` 섹션 추가
- [ ] Task 3.2: CLAUDE.md `### Key Commands` 추가
- [ ] Task 3.3: §3.4 Verification 자동/수동 시나리오 전부 실행

### Unplanned

(아직 없음)

## 5. Out of Scope

- **Gemini permanent tool approval 복원**: 원래 값으로 되돌리지 않고 단순 키 삭제. 사용자가 직접 관리.
- **자동 설정 파일 백업 (RC 제외)**: settings.json 등은 사용자가 직접 백업 책임.
- **다른 agent 지원**: claude/gemini/opencode 이외는 미지원.
- **자동 회복(`--uninstall` 실패 후 rollback)**: 카운터 출력만 제공.

## 6. Decisions

| #   | Date       | Decision                                              | Reason                                                     | Impact                              |
| :-- | :--------- | :---------------------------------------------------- | :--------------------------------------------------------- | :---------------------------------- |
| 1   | 2026-05-15 | `--force` 플래그 추가                                 | CI/CD 비대화형 환경 지원                                   | 파서 +1 옵션                        |
| 2   | 2026-05-15 | `--check`와 `--uninstall` 상호 배타                   | 동시 지정 시 의미 모호                                     | exit 2 즉시 거부                    |
| 3   | 2026-05-15 | `settings.json` 조건부 제거 (cube 소유 검증)          | 사용자 커스텀 statusLine 보존                              | python3 heredoc 추가                |
| 4   | 2026-05-15 | RC_FILE은 타임스탬프 백업 + awk + mv 패턴             | macOS/Linux 호환 + 복원 가능                               | `sed -i` 미사용                     |
| 5   | 2026-05-15 | `cube_owned_symlink` 술어로 모든 `rm` 가드            | TOCTOU 방어 + 사용자 파일 보존                             | 헬퍼 1개, 모든 단계 호출            |
| 6   | 2026-05-15 | 4단계 lifecycle (Enumerate/Preview/Confirm/Execute)   | `check_installation`과 미러링하여 유지보수성 확보          | `uninstall_installation()` 명확 분기 |
