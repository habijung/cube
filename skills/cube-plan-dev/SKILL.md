---
name: cube-plan-dev
description: 기존 계획을 로드하여 개발을 이어갑니다. trigger: /cube-plan-dev, 계획 이어가기, 이어서 개발, start development
argument-hint: "[task-id]"
disable-model-invocation: false
allowed-tools: Bash, Read, Write, Grep, Task
compatibility: opencode, claude, gemini
---

# Plan Developer

`.cube/plans/<task-id>/`에 저장된 계획을 로드하여 개발을 수행합니다. Plan Agent가 수립한 계획을 Dev Agent가 별도 세션에서 이어받아 구현하는 비동기 핸드오프 스킬입니다.

## 사용법

```
/cube-plan-dev                  # 활성 계획 자동 선택 (1개일 때)
/cube-plan-dev auth-refactor    # task-id 명시
```

---

## 실행 절차

### Step 1 — Task 선택

활성 계획을 선택하십시오:

1. **task-id 인자가 있으면:** `.cube/plans/<task-id>/` 존재 여부를 확인
2. **인자가 없으면:**
   - `.cube/plans/index.md`를 읽어 활성 계획 목록 확인
   - **1개:** 자동 선택
   - **2개 이상:** 목록을 제시하고 사용자에게 선택 요청
   - **0개:** "활성 계획이 없습니다. `/cube-plan`으로 새 계획을 생성하세요." 출력 후 종료


### Step 2 — 컨텍스트 로드

선택된 계획의 4개 파일을 모두 읽으십시오:

1. `plan.md` — 전체 계획 구조 파악
2. `context.md` — 프로젝트 컨텍스트 및 기술 스택 확인
3. `progress.md` — 현재 진행 상황 확인
4. `decisions.md` — 이전 의사결정 이력 확인

### Step 3 — 진행 상황 요약

사용자에게 다음을 보고하십시오:

- **Task:** `<task-id>` — `<설명>`
- **Progress:** Done M/N tasks
- **Current Phase:** `<현재 진행 중인 Phase>`
- **Next Task:** `<다음으로 수행할 미완료 체크박스>`
- **Key Decisions:** 최근 decisions.md 항목 (있을 경우)

사용자에게 개발을 시작할지 확인하십시오.

### Step 4 — 개발 수행

사용자 승인 후, `progress.md`의 체크박스를 기준으로 순차적으로 개발을 수행하십시오.

**진행 상황 갱신 규칙:**

1. **체크박스 업데이트:** 각 작업 완료 시 `progress.md`의 해당 체크박스를 `[x]`로 변경하고 Summary 카운트를 갱신
2. **단건 체크:** 체크박스는 완료 시 하나씩 체크 (벌크 체크 금지)
3. **체크 해제 금지:** 이미 체크된 항목의 해제가 필요한 경우, 반드시 `decisions.md`에 사유를 기록한 후 해제
4. **계획 외 작업:** 계획에 없었으나 개발 중 필요해진 작업은 `progress.md`의 `### Unplanned` 섹션에 추가
5. **의사결정 기록:** 계획과 다른 방향으로 진행하거나 중요한 결정을 내릴 때마다 `decisions.md`에 기록

### Step 5 — 진행 상황 커밋

적절한 시점에 진행 상황을 커밋하십시오:

- **커밋 시점:** Phase 단위, 또는 의미 있는 작업 단위 완료 시
- **커밋 메시지:** `plan: Update <task-id> progress`
- **커밋 범위:** `.cube/plans/<task-id>/` 내 파일만 포함 (코드 변경은 별도 커밋)

> **주의:** 코드 변경 커밋과 plan 진행 상황 커밋은 분리하십시오. 코드 커밋은 `cube-commit` 스킬 또는 프로젝트 컨벤션을 따르십시오.

---

## Guidelines

- **Read Before Act:** 개발을 시작하기 전에 반드시 4개 파일을 모두 읽고 컨텍스트를 파악하십시오.
- **No Push Policy:** `git push`는 절대 실행하지 마십시오.
- **Accept Mode Only:** 이 스킬은 에이전트의 built-in plan mode를 사용하지 않습니다. 항상 accept/normal mode에서 실행하십시오.
- **Plan Respect:** 계획을 임의로 변경하지 마십시오. 변경이 필요하면 반드시 `decisions.md`에 기록하고 사용자에게 보고하십시오.
- **Commit Convention:** plan 관련 커밋 메시지는 `plan:` prefix를 사용하며, prefix 이후 첫 글자는 대문자로 시작합니다.

---

**Updated At:** 2026. 4. 7.
