---
name: cube-plan
description: 구현 계획을 수립하고 .cube/plans/ 디렉토리에 저장합니다.
trigger:
  - /cube-plan
  - 계획 세워줘
  - plan
argument-hint: '[task-id] "설명" [--list] [--close task-id]'
disable-model-invocation: false
allowed-tools: Bash, Read, Grep
compatibility: opencode, claude, gemini
---

# Plan Creator

구현 계획을 수립하고 `.cube/plans/<task-id>.md` 파일로 저장합니다. Dev Agent가 별도 세션에서 계획을 로드하여 개발을 이어갈 수 있도록, 파일 시스템을 공유 매체로 사용하는 비동기 핸드오프 스킬입니다.

## 사용법

```bash
/cube-plan "로그인 화면 리팩토링"         # 새 계획 생성 (task-id 자동 생성)
/cube-plan auth-refactor "인증 리팩토링"  # task-id 명시
/cube-plan --list                         # 활성 계획 목록 조회
/cube-plan --close auth-refactor          # 계획 종료 및 삭제
```

---

## 실행 절차

### Step 1 — 인자 파싱 및 모드 결정

인자를 분석하여 실행 모드를 결정하십시오:

- `--list` → **List 모드**: 목록 출력 후 종료
- `--close <task-id>` → **Close 모드**: Step 6으로 이동
- 그 외 → **Create 모드**: Step 2부터 순차 진행

### Step 2 — Task ID 결정

Task ID를 결정하십시오:

1. **명시적 지정:** 첫 번째 인자가 따옴표 없는 문자열이고 두 번째 인자가 설명이면, 첫 번째 인자를 task-id로 사용
2. **자동 생성:** 설명 텍스트에서 핵심 키워드를 추출하여 `kebab-case`로 변환
   - 최대 30자, 영문 소문자 + 하이픈만 허용
   - 예: "로그인 화면 리팩토링" → `login-screen-refactor`
3. **충돌 처리:** `.cube/plans/<task-id>.md`가 이미 존재하면 `-2`, `-3` 접미사를 자동 부여

### Step 3 — 프로젝트 컨텍스트 수집

다음 정보를 수집하십시오:

1. **Git 정보:** 현재 브랜치명, 최근 커밋 3개 (`git log -3 --oneline`)
2. **프로젝트 지침:** `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` 등 프로젝트 루트의 에이전트 설정 파일
3. **기술 스택 추론:** 위 파일에 명시되어 있으면 그대로 사용. 없으면 `package.json`, `Podfile`, `requirements.txt`, `go.mod`, `Cargo.toml` 등에서 추론. 모두 없으면 "Not detected" 표시
4. **관련 코드:** 사용자가 설명한 영역과 관련된 파일/디렉토리를 Grep/Read로 탐색

### Step 4 — 계획 수립

수집한 컨텍스트를 바탕으로 **단일 계획 파일(`<task-id>.md`)**의 내용을 작성하십시오. 파일은 YAML frontmatter와 6개의 주요 섹션으로 구성됩니다.

**YAML frontmatter (4개 필드 모두 필수):**

- `task-id`: Step 2에서 결정한 task id
- `status`: 항상 `active`로 시작 (close 시 `done` 또는 `abandoned`로 전이)
- `branch`: 작업 브랜치 (Step 3에서 수집)
- `created`: 생성 날짜 (YYYY-MM-DD)

**섹션:**

1. **Context** — 프로젝트 컨텍스트 및 기술 스택 스냅샷
2. **Overview** — 구현 목표와 배경
3. **Implementation Strategy** — 설계 본문 (5개 sub-section)
   - 3.1 Approach — 핵심 접근법 + 다른 접근과의 트레이드오프
   - 3.2 Files Affected — 변경 대상 파일 표 (Path / Change / Why)
   - 3.3 Risks & Mitigations — 위험 요인과 완화 방안
   - 3.4 Verification — 구체적 명령어 또는 시나리오 + 기대 출력
   - 3.5 Acceptance Criteria — 완료 기준 체크박스 리스트
4. **Progress & Phases** — 구현 단계별 체크박스 리스트
5. **Out of Scope** — 의도적 제외 항목과 그 사유
6. **Decisions** — 의사결정 기록 테이블

단일 파일의 템플릿은 아래 **File Templates** 섹션을 참조하십시오.

**Strategy 작성 원칙:**

- **Approach**: **핵심 구현 단위(헬퍼 함수 · 주요 알고리즘 · 파싱 로직 등)마다 코드 스니펫 1개씩** 포함할 것 (bash/python/typescript 등; 보통 3개 이상, 단순 task는 1개로 충분). "1개 이상"이라는 표현에 만족하지 말고 task 복잡도에 비례하여 scale. 약한 모델(Haiku/Flash 등)이 plan만 보고 추가 질문 없이 구현할 수 있도록 self-contained하게 작성. 구현 단위가 4개 이상이거나 헬퍼/유틸이 다수라면 **sub-section(3.1.1, 3.1.2 …)으로 분할 권장**하며, 다른 접근과의 트레이드오프가 의사결정에 영향을 주는 경우 **비교표 포함 권장**.
- **Files Affected**: 단일 파일이라도 표로 명시 (Path / Change / Reuse / Why). 라인 번호는 알려진 경우 포함. Reuse 컬럼에는 재사용할 기존 함수/패턴을 `path/file.ext:function_name` 형식으로 명시(없으면 `-`).
- **Verification**: "테스트 작성"같은 추상 표현 금지. 실제 실행할 명령어 또는 사람이 검증할 시나리오를 적을 것. **Self-Contained Check**: 작성 완료 후 "약한 모델(Haiku/Flash 등)이 본 plan만 보고 추가 질문 없이 구현 가능한가?"를 self-review하여 부족한 부분(코드 스니펫 누락, 모호한 파일 경로, 빠진 검증 시나리오 등)을 보강할 것.
- **Acceptance Criteria**: 객관적으로 ✅/❌ 판정 가능해야 함. 모호한 기준(e.g. "코드 품질 향상")은 거부.

**사용자에게 계획 초안을 제시하고 승인을 받으십시오.** 승인 전까지 파일을 생성하지 마십시오.

### Step 5 — 파일 생성 및 등록

사용자 승인 후 다음을 수행하십시오:

1. **`.cube/` 초기화:** `.cube/` 디렉토리가 없으면 생성하고, `.cube/.gitignore`가 없으면 다음 내용으로 생성하십시오:

   ```gitignore
   # Cube - Generated file tracking policy
   # Tracked: plans/ (persistent, git-committed)
   # Ignored: temporary outputs
   review.md
   ```

2. `.cube/plans/` 디렉토리가 없으면 생성 (이전처럼 `<task-id>` 하위 디렉토리는 만들지 않음)
3. `.cube/plans/<task-id>.md` 파일 생성
4. `.cube/plans/index.md` 업데이트 (없으면 새로 생성)
5. `.cube/plans/`가 `.gitignore`에 포함되어 있으면 경고 출력
6. Git 커밋: `git add .cube/ && git commit -m "plan: Create <task-id>"`

### Step 6 — 계획 종료 (Close 모드 전용)

`--close <task-id>` 실행 시:

1. `.cube/plans/<task-id>.md`를 읽어 다음 두 가지를 확인하십시오:
   - `## 4. Progress & Phases` 내 미완료 체크박스
   - `### 3.5 Acceptance Criteria` 내 미달 항목
2. **미완료/미달 항목이 있으면** 어느 절의 어느 항목이 미완료인지 명시하여 경고를 출력하고 사용자 확인을 요청하십시오. 사용자가 `status: abandoned`로 종료하기를 원하면 진행, 그 외에는 작업을 중단하십시오.
3. 사용자 승인 후 다음 절차를 결정적으로 수행하십시오:
   - **문서 정제 (Refine):** 아래 **File Templates** 절의 **Closeout 템플릿**대로 새 문서를 작성. `<!-- required: ... -->` 주석은 **제거하지 마십시오**. frontmatter는 4→6 필드 전이 (`status`를 `done` 또는 `abandoned`로 변경, `closed: YYYY-MM-DD`와 `final-commit: <단축 hash>` 추가). 5개 본문 섹션 각각의 데이터 소스는 템플릿 주석 참조.
   - **아카이브 보관 (Archive):** `docs/plans/<task-id>.md`에 저장 (디렉토리 없으면 생성, 경로는 항상 고정).
   - **임시 파일 정리 (Cleanup):** `.cube/plans/<task-id>.md` 삭제 + `.cube/plans/index.md`에서 해당 행 제거 (활성 0개면 파일 자체 삭제).
   - Git 커밋: `git add docs/plans/ .cube/ && git commit -m "plan: Close and archive <task-id>"`

---

## List 모드

`--list` 실행 시:

1. `.cube/plans/index.md`가 있으면 내용을 출력
2. 없거나 활성 계획이 0개이면 "활성 계획이 없습니다." 출력

---

## File Templates

### index.md

````markdown
# Active Plans

| Task ID | Status | Branch | Created | Description |

```markdown
| :-------- | :-------: | :------- | :--------- | :---------- |
| <task-id> | 🟢 Active | <branch> | YYYY-MM-DD | <설명> |
```
````

### `<task-id>.md` (단일 계획 파일)

활성 plan 문서. **YAML frontmatter 4개 필드는 모두 필수**이며, close 시 `status` 변경과 `closed`/`final-commit` 필드 추가로 closeout 문서로 전이됩니다.

```markdown
---
task-id: <task-id>
status: active
branch: <branch>
created: YYYY-MM-DD
---

# Plan: <task-id> — <한 줄 설명>

## 1. Context

- **Repository:** <git remote 또는 디렉토리명>
- **Branch:** <현재 브랜치>
- **Tech Stack:** <언어, 프레임워크, DB 등>
- **Architecture & Conventions:** <주요 아키텍처 및 코딩 규칙>
- **Key Commands:** Build: `<명령어>`, Test: `<명령어>`
- **Relevant Code:** <기존 코드 이해에 필요한 파일/디렉토리 포인터 (읽기용, §3.2 Files Affected와 별개)>
- **Recent Commits:**
  - <최근 커밋 3개>

## 2. Overview

<구현 목표와 배경을 2-3 문단으로 서술. 왜 이 작업이 필요한지, 이전 상태와 달라질 결과>

- **References:** <관련 파일, 문서, URL 등>

## 3. Implementation Strategy

### 3.1 Approach

<핵심 접근법 1-2 문단. 다른 접근과의 트레이드오프 1-2 줄 포함>

### 3.2 Files Affected

| Path   | Change                | Reuse                       | Why         |
| :----- | :-------------------- | :-------------------------- | :---------- |
| <path> | NEW / MODIFY / DELETE | <`path:func` 형식 또는 `-`> | <간단 사유> |

### 3.3 Risks & Mitigations

- **Risk:** <리스크> → **Mitigation:** <완화 방안>

### 3.4 Verification

- <검증 단계 1: 구체적 명령어 또는 시나리오 + 기대 출력>
- <검증 단계 2>

### 3.5 Acceptance Criteria

- [ ] <완료 기준 1>
- [ ] <완료 기준 2>

## 4. Progress & Phases

- **Total:** 0/N tasks
- **Done:** 0
- **Remaining:** N

### Phase 1: <이름>

- [ ] Task 1.1: <설명>
- [ ] Task 1.2: <설명>

### Phase 2: <이름>

- [ ] Task 2.1: <설명>
- [ ] Task 2.2: <설명>

### Unplanned

<계획에 없었으나 개발 중 추가된 작업>

## 5. Out of Scope

- **<제외 항목 1>:** <왜 의도적으로 제외했는지 + 트레이드오프>
- **<제외 항목 2>:** <사유>

## 6. Decisions

| #   | Date       | Decision    | Reason | Impact |
| :-- | :--------- | :---------- | :----- | :----- |
| 1   | YYYY-MM-DD | <결정 사항> | <사유> | <영향> |
```

### `docs/plans/<task-id>.md` (Closeout 템플릿)

`--close` 실행 시 생성되는 영구 아카이브 문서. **YAML frontmatter 6개 필드와 `<!-- required: ... -->` 주석은 모두 보존하십시오.**

```markdown
---
task-id: <task-id>
status: done
branch: <branch>
created: YYYY-MM-DD
closed: YYYY-MM-DD
final-commit: <hash>
---

# Plan Closeout: <task-id> — <한 줄 설명>

## 1. Outcome

<!-- required: 1-paragraph summary, branch, final-commit -->

<달성한 결과를 1-2 문단으로 서술>

- **Result:** <한 줄 요약>
- **Branch:** <branch>
- **Final Commit:** `<hash>`

## 2. Changes Made

<!-- required: file list with commit refs (or commit-by-commit summary) -->

| File   | Change      | Commit   |
| :----- | :---------- | :------- |
| <path> | <변경 요약> | `<hash>` |

## 3. Decisions

<!-- preserved from plan §6 + any closeout-time additions -->

| #   | Date | Decision | Reason | Impact |
| :-- | :--- | :------- | :----- | :----- |

## 4. Known Issues & Follow-ups

<!-- limitations, deferred items, recommended follow-up plans -->

- **Limitation:** <남은 한계 또는 미달 항목>
- **Follow-up:** <후속 작업 제안 또는 추천 plan id>

## 5. Verification Results

<!-- required: each Acceptance Criterion marked ✅/❌ with verification method -->

- ✅ <Acceptance criterion (plan §3.5에서 가져옴)> — <검증 방법/결과>
- ❌ <달성 못한 AC> — <사유 + close 결정 근거>
```

> **Note:** `status: abandoned`(미완료 종료) 케이스도 동일 템플릿을 사용합니다. frontmatter `status` 값만 변경하고, §4·§5에 미달 사유와 잔여 작업을 명시하십시오.
>
> **Examples:** 활성 plan 형식은 `examples/cube-plan.md`, closeout 형식은 `examples/cube-plan-dev.md` 참조 (skill 디렉토리 기준 상대경로, 동일 task-id 쌍).

---

## Guidelines

- **Approval Gate:** Step 4에서 계획 초안을 반드시 사용자에게 제시하고, 명시적 승인 후에만 파일을 생성하십시오.
- **No Push Policy:** `git push`는 절대 실행하지 마십시오.
- **Accept Mode Only:** 이 스킬은 에이전트의 built-in plan mode를 사용하지 않습니다. 항상 accept/normal mode에서 실행하십시오.
- **Git Tracking:** `.cube/plans/` 디렉토리는 git에 포함됩니다. `.gitignore`에 추가하지 마십시오.
- **Commit Convention:** 커밋 메시지는 `plan:` prefix를 사용하며, prefix 이후 첫 글자는 대문자로 시작합니다.

---

**Updated At:** 2026. 5. 15.
