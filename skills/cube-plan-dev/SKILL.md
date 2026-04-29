---
name: cube-plan-dev
description: 기존 계획을 로드하여 개발을 이어갑니다. trigger: /cube-plan-dev, 계획 이어가기, 이어서 개발, start development
argument-hint: "[task-id]"
disable-model-invocation: false
allowed-tools: Bash, Read, Write, Grep, Task
compatibility: opencode, claude, gemini
---

# Plan Developer

`.cube/plans/<task-id>.md`에 저장된 단일 계획 파일을 로드하여 개발을 수행합니다. Plan Agent가 수립한 계획을 Dev Agent가 별도 세션에서 이어받아 구현하고 최종 완료 처리까지 수행하는 비동기 핸드오프 스킬입니다.

## 사용법

```bash
/cube-plan-dev                  # 활성 계획 자동 선택 (1개일 때)
/cube-plan-dev auth-refactor    # task-id 명시
```

---

## 실행 절차

### Step 1 — Task 선택

활성 계획을 선택하십시오:

1. **task-id 인자가 있으면:** `.cube/plans/<task-id>.md` 존재 여부를 확인
2. **인자가 없으면:**
   - `.cube/plans/index.md`를 읽어 활성 계획 목록 확인
   - **1개:** 자동 선택
   - **2개 이상:** 목록을 제시하고 사용자에게 선택 요청
   - **0개:** "활성 계획이 없습니다. `/cube-plan`으로 새 계획을 생성하세요." 출력 후 종료

### Step 2 — 컨텍스트 로드

선택된 계획의 파일(`.cube/plans/<task-id>.md`) 전체를 읽어 다음 정보를 파악하십시오:

1. `1. Context` — 프로젝트 컨텍스트 및 기술 스택 확인
2. `2. Overview` — 전체 목표 파악
3. `3. Implementation Strategy` — 설계 본문 (필독)
   - `3.1 Approach` — 구현 시 따라야 할 핵심 접근법
   - `3.2 Files Affected` — **이 표에 명시된 파일 외 수정 시 사용자 확인 필수**
   - `3.3 Risks & Mitigations` — 구현 중 주의할 위험 요인
   - `3.4 Verification` — 완료 후 수행할 검증 단계
   - `3.5 Acceptance Criteria` — `[x]` 전이 가능한 객관적 완료 기준
4. `4. Progress & Phases` — 현재 진행 상황 파악
5. `5. Out of Scope` — **명시된 항목은 절대 손대지 말 것**
6. `6. Decisions` — 이전 의사결정 이력 확인

### Step 3 — 진행 상황 요약

사용자에게 다음을 보고하십시오:

- **Task:** `<task-id>` — `<설명>`
- **Progress:** Done M/N tasks
- **Acceptance Criteria:** Met X/Y
- **Current Phase:** `<현재 진행 중인 Phase>`
- **Next Task:** `<다음으로 수행할 미완료 체크박스>`
- **Key Decisions:** 최근 §6 Decisions 항목 (있을 경우)

사용자에게 개발을 시작할지 확인하십시오.

### Step 4 — 개발 수행

사용자 승인 후, `4. Progress & Phases`의 체크박스를 기준으로 순차적으로 개발을 수행하십시오.

**개발 원칙:**

- **§3.1 Approach 준수:** 명시된 접근법을 따르되, 다른 방향으로 진행해야 한다면 `6. Decisions`에 사유 기록 후 사용자에게 보고
- **§3.2 Files Affected 외 파일 수정 금지:** 표에 없는 파일을 수정해야 한다면 작업 전 사용자에게 확인 요청 후 표에 행 추가
- **§5 Out of Scope 항목 절대 금지:** 의도적으로 제외된 항목은 손대지 말 것

**진행 상황 갱신 규칙:**

1. **체크박스 업데이트:** 각 작업 완료 시 `.cube/plans/<task-id>.md` 내의 해당 체크박스를 `[x]`로 변경하고 상단의 Summary 카운트(Done/Remaining)를 갱신
2. **단건 체크:** 체크박스는 완료 시 하나씩 체크 (벌크 체크 금지)
3. **체크 해제 금지:** 이미 체크된 항목의 해제가 필요한 경우, 반드시 `6. Decisions`에 사유를 기록한 후 해제
4. **계획 외 작업:** 계획에 없었으나 개발 중 필요해진 작업은 `### Unplanned` 섹션에 추가
5. **의사결정 기록:** 계획과 다른 방향으로 진행하거나 중요한 결정을 내릴 때마다 `6. Decisions`에 기록
6. **AC 갱신:** §3.5 Acceptance Criteria 항목이 충족되면 해당 체크박스를 `[x]`로 갱신 (Phase Task 체크박스와 별도로 관리)

### Step 5 — 진행 상황 커밋

적절한 시점에 진행 상황을 커밋하십시오:

- **커밋 시점:** Phase 단위, 또는 의미 있는 작업 단위 완료 시
- **커밋 메시지:** `plan: Update <task-id> progress`
- **커밋 범위:** `.cube/plans/<task-id>.md` 파일만 포함 (코드 변경은 별도 커밋)

> **주의:** 코드 변경 커밋과 plan 진행 상황 커밋은 분리하십시오. 코드 커밋은 `cube-commit` 스킬 또는 프로젝트 컨벤션을 따르십시오.

### Step 6 — 계획 완료 및 종료 (Completion)

다음 **두 가지 조건이 모두 충족**되었을 때 종료 절차를 진행하십시오:

- `4. Progress & Phases`의 모든 체크박스가 `[x]`
- `3.5 Acceptance Criteria`의 모든 체크박스가 `[x]`

조건 충족 시 다음 절차를 수행하십시오:

1. `.cube/plans/index.md` 파일을 읽고, 해당 `<task-id>` 행의 `Status` 컬럼을 `Complete`로 즉시 업데이트합니다.
2. 사용자에게 개발 완료를 보고하십시오 (Phase 완료 + AC 충족 양쪽 명시).
3. 플랜을 공식적으로 닫고 최종 문서 정리를 위해, **`/cube-plan --close <task-id>` 명령어를 실행**하거나 사용자가 직접 입력하도록 안내하십시오.

> **AC 미달 상태로 종료해야 하는 경우** (예: 외부 의존성으로 인한 블로커): `6. Decisions`에 `status: abandoned` 결정 사유를 기록한 후, 사용자 승인을 받아 `--close`를 진행하십시오. closeout 문서의 `frontmatter status`는 `abandoned`로 설정됩니다.

---

## Guidelines

- **Read Before Act:** 개발을 시작하기 전에 반드시 계획 파일을 모두 읽고 컨텍스트 파악을 진행하십시오.
- **No Push Policy:** `git push`는 절대 실행하지 마십시오.
- **Accept Mode Only:** 이 스킬은 에이전트의 built-in plan mode를 사용하지 않습니다. 항상 accept/normal mode에서 실행하십시오.
- **Plan Respect:** 계획을 임의로 변경하지 마십시오. 변경이 필요하면 반드시 `6. Decisions` 섹션에 기록하고 사용자에게 보고하십시오.
- **Commit Convention:** plan 관련 커밋 메시지는 `plan:` prefix를 사용하며, prefix 이후 첫 글자는 대문자로 시작합니다.

---

**Updated At:** 2026. 4. 29.
