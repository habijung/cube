---
name: cube-commit
description: 변경 사항에 대해 커밋을 수행하거나 커밋 메시지를 추천할 때 사용되는 스킬입니다.
trigger:
  - /cube-commit
  - commit
argument-hint: "[메시지 힌트 또는 키워드]"
disable-model-invocation: false # Claude, User 모두 사용 가능
allowed-tools: Bash
compatibility: opencode, claude, gemini
---

# Commit Assistant

사용자가 "commit", "git commit", "Commit the changes", "커밋해줘", "커밋 메시지 추천"과 같은 요청을 할 때 이 스킬이 트리거됩니다.

## Instructions

1. **Status Investigation:** 대상 저장소 루트에서 `git symbolic-ref -q HEAD`가 로컬 브랜치를 가리키지 않으면 중단하세요. 실제 인덱스를 읽기 전에 `git rev-parse --absolute-git-dir`과 `git rev-parse --git-common-dir`로 Git 디렉터리를 확인하고, 어느 쪽에든 `sharedindex.*`가 있으면 공유 인덱스의 시각을 갱신하지 않도록 이 절차를 중단하세요(이전 파일이 남은 경우도 포함). 그 외에는 `git --no-optional-locks status` 및 `git --no-optional-locks diff --no-ext-diff --no-textconv HEAD` (이미 스테이징했거나 첫 커밋이면 `HEAD` 대신 `--staged`)를 실행하여 현재 추적 중인 파일 상태와 구체적인 변경 내역을 확인하세요. 이전에 어떤 커밋들이 있었는지 보려면 `git log -n 3` 등을 활용하여 스타일을 참고하되, `## Commit Message Rules`에 정의된 규칙이 항상 우선합니다. **반드시 스킬 호출 시점에 명령어를 새로 실행하세요. 대화 컨텍스트에 남아 있는 이전 git 출력을 재사용해서는 안 됩니다.**
2. **Author Resolution (Silent):** 다음 순서로 author 정보를 수집하되, 오류가 없는 한 사용자에게 보고하지 마세요.
   - `git config --local user.name` / `git config --local user.email` 실행 → local 설정 존재 여부를 내부적으로 기록 (출처 태그 결정용)
   - `git config user.name` / `git config user.email` 실행 → 실제 사용될 author 확정 (local → global 자동 fallback)
   - **local, global 모두 없음:** 커밋을 진행하지 말고 사용자에게 경고하세요.
   - `git remote get-url origin 2>/dev/null` 실행 → remote URL을 내부적으로 기록 (제안 단계의 경고 메시지 출력 여부 판단용)
3. **Context Analysis (Silent):** Step 1에서 수집한 상태와 diff를 재분석하여 현재 진행 중인 작업의 전체 맥락(큰 그림)을 파악하세요. 별도 명령어를 재실행하지 마세요. 결과를 사용자에게 별도로 보고하지 마세요.
4. **Message Drafting:** 파악한 전체 맥락을 바탕으로 커밋 메시지 초안을 작성하되, 타겟은 다음 규칙을 따릅니다.
   - **Staged 파일이 있는 경우:** 전체 작업 중 *현재 스테이징된 파일들*이 담당하는 역할에 맞춰 메시지를 작성합니다.
   - **Staged 파일이 없는 경우:** 전체 변경 사항을 한 번에 커밋하려 한다고 간주합니다. 모든 modified + untracked 파일을 확인한 뒤, 각 파일을 현재 커밋 주제와의 관련성으로 분류하세요.
     - **관련 있음:** 커밋 주제와 직접 연관된 파일 → 스테이징 대상으로 선정
     - **관련 없음:** 다른 작업(별도 Agent 또는 작업 흐름)에 속하는 파일 → 스테이징 제외
     - Step 5에서 분류 결과와 실제로 스테이징할 파일 경로를 명시하세요. 이미 staged 변경이 있으면 추가 스테이징을 제안하지 마세요.
   - 커밋 메시지는 '무엇을(what)' 했는지보다는 '왜(why)' 했는지에 초점을 맞춥니다. (Conventional Commits 스타일)
   - **Context Independence:** 메시지는 현재 세션/대화 맥락 없이도 독립적으로 이해되어야 합니다. `Phase`, `이전/다음 작업`, `앞서 논의한 대로` 같은 세션 의존적 표현을 사용하지 마세요. (자세한 금지 표현은 `Commit Message Rules` 7번 참고)
5. **Proposal & Approval Request:** 작업 맥락, 파일 상태, 커밋 메시지와 지문을 한 번에 제시하세요. **승인 대상은 제안한 커밋**이며, 지정 파일의 스테이징이 필요한 경우 그 작업도 제안에 포함합니다. 제시 직전에 `Commit Message Rules` 7번을 확인하세요.
   - 이 절차는 일반 커밋 제안에 사용하세요. 병합·리베이스·체리픽·리버트 등 진행 중인 Git 작업이 있으면 이 절차를 시작하지 말고 해당 작업 상태를 보고하세요. 저장소·브랜치·기준 `HEAD`(첫 커밋이면 없음)·초기 인덱스 트리·예정 트리·대상 경로·전체 메시지 해시를 제안에 연결해 기록하세요. 메시지는 마지막 줄바꿈을 포함한 파일로 보관하세요.
   - 제안 전에는 실제 인덱스를 변경하지 마세요. 실제 인덱스의 복사본을 `GIT_INDEX_FILE`로 지정한 임시 환경에서 현재 트리를 계산합니다. 임시 Git 명령에는 `-c core.splitIndex=false`를 지정하세요. 추가 스테이징이 필요하면 같은 임시 인덱스에 `git --literal-pathspecs add -A -- <선정 경로들>`을 실행하여 예정 트리를 계산하세요. 실제 객체 저장소는 대체 객체 저장소로만 참조하고 새 객체는 임시 객체 디렉터리에만 쓰세요. 첫 커밋처럼 실제 인덱스가 없다면 임시 환경에서 `git read-tree --empty`로 초기화하세요.
   - 기준 `HEAD`의 트리(첫 커밋이면 빈 트리)와 예정 트리 사이의 전체 diff를 `--no-ext-diff --no-textconv --binary --full-index --ignore-submodules=none --submodule=short`로 확인해 제안 설명과 대상 경로가 일치하는지 검증하고, 사용자에게 그 diff 또는 열 수 있는 동일한 패치를 보여 주세요. 이미 스테이징된 제안이면 대상 경로의 미스테이징 변경 내용과 파일 유형(스테이징된 삭제 후 재생성된 파일 포함)까지 기록하세요. 상태 코드만으로 대체하지 마세요. 제안과 실제 변경을 정확히 연결할 수 없으면 제안하지 말고 이유를 보고하세요. 승인 대기 중 필요한 메시지·패치 등은 비공개 임시 디렉터리에만 두고, 제안 무효화나 절차 종료 시 정리하세요.

   ```text
   ### 💡 작업 맥락 요약
   - (AI가 파악한 현재 진행 중인 전체 작업 요약 1~2줄)

   ### 📦 커밋 대상 파일 상태
   - 🟢 Staged    : <파일 목록> (이미 스테이징됨, 커밋 대상)
   - 🔵 선정됨     : <파일 목록> (승인 후 `git add`로 지정 경로만 스테이징)
   - 🟡 Unstaged  : <파일 목록> (수정됨, 커밋 주제 무관 → 제외)
   - ⬜ Untracked : <파일 목록> (신규, 커밋 주제 무관 → 제외)
     *(Staged가 없고 선정된 파일이 있는 경우: 승인 후 지정 경로만 스테이징하고 제안과 일치하면 추가 승인 없이 커밋합니다.)*

   ---
   Author : <name> <<email>>  (local)   ← local config 사용 시
   Author : <name> <<email>>  (global)  ← global config fallback 시
   Repository : <작업 트리 루트>
   Branch : <current-branch>
   Fingerprint:
     Base HEAD    : <기준 커밋 ID 또는 없음>
     Commit files : <커밋 대상 경로 목록>
     Commit tree  : <예정 트리 ID>
     Diff summary : <N files, +A -B>
     Message hash : <전체 메시지 해시>
   Message:
     <commit subject>

     <commit body (있는 경우)>
   Patch:
     <예정 트리의 최종 diff 또는 사용자가 열 수 있는 동일 패치>
   ```

   - **`(global)` 태그이고 remote URL이 존재하는 경우:** Author 줄 바로 아래에 경고를 추가하세요.

     ```text
     ⚠️  Remote: <remote-url> — Local git config 미설정
     ```

6. **Approval Validation:** 사용자의 명시적 승인이 **아직 유효한 Step 5의 최신 제안**을 가리키는 것이 명확할 때만 인정하세요. 같은 제안에 대한 질문과 설명만 오갔다면 승인 대기 상태를 유지합니다. 제안문이 직전 AI 메시지가 아니어도 다시 제시하거나 재승인을 요구하지 마세요.
   - 질문 자체나 설명을 이해했다는 응답은 커밋 승인이 아닙니다. `진행`, `OK` 같은 짧은 응답도 대화 맥락에서 최신 제안의 커밋 실행을 명시적으로 승인하는 것이 분명할 때만 인정하세요. 여러 제안이 있거나 다른 작업이 끼어들어 승인 대상이나 의도가 불명확하면, 스테이징하지 말고 무엇을 승인한 것인지 확인하세요.
   - 인덱스를 읽기 전에 Step 1의 공유 인덱스 확인을 반복하세요. 스테이징 전에 Step 5와 같은 방법으로 저장소·브랜치·기준 `HEAD`·초기 인덱스 트리·예정 트리·경로·메시지를 확인하세요. 이미 스테이징된 제안은 Step 5에서 기록한 미스테이징 내용과 파일 유형도 확인하세요. 직전 승인 제안과 다르거나 같은 저장소에서 다른 Git 작업이 겹친 사실을 확인하면, 인덱스를 수정하지 말고 중단하세요.
7. **Commit Execution:** 추가 스테이징이 제안에 포함된 경우에만 실제 인덱스에 `git --literal-pathspecs add -A -- <승인된 경로들>`을 실행하세요. 기존 스테이징을 자동 변경하거나 제외한 파일을 추가하지 마세요.
   - 즉시 진행 중인 다른 Git 작업이 없는지 확인하고, 저장소·브랜치·기준 `HEAD`와 실제 스테이징된 경로·트리·전체 메시지를 승인본과 대조하세요. 일치하면 일반 `git commit --cleanup=verbatim -F <승인된 메시지 파일>`을 실행합니다. 기존 Git 훅을 우회하거나 `-a`·경로 인자로 커밋 대상을 바꾸지 마세요. **제안한 스테이징이 검증을 통과하면 추가 승인 없이 커밋합니다.**
   - 실행 후 종료 상태, 현재 브랜치가 승인한 브랜치인지, 그리고 그 브랜치에 실제로 반영된 커밋을 확인하세요. 전체 부모 목록은 승인한 기준 `HEAD` 한 개(첫 커밋이면 없음)와 일치해야 하고, 트리·전체 메시지도 확인하세요. Git 훅이나 동시 변경으로 결과가 달라졌거나 상태가 불명확하면 실제 상태를 보고하고 자동 재시도·원복은 하지 마세요.

## Guidelines

- **No Implicit Commit:** 사용자가 명시적으로 승인하기 전까지 `git commit`을 실행해서는 안 됩니다. 커밋 메시지 수정 요청이 있을 경우 Step 4로 돌아가 재작성 후 다시 승인을 받으세요.
- **Approval Invalidation:** 제안이 철회되거나 새 제안으로 대체되면 이전 제안과 그 승인은 더 이상 사용할 수 없습니다. 제안한 커밋 대상·내용·메시지 또는 저장소·브랜치·기준 `HEAD`가 달라졌거나, 제안된 절차를 시작하기 전에 인덱스 트리가 달라졌으면 승인 여부와 관계없이 그 제안은 무효입니다. 사유를 설명하고, 커밋을 계속할 경우 최신 상태로 다시 제안해 명시적 승인을 받으세요.
- **Stop on Failure:** 스테이징에 실패했거나 제안과의 일치를 확인할 수 없으면 커밋하지 마세요. 원인과 현재 인덱스 상태를 보고하세요. 예상과 다른 스테이징을 자동 수정하거나 되돌리지 마세요.
- **Proposal State Machine:** `proposal_prepared -> approval_pending -> approved_for_exact_proposal -> verified_index -> commit_executed` 순서를 따릅니다. 승인 후 제안된 스테이징을 실행하는 것은 별도의 승인 단계가 아닙니다.
- **No Push Policy:** 어떠한 경우에도 `git push`를 실행하지 마세요.

## Commit Message Rules

1. **Subject prefix 이후 첫 글자는 대문자로 시작**: `fix: Invalidate...` (O), `fix: invalidate...` (X)
2. **의도와 결과(Why & Outcome) 중심의 기록**: `git diff`로 확인 가능한 단순 코드 변경 사항(예: `- 수정 전 코드를 수정 후로 변경함`, `- header 1을 header 2로 수정`)은 **절대 본문에 작성하지 마십시오.** 대신 해당 수정이 **왜(Why)** 필요했는지, 그리고 수정 후 어떤 **결과(Outcome)**가 기대되는지를 기술하십시오. (예: `- 가독성 확보를 위해 헤더 계층 구조 최적화`, `- 컴파일 경고 제거를 위한 불필요한 캐스트 제거`)
3. **Co-author 추가 금지**: AI agent가 생성한 커밋이라도 `Co-Authored-By:` 등의 트레일러를 절대 포함하지 않는다.
4. **Subject에 대상 명시 (선택)**: 변경 대상이 명확할 경우 `in <파일명>` 또는 `of <컴포넌트>` 형태로 subject에 포함 가능.
5. **Description 리스트 포맷팅**: Description을 작성할 때 여러 개의 리스트 항목(bullet point)을 나열하는 경우, 각 항목 사이에 절대 빈 줄(Empty Line)을 추가하지 마십시오. 항목들은 연속된 줄에 작성되어야 합니다.
6. **본문 생략의 원칙**: 제목(Subject)만으로 변경의 의도와 내용이 명확히 전달되는 경우, 본문(Description)은 과감히 생략하고 제목만으로 커밋 메시지를 생성하십시오.
7. **컨텍스트 독립성 (Context Independence)**: 커밋 메시지는 현재 작업 세션/대화 맥락 없이 `git log`만 봤을 때도 독립적으로 이해되어야 합니다. 다음과 같은 세션 의존적 표현을 절대 사용하지 마십시오.
   - **단계/Phase 참조:** `Phase N에서는...`, `Step 2 작업으로...`, `다음 단계로...`
   - **과거 작업 참조:** `이전 작업에서...`, `지난 커밋에서...`, `앞서 논의한 대로...`
   - **미래 계획 참조:** `차후에 수정 예정`, `나중에 처리할...`, `다음 PR에서는...`

   대신 변경 자체의 **의도(Why)**와 **결과(Outcome)**만 절대적 표현으로 기술하십시오.
   - ❌ `Phase 2에서는 이를 API로 노출하기 위한 사전 작업으로 모듈을 분리`
   - ✅ `재사용성 확보를 위해 모듈 분리 — 외부 API 노출의 사전 단계로 활용 가능`

### Example

```markdown
feat: Add dark mode support in ThemeManager

- Persist user selection to UserDefaults for cross-session consistency
- Improve visual accessibility by aligning with system appearance settings
```

#### 컨텍스트 의존성 비교 (Rule 7 참고)

❌ **Bad** — 세션 맥락이 없으면 의미 불명:

```markdown
refactor: Split ThemeManager module

- Phase 2에서 다크모드 토글 API를 노출하기 위한 사전 작업
- 이전에 논의한 대로 ThemeStore와 ThemeView를 분리
```

✅ **Good** — 독립적으로 이해 가능:

```markdown
refactor: Split ThemeManager into store and view layers

- Decouple state persistence from rendering for independent testing
- Enable future extension points without modifying view layer
```

---

**Updated At:** 2026. 5. 17.
