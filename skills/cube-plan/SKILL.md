---
name: cube-plan
description: 구현 계획을 수립하고 .cube/plans/ 디렉토리에 저장합니다. trigger: /cube-plan, 계획 세워줘, plan
argument-hint: "[task-id] \"설명\" [--list] [--close task-id]"
disable-model-invocation: false
allowed-tools: Bash, Read, Grep
compatibility: opencode, claude, gemini
---

# Plan Creator

구현 계획을 수립하고 `.cube/plans/<task-id>/` 디렉토리에 파일로 저장합니다. Dev Agent가 별도 세션에서 계획을 로드하여 개발을 이어갈 수 있도록, 파일 시스템을 공유 매체로 사용하는 비동기 핸드오프 스킬입니다.

## 사용법

```
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
3. **충돌 처리:** `.cube/plans/<task-id>/`가 이미 존재하면 `-2`, `-3` 접미사를 자동 부여

### Step 3 — 프로젝트 컨텍스트 수집

다음 정보를 수집하십시오:

1. **Git 정보:** 현재 브랜치명, 최근 커밋 3개 (`git log -3 --oneline`)
2. **프로젝트 지침:** `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` 등 프로젝트 루트의 에이전트 설정 파일
3. **기술 스택 추론:** 위 파일에 명시되어 있으면 그대로 사용. 없으면 `package.json`, `Podfile`, `requirements.txt`, `go.mod`, `Cargo.toml` 등에서 추론. 모두 없으면 "Not detected" 표시
4. **관련 코드:** 사용자가 설명한 영역과 관련된 파일/디렉토리를 Grep/Read로 탐색

### Step 4 — 계획 수립

수집한 컨텍스트를 바탕으로 4개 파일의 내용을 작성하십시오:

1. **`plan.md`** — 구현 계획서 (Overview + Phase별 체크박스 + References)
2. **`context.md`** — 프로젝트 컨텍스트 스냅샷
3. **`progress.md`** — 진행 상황 추적
4. **`decisions.md`** — 의사결정 기록

각 파일의 템플릿은 아래 **File Templates** 섹션을 참조하십시오.

**사용자에게 계획 초안을 제시하고 승인을 받으십시오.** 승인 전까지 파일을 생성하지 마십시오.

### Step 5 — 파일 생성 및 등록

사용자 승인 후 다음을 수행하십시오:

1. **`.cube/` 초기화:** `.cube/` 디렉토리가 없으면 생성하고, `.cube/.gitignore`가 없으면 다음 내용으로 생성하십시오:
   ```
   # Cube - Generated file tracking policy
   # Tracked: plans/ (persistent, git-committed)
   # Ignored: temporary outputs
   review.md
   ```
2. `.cube/plans/<task-id>/` 디렉토리 생성
3. 4개 파일(`plan.md`, `context.md`, `progress.md`, `decisions.md`) 생성
4. `.cube/plans/index.md` 업데이트 (없으면 새로 생성)
5. `.cube/plans/`가 `.gitignore`에 포함되어 있으면 경고 출력
6. Git 커밋: `git add .cube/ && git commit -m "plan: Create <task-id>"`

### Step 6 — 계획 종료 (Close 모드 전용)

`--close <task-id>` 실행 시:

1. `.cube/plans/<task-id>/progress.md`를 읽어 미완료 항목 확인
2. **미완료 항목이 있으면** 경고 메시지를 출력하고 사용자 확인을 요청
3. 사용자 승인 후:
   - `.cube/plans/<task-id>/` 디렉토리 삭제
   - `.cube/plans/index.md`에서 해당 행 제거
   - 활성 계획이 0개가 되면 `.cube/plans/index.md`도 삭제
   - Git 커밋: `git add .cube/ && git commit -m "plan: Close <task-id>"`

---

## List 모드

`--list` 실행 시:

1. `.cube/plans/index.md`가 있으면 내용을 출력
2. 없거나 활성 계획이 0개이면 "활성 계획이 없습니다." 출력

---

## File Templates

### index.md

```markdown
# Active Plans

| Task ID   |  Status   | Branch   | Created    | Description |
| :-------- | :-------: | :------- | :--------- | :---------- |
| <task-id> | 🟢 Active | <branch> | YYYY-MM-DD | <설명>      |
```

### plan.md

```markdown
# Plan: <task-id>

## Overview

<구현 목표와 배경을 2-3 문단으로 서술>

## Phases

### Phase 1: <이름>

- [ ] Task 1.1: <설명>
- [ ] Task 1.2: <설명>

### Phase 2: <이름>

- [ ] Task 2.1: <설명>
- [ ] Task 2.2: <설명>

## References

- <관련 파일, 문서, URL 등>
```

### context.md

```markdown
# Context: <task-id>

## Project

- **Repository:** <git remote 또는 디렉토리명>
- **Branch:** <현재 브랜치>
- **Recent Commits:**
  - <최근 커밋 3개>

## Tech Stack

- **Languages:** <언어>
- **Frameworks:** <프레임워크>
- **Database:** <DB>

## Architecture

<AGENTS.md/CLAUDE.md에서 추출한 아키텍처 정보 또는 코드 탐색으로 파악한 구조>

## Conventions

<코딩 컨벤션, 네이밍 규칙 등>

## Key Commands

- **Build:** <빌드 명령어>
- **Test:** <테스트 명령어>
- **Lint:** <린트 명령어>

## Relevant Code

<계획과 관련된 주요 파일/함수 목록 및 간략한 설명>
```

### progress.md

```markdown
# Progress: <task-id>

## Summary

- **Total:** 0/N tasks
- **Done:** 0
- **Remaining:** N

## Phase 1: <이름>

- [ ] Task 1.1: <설명>
- [ ] Task 1.2: <설명>

## Phase 2: <이름>

- [ ] Task 2.1: <설명>
- [ ] Task 2.2: <설명>

### Unplanned

<계획에 없었으나 개발 중 추가된 작업>
```

### decisions.md

```markdown
# Decisions: <task-id>

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

**Updated At:** 2026. 4. 7.
