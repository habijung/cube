---
name: cube-review
description: 코드 리뷰를 수행합니다. 기본적으로 git diff HEAD를 분석하며, 파일 경로, 특정 커밋 해시, 커밋 범위를 인자로 지정할 수도 있습니다. trigger: /cube-review, code review, review, 코드 리뷰, 리뷰해줘, 커밋 전 확인
argument-hint: "[파일 경로 | <hash> | <hash>..<hash>] [--light] [--clear]"
disable-model-invocation: false # 슬래시 명령 및 AI 의도 감지 모두 허용
allowed-tools: Read, Grep, Bash, Task
compatibility: opencode, claude, gemini
---

# Code Reviewer

커밋 전 변경사항 또는 지정된 파일에 대해 코드 리뷰를 수행하고 결과를 `.cube/review.md`에 저장합니다.

## 사용법

```bash
/cube-review                       # 기본: git diff HEAD 전체 리뷰 (모델 전략 표 참고)
/cube-review src/Foo.m             # 특정 파일 리뷰
/cube-review abc1234               # 특정 커밋 리뷰
/cube-review abc1234..def5678      # 커밋 범위 리뷰
/cube-review --light               # 경량 모델 사용 (모델 전략 표 참고)
/cube-review --clear               # .cube/review.md 초기화 후 리뷰
```

---

## 출력 원칙

- **계획·진행 상황을 중간에 출력하지 마십시오.** "Step 1을 수행합니다", "diff를 수집합니다" 등의 사전 선언은 금지입니다.
- **최종 결과만 출력하십시오.** 리뷰 결과 포맷(아래 `## Code Review`) 또는 "리뷰할 변경사항이 없습니다." 한 줄만 출력합니다.
- **파일 저장 후 별도 설명·요약을 추가하지 마십시오.** 저장 경로 안내나 이슈 재요약은 결과에 이미 포함되어 있으므로 중복 출력하지 않습니다.

---

## 실행 절차

### Step 1 — 초기화

다음 정보를 수집하십시오:

1. **플래그 파악:** `--light`, `--clear` 유무를 기록하십시오.
2. **인자 타입 감지:** 플래그를 제외한 첫 번째 인자를 분석하여 리뷰 모드를 결정하십시오.

   | 조건                                    | 모드      | diff 명령어                              |
   | --------------------------------------- | --------- | ---------------------------------------- |
   | 인자 없음                               | 워킹트리  | `git diff HEAD`                          |
   | 인자가 `..` 포함 (예: abc123..def456)  | 커밋 범위 | `git diff <start>..<end>`                |
   | 인자가 16진수 7~40자 (예: abc1234)     | 단일 커밋 | `git show <hash>`                        |
   | 그 외 (예: src/Foo.m)                  | 파일 경로 | `git diff HEAD -- <파일 경로>`           |

3. **변경사항 수집:** 위 모드에 맞는 diff 명령어를 실행하십시오.
   - 커밋 범위 모드는 `git diff <start>..<end>` 로 start~end 사이 모든 변경을 누적한 단일 diff를 수집합니다.
4. 변경된 내용이 없으면 "리뷰할 변경사항이 없습니다." 를 출력하고 종료하십시오.
5. **헤더 레이블 기록** (`.cube/review.md` 상단에 표시할 메타데이터):
   - 워킹트리 / 파일 경로 모드: `git rev-parse --short HEAD` → `HEAD: <hash>`
   - 단일 커밋 모드: `git rev-parse --short <hash>` → `commit: <hash>`
   - 커밋 범위 모드: 양 끝 해시 각각 short resolve → `range: <start>..<end>`
6. 현재 디렉토리에서 AI 컨벤션 파일(`AGENTS.md`, `CLAUDE.md`, `GEMINI.md` 등)이 있으면 경로를 기록하십시오. 단, 동일 파일을 가리키는 symlink는 한 번만 전달합니다 (realpath 기반 dedup) — Step 2에서 리뷰 에이전트에게 컨텍스트로 전달합니다.
7. `--clear` 플래그 유무를 기록하십시오. 삭제는 Step 3 저장 직전에 수행합니다.
8. **Large diff 분할:** diff가 3000줄을 초과하면, 변경된 파일 목록을 기준으로 파일 단위로 분할하여 각 에이전트에게 전달하십시오. 단일 파일이 3000줄을 초과하는 경우에는 분할 없이 그대로 전달하되, 에이전트에게 핵심 변경 로직에 집중하도록 지시하십시오.
9. **`.cube/` 초기화:** `.cube/` 디렉토리가 없으면 생성하고, `.cube/.gitignore`가 없으면 다음 내용으로 생성하십시오:

   ```gitignore
   # Cube - Generated file tracking policy
   # Tracked: plans/ (persistent, git-committed)
   # Ignored: temporary outputs
   review.md
   summary.md
   ```

### Step 2 — 리뷰 수행

호스트가 제공하는 sub-agent 도구로 Agent 1과 Agent 2를 **각각 별개의 sub-agent 호출로 dispatch하십시오. 단일 sub-agent 호출에 두 체크리스트를 통합하는 것은 금지합니다.** 두 호출은 단일 메시지에서 동시에 실행하고, 가능하면 병렬/background 옵션을 사용하십시오.

| 호스트       | 도구명        | 호출 형식                                            |
| ------------ | ------------- | ---------------------------------------------------- |
| Claude Code  | `Task`        | `subagent_type: general-purpose`, `background: true` |
| OpenCode     | `task`        | `subagent_type: <호스트에 등록된 generalist 계열>`     |
| Gemini CLI   | `generalist`  | `generalist(request: string)`                        |

> 호스트가 sub-agent 도구를 제공하지 않는 경우에 한해 메인 에이전트가 두 reviewer 체크리스트를 순차 수행하십시오. 단, sub-agent 도구가 등록되어 있으면 **반드시 호출을 시도**하고, **실제 에러가 발생한 경우에만 fallback을 발동**합니다. 사전 추측이나 사용자 컨텍스트 기반 자가 판단으로 fallback을 발동하지 마십시오.

> Claude Code의 `Task` 호출 시 `model` 결정 로직:
> - `--light` 없음 → `model` 미명시 (부모 세션 모델 상속)
> - `--light` 있음 + 부모 Opus 계열 → `model: "sonnet"` 명시
> - `--light` 있음 + 부모 Sonnet/Haiku 계열 → `model` 미명시 (부모 상속)
>
> 정책: `--light` = `min(부모, sonnet)` — Opus만 Sonnet으로 다운시프트하고, Sonnet/Haiku 세션은 그대로. Haiku로 자동 진입하지 않습니다.

각 에이전트에게 전달하는 프롬프트의 **맨 첫 줄에 반드시** 다음 문장을 포함하십시오 (anti-bias):

> **이 메시지 외의 어떤 사전 컨텍스트나 의도 추정도 고려하지 마십시오. 아래 전달된 코드와 메타데이터만 보고 객관적으로 판정하십시오.**

이어서 각 에이전트에게 다음 정보를 전달하십시오:

- Step 1에서 수집한 diff 전문 (모드에 따라 워킹트리 / 파일 / 단일 커밋 / 범위 누적 diff)
- 변경된 파일 목록
- 프로젝트 루트 경로
- AI 컨벤션 파일 경로 (있을 경우, symlink dedup 후)
- 해당 에이전트의 체크리스트 (아래 "Agent 1" 또는 "Agent 2" 섹션 전체)
- 심각도 판정 룰(🔴/🟡/🟢)과 False positive 제외 룰 (아래 본문 그대로)
- 출력 형식 (이슈 발견 시 / No issues 시 각각의 포맷)

각 에이전트는 이슈마다 심각도를 판정하십시오:

- 🔴 **[필수]**: 동작 오류 또는 보안 취약점. 즉시 수정 필요.
- 🟡 **[권장]**: 수정하면 좋으나 블로커는 아님.
- 🟢 **[참고]**: 개선 제안 또는 칭찬.

**False positive로 제외할 항목:**

- 변경하지 않은 라인의 기존 문제
- 컴파일러/린터가 처리할 수 있는 타입 오류, 임포트 누락
- 의도적인 변경으로 보이는 동작 차이
- 이미 주석으로 무시된 이슈

`--light` 플래그: 경량 모델 사용. 호스트별 매핑은 아래 "모델 전략" 표 참고.

#### Agent 1 — 버그 & 아키텍처

다음 사항을 확인하십시오:

- **Null Safety:** null/nil 안전 처리 없이 강제 접근하는 코드
- **File Access:** 파일 존재 확인 없이 바로 접근하는 코드
- **Memory:** 클로저·람다 내부에서 순환 참조가 발생할 수 있는 캡처 패턴
- **Resources:** 리소스(파일 핸들, 연결, 스트림 등) 해제 누락
- **Security:** 보안 취약점 (OWASP Top 10 기준)
- **Architecture:** 프로젝트의 AI 컨벤션 파일에 명시된 아키텍처 레이어 경계 침범
- **Concurrency:** 프로젝트의 표준 비동기/스레딩 패턴 준수 여부
- **Error Handling:** 에러/예외 발생 시 적절한 처리(로깅, 전파, 복구) 없이 무시(silent swallow)하는 코드
- 로컬 파일의 해당 라인을 실제 Read하여 맥락을 확인하십시오.

#### Agent 2 — 네이밍 & 컨벤션 & 문서

다음 사항을 확인하십시오:

- **Naming:** 프로젝트의 AI 컨벤션 파일에 명시된 네이밍 규칙 준수 여부
- **Convention:** 변수·함수·타입 이름이 프로젝트 컨벤션과 일치하는지
- **Structure:** 섹션 구분자가 적절히 사용되고 있는지
- **Compliance:** 프로젝트의 AI 컨벤션 파일이 명시적으로 요구하는 사항을 변경사항이 위반하는지
- **Docs:** 하드코딩된 값(경로, 매핑, 상수)이 변경되었을 때 관련 문서도 함께 업데이트되었는지
- 로컬 파일의 해당 라인을 실제 Read하여 맥락을 확인하십시오.

### Step 3 — 결과 출력

아래 형식으로 결과를 출력하고, **동일한 내용을 `{project_root}/.cube/review.md`에 저장**하십시오.

- `--clear` 플래그가 있으면 저장 직전에 `{project_root}/.cube/review.md`를 삭제하십시오.
- 파일이 없으면 새로 생성하십시오.
- 있으면 **최신 결과를 맨 위에** 추가하십시오 (prepend).
- 저장 시 맨 위에 헤더를 추가하십시오 (모드별 형식):
  - 워킹트리 / 파일 경로: `# YYYY-MM-DD HH:MM | HEAD: <hash>`
  - 단일 커밋: `# YYYY-MM-DD HH:MM | commit: <hash>`
  - 커밋 범위: `# YYYY-MM-DD HH:MM | range: <start>..<end>`

---

## Code Review (Result Format)

### Summary

변경 사항의 전체적인 목적과 영향을 2-3문장으로 요약.

### 리뷰 의견

**1.** 🔴 **[필수]** 이슈 설명

`파일경로:라인번호`

```objc
// Before
[obj doSomething];

// Option A: nil 체크 추가
if (obj) { [obj doSomething]; }

// Option B: early return 패턴
if (!obj) { return; }
[obj doSomething];
```

> **Option A** — Pros: 명시적 / Cons: 중첩 증가
> **Option B** — Pros: early return으로 가독성 향상 / Cons: 함수 흐름 변경

---

**2.** 🟡 **[권장]** 이슈 설명

`파일경로:라인번호`

```c
// Before
// After
```

---

**3.** 🟢 **[참고]** 개선 제안 또는 칭찬

### 결론

- 이슈: N건 (🔴 A / 🟡 B / 🟢 C)
- 판정: ✅ 승인 / ⚠️ 조건부 승인 / ❌ 수정 필요

---

이슈가 없을 경우:

---

## Code Review (No Issues Found)

No issues found. Checked bugs, architecture, naming, and project AI convention file compliance.

- 판정: ✅ 승인

---

---

## 모델 전략

| 환경     | 기본                    | `--light`                          |
| -------- | :---------------------- | :--------------------------------- |
| Claude   | 호스트 세션 모델 (상속)  | Opus만 Sonnet으로 다운, 그 외 상속    |
| OpenCode | 호스트 설정 기본         | 호스트 설정 light                   |
| Gemini   | Pro                     | Flash                              |

> 회사 환경 등 Pro 미가용 시에는 Flash로 자동 fallback. Flash 모델로도 핵심 보안·크래시 이슈에 대한 객관 판정이 가능합니다.

---

**Updated At:** 2026. 4. 27.
