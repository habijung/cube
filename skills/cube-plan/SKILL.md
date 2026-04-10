---
name: cube-plan
description: 구현 계획을 수립하고 .cube/plans/ 디렉토리에 저장합니다. trigger: /cube-plan, 계획 세워줘, plan
argument-hint: "[task-id] \"설명\" [--list] [--close task-id]"
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

수집한 컨텍스트를 바탕으로 **단일 계획 파일(`<task-id>.md`)**의 내용을 작성하십시오. 파일은 4개의 주요 섹션으로 구성됩니다:

1. **Context** — 프로젝트 컨텍스트 및 기술 스택 스냅샷
2. **Overview** — 구현 목표와 배경
3. **Progress & Phases** — 구현 단계별 체크박스 리스트
4. **Decisions** — 의사결정 기록 테이블

단일 파일의 템플릿은 아래 **File Templates** 섹션을 참조하십시오.

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

1. `.cube/plans/<task-id>.md`를 읽어 `## 3. Progress & Phases` 내 미완료 항목 확인
2. **미완료 항목이 있으면** 경고 메시지를 출력하고 사용자 확인을 요청
3. 사용자 승인 후 다음의 문서 정리(Cleanup & Archive)를 수행하십시오:
   - **문서 정제 (Refine):** `.cube/plans/<task-id>.md` 내용 중 불필요한 과정(체크리스트 등)을 제외하고, 다음 항목을 포함하여 공식 문서 형태로 요약합니다:
     - **Overview:** 작업 개요 및 최종 결과
     - **Technical Details:** 주요 기술적 시도 및 해결 방안 (`Decisions` 기반)
     - **Known Issues:** 한계점, 남은 버그 또는 추후 과제
   - **아카이브 보관 (Archive):** 정제된 문서를 영구 보관용 디렉토리(예: `docs/tasks/<task-id>.md` 또는 `CHANGELOG.md` 등 프로젝트 상황에 맞게)에 저장합니다.
   - **임시 파일 정리 (Cleanup):** 
     - `.cube/plans/<task-id>.md` 파일 삭제
     - `.cube/plans/index.md`에서 해당 행 제거 (활성 계획이 0개가 되면 파일 자체 삭제)
   - Git 커밋: `git add docs/ .cube/ && git commit -m "plan: Close and archive <task-id>"`

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

```markdown
# Plan: <task-id>

## 1. Context

- **Repository:** <git remote 또는 디렉토리명>
- **Branch:** <현재 브랜치>
- **Tech Stack:** <언어, 프레임워크, DB 등>
- **Architecture & Conventions:** <주요 아키텍처 및 코딩 규칙>
- **Key Commands:** Build: `<명령어>`, Test: `<명령어>`
- **Relevant Code:** <주요 관련 파일 목록>
- **Recent Commits:**
  - <최근 커밋 3개>

## 2. Overview

<구현 목표와 배경을 2-3 문단으로 서술>
- **References:** <관련 파일, 문서, URL 등>

## 3. Progress & Phases

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

## 4. Decisions

| #   | Date       | Decision    | Reason | Impact |
| :-- | :--------- | :---------- | :----- | :----- |
| 1   | YYYY-MM-DD | <결정 사항> | <사유> | <영향> |
```

---

## Guidelines

- **Approval Gate:** Step 4에서 계획 초안을 반드시 사용자에게 제시하고, 명시적 승인 후에만 파일을 생성하십시오.
- **No Push Policy:** `git push`는 절대 실행하지 마십시오.
- **Accept Mode Only:** 이 스킬은 에이전트의 built-in plan mode를 사용하지 않습니다. 항상 accept/normal mode에서 실행하십시오.
- **Git Tracking:** `.cube/plans/` 디렉토리는 git에 포함됩니다. `.gitignore`에 추가하지 마십시오.
- **Commit Convention:** 커밋 메시지는 `plan:` prefix를 사용하며, prefix 이후 첫 글자는 대문자로 시작합니다.

---

**Updated At:** 2026. 4. 10.
