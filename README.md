# Cube 🧊
**Unified AI Agent Configuration & Instruction System**

[![Bash Support](https://img.shields.io/badge/Shell-Bash%20%7C%20Zsh-4EAA25.svg)](https://www.gnu.org/software/bash/)
[![AI-Powered](https://img.shields.io/badge/AI-Optimized-blueviolet.svg)](https://geminicli.com)

에이전트별로 파편화된 지침(Instructions)과 설정을 통합 관리하여, 모든 환경(CLI, Web)에서 일관된 AI 경험을 제공하는 범용 설정 시스템입니다.

---

## 🌟 Key Features

- **Architecture First:** 모든 개발 작업 전 아키텍처 설계를 선행하여 견고한 소프트웨어 구조를 지향합니다.
- **Cross-Shell Compatibility:** Bash와 Zsh를 모두 지원하며, `install.sh`를 통해 자동화된 환경 구축이 가능합니다.
- **Multi-Agent Support:** Gemini CLI, Claude Code, OpenCode(with Ollama) 등 다양한 에이전트를 위한 통합 스킬셋을 제공합니다.
- **Topic-based Indexing:** 모든 지침에 명확한 토픽 레이블을 부여하여 AI의 컨텍스트 이해도를 극대화했습니다.
- **Web UI Optimization:** 좁은 화면에서도 가독성을 잃지 않도록 설계된 '요약표 + 상세 리스트' 하이브리드 레이아웃을 채택했습니다.

## 📂 Project Structure

| Directory/File | Description |
| :--- | :--- |
| `cube.sh` | 에이전트 실행 및 환경 통합을 위한 Alias 모음 |
| `scripts/` | `install.sh` 및 환경별 커스텀 스크립트 모음 |
| `skills/` | 모든 에이전트가 공유하는 통합 지침 (**SKILL.md**) |
| `templates/` | 프로젝트 루트에 적용 가능한 로컬 설정 템플릿 |

## 🧩 Core Skills

| Skill | Description |
| :--- | :--- |
| **`cube-commit`** | 원자적 커밋(Atomic Commits) 전략 기반의 커밋 보조 |
| **`cube-question`** | 병렬 탐색을 통한 코드 및 아키텍처 질의응답 |
| **`cube-review`** | 컨벤션 및 효율성 중심의 건설적 코드 리뷰 |
| **`cube-summary`** | 세션 요약 및 컨텍스트 복구용 프롬프트 생성 (Web 호환) |

## 🛠 Getting Started

### 1. Manual Installation
이 저장소를 클론한 후, 다음 명령어를 실행하여 환경을 구축하세요:
```bash
# 기본 설치 (모든 에이전트 지원)
bash ./scripts/install.sh

# 특정 에이전트만 선택 설치
bash ./scripts/install.sh claude gemini
```

### 🤖 2. For AI Agents (Setup Instruction)
AI 에이전트는 사용자가 "Cube 환경을 세팅해줘"라고 요청하면 다음 단계를 따르세요:
1. **Agent Selection:** 어떤 에이전트(Claude, Gemini, OpenCode)를 설정할지 사용자에게 확인합니다.
2. **Execution:** 선택된 에이전트를 인자로 하여 `bash ./scripts/install.sh <agents>`를 실행합니다.
3. **Verification:** 실행 결과를 보고하고, 심볼릭 링크가 정상적으로 생성되었는지 확인합니다.

---

## 📚 References
- [Gemini CLI Documentation](https://geminicli.com/docs/)
- [Claude Code Documentation](https://code.claude.com/docs/)
