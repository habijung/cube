---
name: cube-review
description: >-
  코드 리뷰를 수행합니다. 기본적으로 git diff HEAD를 분석하며,
  파일 경로, 특정 커밋 해시, 커밋 범위를 인자로 지정할 수도 있습니다.
trigger:
  - /cube-review
  - code review
  - review
  - 코드 리뷰
  - 리뷰해줘
  - 커밋 전 확인
argument-hint: "[파일 경로 | <hash> | <hash>..<hash>] [--heavy] [--save] [--clear]"
disable-model-invocation: false # 슬래시 명령 및 AI 의도 감지 모두 허용
allowed-tools: Read, Grep, Bash, Task
compatibility: opencode, claude, gemini, pi
---

# Code Reviewer

커밋 전 변경사항 또는 지정된 파일에 대해 코드 리뷰를 수행합니다. 기본으로는 채팅에 짧은 결과만 출력하며, `--save` 또는 `--clear`가 지정된 경우에만 상세 결과를 `.cube/review.md`에 저장합니다.

## 사용법

```bash
/cube-review                       # 기본: git diff HEAD 전체 리뷰 (Sonnet sub-agents)
/cube-review src/Foo.m             # 특정 파일 리뷰
/cube-review abc1234               # 특정 커밋 리뷰
/cube-review abc1234..def5678      # 커밋 범위 리뷰
/cube-review --heavy               # Opus sub-agents 사용 (미묘한 버그 예상 시)
/cube-review --save                # 상세 결과를 .cube/review.md 맨 위에 추가
/cube-review --clear               # 기존 기록을 이번 상세 결과로 교체
```

---

## 출력 원칙

- **계획·진행 상황을 중간에 출력하지 마십시오.** "Step 1을 수행합니다", "diff를 수집합니다" 등의 사전 선언은 금지입니다.
- **짧은 최종 결과만 출력하십시오.** 리뷰 완료 여부와 판정, 남은 필수 지적과 사용자가 판단할 사항만 알리세요. 필수 지적이 있으면 파일·라인과 해당 지적의 근거를 짧게 포함하세요. 리뷰가 완료되지 않았으면 사유를 알리고 통과로 표시하지 마세요.
- **상세 리뷰는 채팅에 다시 작성하지 마십시오.** 저장을 요청한 경우에만 저장 경로 또는 저장 실패를 최종 결과에 포함하세요.

---

## 실행 절차

### Step 1 — 초기화

다음 정보를 수집하십시오:

1. **플래그 파악:** `--heavy`, `--save`, `--clear` 유무를 기록하십시오. `--clear`는 저장을 포함하며, `--save`와 함께 지정하면 `--clear` 동작을 적용합니다.
2. **인자 타입 감지:** 플래그를 제외한 첫 번째 인자를 분석하여 리뷰 모드를 결정하십시오.

   | 조건 (위에서부터 첫 일치)             | 모드      | diff 명령어                                                            |
   | :------------------------------------ | :-------- | :--------------------------------------------------------------------- |
   | 인자 없음                             | 워킹트리  | `git diff --no-relative HEAD`                                          |
   | 인자가 `./` 또는 `../`로 시작          | 파일 경로 | `git diff --no-relative HEAD -- ":(literal)$path"`                      |
   | 인자가 `..` 포함 (예: abc123..def456) | 커밋 범위 | `git diff --no-relative <검증된 범위>`                                 |
   | 인자가 16진수 7~40자 (예: abc1234)     | 단일 커밋 | `git -c log.showSignature=false show --no-relative --format= <commit>` |
   | 그 외 (예: src/Foo.m)                 | 파일 경로 | `git diff --no-relative HEAD -- ":(literal)$path"`                      |

3. **변경사항 수집:** 위 모드에 맞는 명령어를 호출한 디렉터리에서 실행하십시오. 파일 경로 모드의 사용자 입력은 호출 위치 기준으로, `:(literal)`을 붙여 하나의 Git 인자로 전달하세요. 모든 모드에서 Git 명령의 경로 인자 끝에 저장소 루트 기준 제외 경로 `':(top,exclude,literal).cube/review.md'`를 붙이세요. 경로 구분자인 `--`가 없다면 제외 경로 앞에 추가하세요.
   - diff를 실행하는 Git 명령에만 `GIT_LITERAL_PATHSPECS=0 GIT_GLOB_PATHSPECS=0 GIT_NOGLOB_PATHSPECS=0 GIT_ICASE_PATHSPECS=0`을 지정하세요. 상속된 설정 때문에 제외 규칙이 비활성화되거나 충돌하면 안 됩니다.
   - 커밋 범위는 `...`를 먼저 찾고, 없으면 `..`로 양 끝을 나누세요. 생략된 끝은 `HEAD`로 해석하세요. 단일 커밋의 해시와 범위 양 끝은 각각 `git rev-parse --verify --end-of-options "${ref}^{commit}"`으로 검증하세요. 범위는 검증된 커밋 ID를 입력과 같은 구분자로 다시 연결해 하나의 인자로 전달하세요. 커밋으로 해석되지 않거나 Git 명령이 실패하면 오류를 보고하고 중단하세요. 실패를 변경 없음으로 처리하지 마세요.
4. 제외 적용 후 검토할 파일 변경이 없으면 "리뷰할 변경사항이 없습니다."를 출력하고 종료하십시오. 저장소 루트의 `.cube/review.md`만 지정한 경우도 여기에 해당합니다.
5. **저장 요청이 있을 때만 헤더 레이블 기록** (`.cube/review.md` 상단에 표시할 메타데이터):
   - 워킹트리 / 파일 경로 모드: `git rev-parse --short HEAD` → `HEAD: <hash>`
   - 단일 커밋 모드: `git rev-parse --short <hash>` → `commit: <hash>`
   - 커밋 범위 모드: 검증된 양 끝 커밋을 각각 짧은 해시로 표시하고 입력과 같은 구분자 유지 → 예: `range: <start>..<end>`
6. 현재 디렉토리에서 AI 컨벤션 파일(`AGENTS.md`, `CLAUDE.md`, `GEMINI.md` 등)이 있으면 경로를 기록하십시오. 단, 동일 파일을 가리키는 symlink는 한 번만 전달합니다 (realpath 기반 dedup) — Step 2에서 리뷰 에이전트에게 컨텍스트로 전달합니다.
7. **Large diff 분할 (token efficiency):** diff가 1500줄을 초과하면 다음 절차로 부분 집합 A·B에 분배하십시오.
   1. **공용 헤더 식별 (양쪽 공통 전달):** `*Define.h`, `*Models.h`, `*Constants.h` 등 enum/타입/상수를 정의하는 헤더 파일은 분할 대상에서 제외하고 양쪽 에이전트 모두에게 전달합니다 (cross-file 네이밍·미러링 패턴 감지 보존).
   2. **prefix 그룹핑:** 같은 디렉토리 prefix를 공유하는 파일은 하나의 그룹으로 묶습니다 (예: `RVmacRXViewerDisplay/**`는 한 그룹, Sender/Receiver 짝은 함께).
   3. **Greedy bin-packing:** 그룹 단위로 줄 수 합계가 균등해지도록 A·B 두 부분 집합에 분배합니다.
   4. **분배:**
      - **Agent 1**에게 `(A의 diff + A의 파일 목록 + 공용 헤더)` 전달.
      - **Agent 2**에게 `(B의 diff + B의 파일 목록 + 공용 헤더)` 전달.
      - **양쪽에 동일한 부분 집합을 전달하지 마십시오.** 양쪽 전달 시 분할 효과가 0이 됩니다.
   5. **단일 파일 예외:** 단일 파일이 1500줄을 초과하는 경우에는 분할하지 않고 그대로 전달하되, 에이전트에게 핵심 변경 로직에 집중하도록 지시하십시오.

   > Rationale: 4점 측정에서 분기는 트리거됐으나 분배 누락으로 비용이 $8.55까지 상승(M8 케이스). 부분 집합 명시 분배 + 공용 헤더 broadcast로 토큰 ~40% 감소를 노립니다.

### Step 2 — 리뷰 수행

호스트가 제공하는 sub-agent 도구로 Agent 1과 Agent 2를 **각각 별개의 sub-agent 호출로 dispatch하십시오. 단일 sub-agent 호출에 두 체크리스트를 통합하는 것은 금지합니다.** 두 호출은 단일 메시지에서 동시에 실행하고, 가능하면 병렬/background 옵션을 사용하십시오.

| 호스트      | 도구명       | 호출 형식                                            |
| ----------- | ------------ | ---------------------------------------------------- |
| Claude Code | `Task`       | `subagent_type: general-purpose`, `background: true` |
| OpenCode    | `task`       | `subagent_type: <호스트에 등록된 generalist 계열>`   |
| Gemini CLI  | `generalist` | `generalist(request: string)`                        |
| Pi          | `subagent`   | 호스트가 제공하는 호출 형식 사용                      |

> 호스트가 sub-agent 도구를 제공하지 않는 경우에 한해 메인 에이전트가 두 reviewer 체크리스트를 순차 수행하십시오. 단, sub-agent 도구가 등록되어 있으면 **반드시 호출을 시도**하고, **실제 에러가 발생한 경우에만 fallback을 발동**합니다. 사전 추측이나 사용자 컨텍스트 기반 자가 판단으로 fallback을 발동하지 마십시오.
>
> Claude Code의 `Task` 호출 시 `model` 결정 로직:
>
> - `--heavy` 없음 (기본) → `model: "sonnet"` 명시 (부모 모델 무관)
> - `--heavy` 있음 → `model: "opus"` 명시 (부모 모델 무관)
>
> 정책: 코드 리뷰는 패턴 매칭 비중이 높아 Sonnet 4.6으로 충분합니다. Opus 4.7 단가는 ~5× 비싸므로 기본은 Sonnet, 매우 미묘한 동시성/논리 버그가 예상되는 케이스에 한해 `--heavy`로 Opus opt-in.
> Sonnet 환경에서 호출되어도 동일하게 Sonnet 명시 (cross-host 일관성).
>
> Rationale: viewer repo 4점 측정에서 Opus×2 dual-agent 비용이 $8.55까지 도달. Sonnet 강제로 ~75% 단가 절감.

각 에이전트에게 전달하는 프롬프트의 **맨 첫 줄에 반드시** 다음 문장을 포함하십시오 (anti-bias):

> **이 메시지 외의 어떤 사전 컨텍스트나 의도 추정도 고려하지 마십시오. 아래 전달된 코드와 메타데이터만 보고 객관적으로 판정하십시오.**

이어서 각 에이전트에게 다음 정보를 전달하십시오:

- 해당 에이전트에게 할당된 diff (Step 1-7에서 분할된 경우 부분 집합 A 또는 B + 공용 헤더 diff; 분할되지 않은 경우 diff 전문)
- 해당 에이전트에게 할당된 변경 파일 목록 (분할 시 부분 집합 + 공용 헤더 파일 목록)
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

두 리뷰 결과를 대조하고, 출력 원칙에 따라 채팅에는 짧은 최종 결과만 남기십시오.

- **기본 실행:** `.cube/review.md`를 읽거나 쓰지 말고, 리뷰 저장을 위해 `.cube/`나 `.cube/.gitignore`를 생성하지 마세요.
- **저장 요청 (`--save` 또는 `--clear`):** 변경사항이 있고 리뷰를 완료한 경우에만, 저장용 상세 결과를 아래 형식으로 한 번 작성하세요. 저장 직전에 `.cube/`가 없으면 생성하세요. `.cube/.gitignore`가 없다면 아래 내용으로 생성하고, 이미 있으면 그대로 두세요.

  ```gitignore
  # Cube - Generated file tracking policy
  # Tracked: plans/ (persistent, git-committed)
  # Ignored: temporary outputs
  review.md
  summary.md
  ```

- **저장 방식:** 새 상세 결과와 헤더를 `.cube/` 안의 임시 파일에 작성하세요. `--save`에서는 기존 로그가 있다면 구분 줄을 넣고 기존 바이트를 임시 파일 뒤에 이어 붙이세요. 파일 간 복사는 Bash에서 처리하고, 기존 내용을 읽기 도구나 명령 출력으로 모델에 가져오지 마세요. `--clear`에서는 기존 내용을 읽거나 이어 붙이지 않습니다. 임시 파일이 완성된 뒤에만 `{project_root}/.cube/review.md`를 교체하세요. 기존 파일을 먼저 삭제하지 말고, 저장이 실패하면 기존 기록을 보존하고 임시 파일을 정리하세요.
- **저장 헤더** (모드별 형식):
  - 워킹트리 / 파일 경로: `# YYYY-MM-DD HH:MM | HEAD: <hash>`
  - 단일 커밋: `# YYYY-MM-DD HH:MM | commit: <hash>`
  - 커밋 범위: Step 1의 범위 레이블 사용 (예: `# YYYY-MM-DD HH:MM | range: <start>..<end>`)

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

| 환경     | 기본 (sub-agent)     | `--heavy`                                                 |
| -------- | :------------------- | :-------------------------------------------------------- |
| Claude   | Sonnet 4.6           | Opus 4.7                                                  |
| OpenCode | 호스트 mid-tier 기본 | 호스트 premium tier                                       |
| Gemini   | Pro                  | Pro (Gemini는 Pro가 최상위 — `--heavy`는 no-op + warning) |

> 코드 리뷰는 패턴 매칭 비중이 높아 Sonnet 4.6으로 충분합니다. 회사 환경 등 Pro 미가용 시에는 Flash로 자동 fallback. Flash 모델로도 핵심 보안·크래시 이슈에 대한 객관 판정이 가능합니다.

---

**Updated At:** 2026. 10. 19.
