# Agent Skills

이 디렉토리는 Claude, Gemini, OpenCode 등 호환되는 AI 에이전트들이 공통으로 사용하는 **Agent Skills**를 저장하는 곳입니다.

## 🌟 What are Agent Skills?

Agent Skill은 AI 에이전트가 특정 상황에서 어떻게 행동해야 하는지, 혹은 어떤 도메인 지식을 활용해야 하는지를 정의한 모듈화된 지침서입니다. 에이전트는 사용자의 요청을 분석하고, 필요한 경우 관련된 스킬을 동적으로 로드하여 작업을 수행합니다.

## 📂 Directory Structure

각 PC의 시스템 스킬과 이 저장소의 스킬을 명확히 구분(Namespace)하기 위해, 모든 스킬 이름 앞에는 반드시 **`cube-`** 접두사를 붙여야 합니다.

각 스킬은 고유한 이름의 디렉토리(`cube-kebab-case`) 안에 `SKILL.md` 파일 형태로 작성되어야 합니다.

```text
skills/
├── cube-my-new-skill/
│   ├── SKILL.md
│   └── scripts/ (옵션: 실행 스크립트)
└── cube-another-skill/
    └── SKILL.md
```

## 📝 How to Create a Skill (Universal Template)

Gemini CLI, Claude Code, OpenCode 모두에서 완벽하게 호환되도록 다음 규격을 엄격히 준수하세요.

1. **YAML Frontmatter (필수):** 파일 최상단에 `---`로 둘러싸인 메타데이터를 작성합니다.
2. **Name Matching & Namespace:** `name` 속성의 값은 반드시 **`cube-kebab-case`** 형태의 소문자여야 하며, **디렉토리 이름과 정확히 일치**해야 합니다. (전역 스킬과의 이름 충돌을 방지하기 위함입니다)
3. **Description:** 에이전트가 언제 호출해야 할지 알 수 있도록 명확하고 간결하게(250자 이내) 작성합니다.
4. **Argument Hint (선택):** `argument-hint` 필드로 스킬 호출 시 사용자에게 표시할 입력 힌트를 지정합니다. (Claude Code 전용)
5. **Updated At (필수):** 파일 본문 마지막에 `---` 구분선과 함께 `**Updated At:** YYYY. M. D.` 형식으로 작성 날짜를 기록합니다.

### 📄 Example `SKILL.md`

```markdown
---
name: cube-frontend-reviewer
description: React 또는 Vue.js 프론트엔드 코드에 대한 리뷰를 요청할 때 사용되는 스킬
argument-hint: "[파일 경로 또는 PR 번호]"
# Claude-specific
disable-model-invocation: false
allowed-tools: Read Grep
# OpenCode-specific
compatibility: opencode, claude, gemini
---

# Frontend Code Reviewer

이 스킬은 프론트엔드 코드 리뷰를 수행합니다.

## Instructions
1. 컴포넌트는 항상 함수형으로 작성되었는지 확인하세요.
2. 접근성(a11y) 위반 사항이 없는지 검토하세요.

## Guidelines
- 상태 관리가 불필요하게 복잡하지 않은지 확인하고, 더 나은 대안을 제시하세요.

---
**Updated At:** YYYY. M. D.
```

## 🔗 Compatibility & Integration

각 에이전트별로 분산된 환경 설정을 줄이기 위해, 범용 에이전트들은 통합 디렉토리인 `~/.agents/skills`를 활용하는 것을 권장합니다.
이 저장소의 스킬들은 다음 경로에 심볼릭 링크로 연결하여 사용할 수 있습니다:

- **Universal (Gemini CLI, OpenCode):** `~/.agents/skills/` (관리 포인트 일원화)
- **Claude Code (전용 규격):** `~/.claude/skills/`

추후 `scripts/install.sh` 스크립트를 통해 위 경로들에 대한 심볼릭 링크 생성을 자동화할 수 있습니다.
