# Cube 🧊

**AI Agent Configuration System**

에이전트별로 산재된 설정과 지침(Instructions)을 통합하여 관리하고, 여러 프로젝트에 일관되게 적용하기 위한 범용 설정 시스템입니다.

## 📂 Directory Structure

- `skills/`: 모든 에이전트(Claude, Gemini, OpenCode 등)가 공유하는 통합 지침 (SKILL.md 포맷)
- `.config/opencode/`: OpenCode 전역 설정 템플릿
- `templates/AGENTS.md`: 개별 프로젝트 루트에 복사하여 사용하는 로컬 지침 템플릿
- `scripts/install.sh`: 설정 및 심볼릭 링크 자동화 스크립트
- `scripts/claude-status-line.sh`: Claude Code 커스텀 status line 스크립트
- `cube.zsh`: 에이전트 실행 단축 명령어(Alias) 모음

## 🚀 Getting Started

> [!WARNING]
> `scripts/install.sh`는 현재 초기 개발 단계입니다. 아직 모든 기능이 구현되지 않았으므로 실행하지 마세요.

이 프로젝트를 로컬에 클론한 후, 다음 스크립트를 실행하여 설정을 적용합니다:

```zsh
source ./scripts/install.sh
```

## 📚 References

에이전트가 이 시스템의 규격이나 확장에 대해 더 자세한 정보가 필요한 경우, 다음 공식 문서들을 참고할 수 있습니다:

- **Gemini CLI:** [Creating Agent Skills](https://geminicli.com/docs/cli/creating-skills/)
- **Claude Code:** [Extending Claude with Skills](https://code.claude.com/docs/en/skills/)
- **OpenCode:** [Agent Skills Documentation](https://opencode.ai/en/docs/skills/)
