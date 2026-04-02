# Agent Skills

이 디렉토리는 Claude, Gemini, OpenCode 등 호환되는 AI 에이전트들이 공통으로 사용하는 **Agent Skills**를 저장하는 곳입니다.

## 🌟 What are Agent Skills?

Agent Skill은 AI 에이전트가 특정 상황에서 어떻게 행동해야 하는지, 혹은 어떤 도메인 지식을 활용해야 하는지를 정의한 모듈화된 지침서입니다. 에이전트는 사용자의 요청을 분석하고, 필요한 경우 관련된 스킬을 동적으로 로드하여 작업을 수행합니다.

## 📂 Directory Structure

각 스킬은 고유한 이름의 디렉토리(kebab-case) 안에 `SKILL.md` 파일 형태로 작성되어야 합니다.

```text
skills/
├── my-awesome-skill/
│   └── SKILL.md
└── another-skill/
    └── SKILL.md
```

## 📝 How to Create a Skill

새로운 스킬을 추가하려면 다음 규격을 준수하여 `SKILL.md` 파일을 작성하세요.

1. **Title (Skill Identifier):** 파일의 가장 첫 줄은 스킬의 고유 식별자(Identifier) 역할을 하는 최상위 헤딩이어야 합니다. 이 저장소의 스킬임을 명확히 하고 다른 외부 스킬과의 충돌을 방지하기 위해, 반드시 **`# cube:skill-name`** 형식의 네임스페이스와 **kebab-case(소문자, 띄어쓰기 없이 하이픈 연결)**를 사용하세요. (예: `# cube:code-reviewer`)
2. **Description:** 에이전트가 언제 이 스킬을 호출해야 하는지 판단할 수 있도록, 스킬의 목적과 트리거 조건을 명확히 설명하는 블록이 필요합니다.
3. **Instructions:** 스킬이 활성화되었을 때 에이전트가 따라야 할 구체적인 행동 지침이나 규칙을 나열합니다.

### 📄 Example `SKILL.md`

```markdown
# cube:frontend-reviewer

이 스킬은 사용자가 React 또는 Vue.js 프론트엔드 코드에 대한 리뷰를 요청할 때 사용됩니다.

## Instructions

- 컴포넌트는 항상 함수형으로 작성되었는지 확인하세요.
- 접근성(a11y) 위반 사항이 없는지 검토하세요.
- 상태 관리가 불필요하게 복잡하지 않은지 확인하고, 더 나은 대안을 제시하세요.
```

## 🔗 Compatibility

이 디렉토리의 스킬들은 다음 에이전트 플랫폼에서 호환되도록 설계되었습니다:
- **Claude Code** (`~/.claude/skills/`)
- **OpenCode** (`~/.config/opencode/skills/`)
- **Gemini CLI** (호환 가능)

루트 디렉토리의 `scripts/install.sh`를 사용하여 이 폴더를 각 에이전트의 환경에 심볼릭 링크로 연결하여 사용할 수 있습니다.
