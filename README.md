# Cube 🧊

## Unified AI Agent Configuration & Instruction System

[![Bash Support](https://img.shields.io/badge/Shell-Bash%20%7C%20Zsh-4EAA25.svg)](https://www.gnu.org/software/bash/)
[![AI-Powered](https://img.shields.io/badge/AI-Optimized-blueviolet.svg)](https://geminicli.com)

에이전트별로 파편화된 지침(Instructions)과 설정을 통합 관리하여, 모든 환경(CLI, Web)에서 일관된 AI 경험을 제공하는 범용 설정 시스템입니다.

---

## 🤖 For AI Agents

If you are an AI agent, your first action is to **read `AGENTS.md`** and perform the diagnostic mission defined there. This will synchronize your instructions and setup your environment for success.

## 🌟 Key Features

- **Architecture First:** 모든 개발 작업 전 아키텍처 설계를 선행하여 견고한 소프트웨어 구조를 지향합니다.
- **Cross-Shell Compatibility:** Bash와 Zsh를 모두 지원하며, `install.sh`를 통해 자동화된 환경 구축이 가능합니다.
- **Multi-Agent Support:** Gemini CLI, Claude Code, OpenCode(with Ollama), Pi를 위한 통합 스킬셋을 제공합니다.
- **Topic-based Indexing:** 모든 지침에 명확한 토픽 레이블을 부여하여 AI의 컨텍스트 이해도를 극대화했습니다.
- **Web UI Optimization:** 좁은 화면에서도 가독성을 잃지 않도록 설계된 '요약표 + 상세 리스트' 하이브리드 레이아웃을 채택했습니다.

## 📂 Project Structure

| Directory/File | Description                                                          |
| :------------- | :------------------------------------------------------------------- |
| `cube.sh`      | 에이전트 실행 및 환경 통합을 위한 Alias 모음                         |
| `agents/`      | 에이전트별 전용 설정 및 리소스 (배포 대상 경로 미러링)               |
| `scripts/`     | `install.sh` 등 내부 자동화 스크립트                                 |
| `skills/`      | 모든 에이전트가 공유하는 통합 지침 (**SKILL.md**)                    |
| `templates/`   | 프로젝트 루트에 적용 가능한 로컬 설정 템플릿                         |
| `.cube/`       | 스킬 실행 시 생성되는 런타임 출력 디렉토리 ([상세](.cube/README.md)) |

## 🧩 Core Skills

| Skill               | Description                                                  |
| :------------------ | :----------------------------------------------------------- |
| **`cube-cmux`**     | cmux 패널 세션 저장 및 복원 실패 시 재개 명령어 안내         |
| **`cube-commit`**   | 원자적 커밋(Atomic Commits) 전략 기반의 커밋 보조            |
| **`cube-plan`**     | 구현 계획 수립 및 `.cube/plans/` 기반 멀티 에이전트 핸드오프 |
| **`cube-plan-dev`** | 저장된 계획을 로드하여 개발을 이어가는 컨텍스트 복구 스킬    |
| **`cube-question`** | 병렬 탐색을 통한 코드 및 아키텍처 질의응답                   |
| **`cube-review`**   | 3-Step 프로토콜 기반 코드 리뷰 (요청 시 상세 결과 저장)      |
| **`cube-summary`**  | 세션 요약 및 컨텍스트 복구용 프롬프트 생성 (Web 호환)        |

### 🔍 `cube-review` Key Features

- **Structured Protocol:** 초기화 → 리뷰(주제별 독립 리뷰어 1명) → 결과 출력의 3단계 워크플로우를 따릅니다. 놓쳤을 때 영향이 큰 변경에는 해당 리뷰 영역(버그·아키텍처 또는 컨벤션·문서)당 리뷰어 한 명을 추가합니다.
- **Model Selection:** 부모 에이전트가 리뷰 난이도와 확인된 비용 등급을 기준으로 모델을 선택합니다. 상위 비용 등급의 모델은 `--heavy` 또는 별도 승인이 있을 때만 사용합니다.
- **Optional Logging:** 기본으로는 채팅에 짧은 결과만 표시하고 기존 리뷰 파일은 건드리지 않습니다.
- **Functional Flags:**
  - `--heavy`: 이번 리뷰에서 필요한 범위에 상위 비용 등급 모델 사용 허용
  - `--save`: 상세 결과를 `.cube/review.md` 맨 위에 추가
  - `--clear`: `.cube/review.md`를 이번 상세 결과로 교체

## 🛠 Getting Started

### 1. Manual Installation

이 저장소를 클론한 후, 다음 명령어를 실행하여 환경을 구축하세요:

```bash
# 기본 설치 (Claude, Gemini, OpenCode, Pi)
bash ./scripts/install.sh

# 특정 에이전트만 선택 설치
bash ./scripts/install.sh claude gemini

# Pi만 선택 설치
bash ./scripts/install.sh pi

# 전체 환경 진단
bash ./scripts/install.sh --check
```

Skill은 다음 경로에 저장소 디렉터리의 심볼릭 링크로 설치합니다:

- **Claude Code:** `~/.claude/skills/`
- **Gemini CLI · OpenCode · Pi:** 공용 `~/.agents/skills/`

Pi는 공용 경로를 자동 인식하므로 `~/.pi/.agents/skills/`나 Pi용 복사본을 만들 필요가 없습니다. 이미 공용 skill이 설치되어 있으면 같은 링크를 재사용합니다. 각 skill의 에이전트별 실행 조건은 해당 `SKILL.md`를 확인하세요.

Pi 단독 설치는 공용 shell alias·skill 링크와 아래 Pi package만 설정하며, Claude 설정·Gemini 정책·OpenCode 플러그인은 설치하지 않습니다. 구형 Gemini·OpenCode skill 링크 정리도 해당 에이전트를 선택했을 때만 수행합니다.

#### Pi packages

Pi를 선택하거나 기본 전체 설치를 실행하려면 **Pi CLI와 Python 3**가 먼저 설치되어 있어야 합니다. Cube는 Pi 본체를 설치하거나 업데이트하지 않습니다. 사전 조건이 충족되지 않으면 shell 설정·skill 링크 변경 전에 중단합니다. Pi가 필요 없다면 다른 에이전트만 명시적으로 선택하세요.

관리 목록은 [`agents/pi/packages.txt`](agents/pi/packages.txt)이며, 현재 `npm:pi-web-access`와 `npm:pi-subagents`를 포함합니다. 빈 줄·`#` 주석과 버전 없는 npm source만 허용합니다. 버전을 고정하지 않으므로 설치 시점이 다르면 기기 간 버전도 다를 수 있습니다.

- **신규/복구:** `pi install <source>`로 개인 환경에 등록·설치합니다.
- **재실행:** 이미 등록·설치된 관리 대상만 `pi update <source>`로 최신화합니다. Pi 시작 시마다 자동 업데이트하지는 않습니다.
- **범위 보호:** 프로젝트 설정에 영향이 없도록 임시 작업 디렉터리에서 실행하고, 별도로 설치한 package는 직접 업데이트·삭제하지 않습니다. 개인 설정 전체를 복사하거나 symlink하지 않습니다.
- **설정 보존:** object 형식의 resource 필터와 다른 개인 설정을 유지합니다. 같은 package의 버전 고정·중복 선언은 덮어쓰지 않고 해당 항목을 건너뛰며 실패로 보고합니다. 잘못된 JSON도 초기화하지 않습니다.
- **실패 처리:** package별 결과·설치 버전을 표시하며, 일부 실패도 종료 코드에 반영합니다. 성공한 단계는 유지하므로 문제 해결 후 재실행할 수 있습니다. `PI_OFFLINE=1` 또는 `true`인 설치는 최신화를 보장할 수 없어 중단합니다.
- **기기별 설정:** `PI_CODING_AGENT_DIR`을 지정하면 그 개인 환경을 사용합니다. 인증 정보·세션·기기별 설정은 저장소에 수집하지 않습니다.
- **실행 중 세션:** 설치 과정은 Pi/Paseo를 재시작하거나 reload하지 않습니다. 갱신한 extension의 적용은 별도로 확인하세요.

`--check`는 Pi 단독 설치 여부와 관계없이 전체 에이전트 환경을 진단합니다. 선택하지 않은 에이전트의 미설정 항목도 보고할 수 있습니다. Pi 진단은 CLI 존재, 개인 설정의 관리 package 등록 여부, `<agent-dir>/npm/node_modules/`의 package 이름·버전을 로컬에서만 확인합니다. 구형 global npm 설치는 이 관리 경로에 없으면 복구 설치 대상으로 보고합니다. 다운로드·업데이트·extension 로딩·최신 버전 조회는 하지 않으므로, 정상 결과가 실행 호환성이나 최신 버전을 보장하지는 않습니다.

### 🤖 2. For AI Agents (Setup Instruction)

AI 에이전트는 사용자가 "Cube 환경을 세팅해줘"라고 요청하면 다음 단계를 따르세요:

1. **Agent Selection:** 어떤 에이전트(Claude, Gemini, OpenCode, Pi)를 설정할지 사용자에게 확인합니다.
2. **Diagnosis:** 먼저 `bash ./scripts/install.sh --check`를 실행합니다. Pi가 포함되면 관리 package가 설치·최신화된다는 점과 Pi CLI·Python 3 사전 조건을 확인합니다.
3. **Execution:** 선택된 에이전트를 인자로 하여 `bash ./scripts/install.sh <agents>`를 실행합니다.
4. **Verification:** 실행 결과와 심볼릭 링크, Pi 관리 package의 로컬 설치 상태를 확인합니다. 실제 extension 로딩 검증과 로컬 진단 결과를 구분하여 보고합니다.

---

## 📚 References

- [Gemini CLI Documentation](https://geminicli.com/docs/)
- [Claude Code Documentation](https://code.claude.com/docs/)
- [Pi Skills Documentation](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md)
- [Pi Packages Documentation](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/packages.md)
- [Pi Package Commands](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/cli.md#package-commands)
