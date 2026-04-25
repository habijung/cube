---
name: cube-commit
description: 변경 사항에 대해 커밋을 수행하거나 커밋 메시지를 추천할 때 사용되는 스킬입니다. trigger: /cube-commit, commit
argument-hint: "[메시지 힌트 또는 키워드]"
disable-model-invocation: false # Claude, User 모두 사용 가능
allowed-tools: Bash
compatibility: opencode, claude, gemini
---

# Commit Assistant

사용자가 "commit", "git commit", "Commit the changes", "커밋해줘", "커밋 메시지 추천"과 같은 요청을 할 때 이 스킬이 트리거됩니다.

## Instructions

1. **Status Investigation:** 쉘 명령어 `git status` 및 `git diff HEAD` (또는 `git diff --staged`)를 실행하여 현재 추적 중인 파일 상태와 구체적인 변경 내역을 확인하세요. 이전에 어떤 커밋들이 있었는지 보려면 `git log -n 3` 등을 활용하여 스타일을 파악하세요. **반드시 스킬 호출 시점에 명령어를 새로 실행하세요. 대화 컨텍스트에 남아 있는 이전 git 출력을 재사용해서는 안 됩니다.**
2. **Author Resolution (Silent):** 다음 순서로 author 정보를 수집하되, 오류가 없는 한 사용자에게 보고하지 마세요.
   - `git config --local user.name` / `git config --local user.email` 실행 → local 설정 존재 여부를 내부적으로 기록 (출처 태그 결정용)
   - `git config user.name` / `git config user.email` 실행 → 실제 사용될 author 확정 (local → global 자동 fallback)
   - **local, global 모두 없음:** 커밋을 진행하지 말고 사용자에게 경고하세요.
   - `git remote get-url origin 2>/dev/null` 실행 → remote URL을 내부적으로 기록 (Step 5 경고 판단용)
3. **Summary of Changes:** Staged / Unstaged / Untracked 파일 목록을 간결하게 정리하여 사용자에게 보고하세요. 스테이징되지 않은 파일이 있다면 현재 커밋 범위에서 제외됨을 함께 안내하세요.
4. **Message Drafting:** 변경 내역을 바탕으로 명확하고 간결한 커밋 메시지 초안을 작성하세요. 커밋 메시지는 주로 '무엇을(what)' 했는지보다는 '왜(why)' 했는지에 초점을 맞춥니다. (Conventional Commits 스타일 권장)
5. **Approval Request:** 아래 형식으로 커밋 정보를 사용자에게 제시하고, 수정이 필요한지 확인하세요. 사용자가 명시적으로 승인(예: "진행해줘", "OK", "approve")하기 전까지는 절대 커밋을 실행하지 마세요.

   ```text
   Author : <name> <<email>>  (local)   ← local config 사용 시
   Author : <name> <<email>>  (global)  ← global config fallback 시
   Branch : <current-branch>
   Message:
     <commit subject>

     <commit body (있는 경우)>
   ```

   - **`(global)` 태그이고 remote URL이 존재하는 경우:** Author 줄 바로 아래에 경고를 추가하세요.

     ```text
     ⚠️  Remote: <remote-url> — Local git config 미설정
     ```

6. **Commit Execution:** 사용자의 명시적 승인 이후 `git commit`을 실행하세요. `git push`는 사용자가 별도로 요청하지 않는 한 절대 실행하지 마세요.

## Guidelines

- **No Implicit Commit:** 사용자가 명시적으로 승인하기 전까지 `git commit`을 실행해서는 안 됩니다. 커밋 메시지 수정 요청이 있을 경우 Step 4로 돌아가 재작성 후 다시 승인을 받으세요.
- **No Push Policy:** 어떠한 경우에도 `git push`를 실행하지 마세요.

## Commit Message Rules

1. **Subject prefix 이후 첫 글자는 대문자로 시작**: `fix: Invalidate...` (O), `fix: invalidate...` (X)
2. **의도와 결과(Why & Outcome) 중심의 기록**: `git diff`로 확인 가능한 단순 코드 변경 사항(예: `- 수정 전 코드를 수정 후로 변경함`, `- header 1을 header 2로 수정`)은 **절대 본문에 작성하지 마십시오.** 대신 해당 수정이 **왜(Why)** 필요했는지, 그리고 수정 후 어떤 **결과(Outcome)**가 기대되는지를 기술하십시오. (예: `- 가독성 확보를 위해 헤더 계층 구조 최적화`, `- 컴파일 경고 제거를 위한 불필요한 캐스트 제거`)
3. **Co-author 추가 금지**: AI agent가 생성한 커밋이라도 `Co-Authored-By:` 등의 트레일러를 절대 포함하지 않는다.
4. **Subject에 대상 명시 (선택)**: 변경 대상이 명확할 경우 `in <파일명>` 또는 `of <컴포넌트>` 형태로 subject에 포함 가능.
5. **Description 리스트 포맷팅**: Description을 작성할 때 여러 개의 리스트 항목(bullet point)을 나열하는 경우, 각 항목 사이에 절대 빈 줄(Empty Line)을 추가하지 마십시오. 항목들은 연속된 줄에 작성되어야 합니다.
6. **본문 생략의 원칙**: 제목(Subject)만으로 변경의 의도와 내용이 명확히 전달되는 경우, 본문(Description)은 과감히 생략하고 제목만으로 커밋 메시지를 생성하십시오.

### Example

```markdown
feat: Add dark mode support in ThemeManager

- Persist user selection to UserDefaults for cross-session consistency
- Improve visual accessibility by aligning with system appearance settings
```

---

**Updated At:** 2026. 4. 25.
