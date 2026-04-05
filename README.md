# Cube 🧊

**AI Agent Configuration System**

에이전트별로 산재된 설정과 지침(Instructions)을 통합하여 관리하고, 여러 프로젝트에 일관되게 적용하기 위한 범용 설정 시스템입니다.

## 📂 Directory Structure

- `skills/`: 모든 에이전트(Claude, Gemini, OpenCode 등)가 공유하는 통합 지침 (SKILL.md 포맷)
- `.config/opencode/`: OpenCode 전역 설정 템플릿
- `templates/AGENTS.md`: 개별 프로젝트 루트에 복사하여 사용하는 로컬 지침 템플릿
- `scripts/install.sh`: 설정 및 심볼릭 링크 자동화 스크립트
- `scripts/claude-status-line.sh`: Claude Code 커스텀 status line 스크립트
- `cube.sh`: 에이전트 실행 단축 명령어(Alias) 모음

## 🚀 Getting Started

> [!WARNING]
> 이 스크립트는 현재 개발 초기 단계이므로 사용에 주의해주세요. 필요한 경우 스크립트 내용을 먼저 확인한 후 실행하는 것을 권장합니다.

이 프로젝트를 로컬에 클론한 후, 다음 스크립트를 실행하여 설정을 적용합니다:

```bash
source ./scripts/install.sh
```

### 🤖 For AI Agents

AI 에이전트는 사용자가 "Cube 환경을 세팅해줘" 또는 "설치해줘"라고 요청할 경우 다음 지침을 엄격히 따르세요:

1. **에이전트 선택 확인:** 사용자에게 어떤 AI 에이전트(Claude Code, Gemini CLI, OpenCode)의 설정을 진행할지 먼저 물어보세요. (다중 선택 가능)
2. **설치 스크립트 실행:** 사용자의 선택을 바탕으로 터미널 도구를 사용하여 `bash ./scripts/install.sh` 명령어를 실행하세요. 선택된 에이전트를 인자로 전달해야 합니다.
   - 예시: `bash ./scripts/install.sh claude gemini`
   - 아무 인자도 전달하지 않으면 기본적으로 모든 에이전트를 대상으로 세팅을 시도합니다.
3. **사후 확인:** 스크립트 실행 결과를 확인하고 사용자에게 어떤 파일들이 설정되었는지 보고하세요.

## 📚 References

에이전트가 이 시스템의 규격이나 확장에 대해 더 자세한 정보가 필요한 경우, 다음 공식 문서들을 참고할 수 있습니다:

- **Gemini CLI:** [Creating Agent Skills](https://geminicli.com/docs/cli/creating-skills/)
- **Claude Code:** [Extending Claude with Skills](https://code.claude.com/docs/en/skills/)
- **OpenCode:** [Agent Skills Documentation](https://opencode.ai/en/docs/skills/)
