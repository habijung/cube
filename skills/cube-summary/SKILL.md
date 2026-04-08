---
name: cube-summary
description: 현재 대화 세션의 진행 상황을 요약하고, 새 세션에서 컨텍스트를 복구할 수 있는 프롬프트를 생성합니다. trigger: /cube-summary, 요약해줘
argument-hint: "[--web]"
disable-model-invocation: false # Claude, User 모두 사용 가능
allowed-tools: Read, Write
compatibility: opencode, claude, gemini
---

# Session Summary Generator

사용자가 `/cube-summary`를 입력하면 이 스킬이 트리거됩니다.

## Instructions

언어를 `markdown`으로 지정한 단 하나의 코드 블록을 출력하세요. 이 블록은 두 가지 역할을 동시에 수행해야 합니다:

1. 사용자가 읽기 위한 세션 요약
2. 새 채팅 세션에서 컨텍스트를 복구하기 위한 프롬프트

대화 주제와 관계없이 아래의 표준 헤더(`##`) 형식을 사용하여 요약본을 작성하세요. 각 섹션 하단에는 필요에 따라 문단, 하위 헤더(`###`), 코드 블록, 표 등을 자유롭게 사용하여 상세한 기술적 정보를 포함할 수 있습니다.

### Standard Headings

요약본 작성 시 다음 5가지 기본 헤더를 반드시 사용하세요:

- `## 1. Core Goal`: 이 세션에서 달성하려는 핵심 목표에 대한 상세 설명.
- `## 2. Architecture & Key Context` (Optional): 기술적 설계, 데이터 파이프라인, 아키텍처 다이어그램 등 주요 컨텍스트 명시.
- `## 3. Current Status`: 완료된 작업(✅)과 진행 중/미완료 작업(⏳)을 명확히 구분.
- `## 4. Key Decisions & Constraints`: 세션 중 내려진 주요 결정 사항 및 반드시 준수해야 할 제약/규칙 기록.
- `## 5. Next Steps`: 다음에 수행할 작업 목록을 우선순위 순으로 작성.

### Dynamic Flexibility

세션의 특성에 따라 깊이 있는 기술적 세부 사항을 보존해야 할 경우, 위 표준 헤더 외에 추가적인 `##` 헤더(예: `## API Schema`, `## Database Design`)를 자유롭게 생성하여 포함할 수 있습니다.

### Constraints

블록 마지막에 반드시 다음 문장을 포함하세요:

> Context loaded. Please acknowledge this summary and let me know when you are ready to proceed with the Next Steps.

## Web Usage Guide

Gemini(Web), Claude.ai 등 슬래시 커맨드를 지원하지 않는 환경에서도 동일한 기능을 사용할 수 있습니다.

**설정 방법:**

1. 사용 중인 AI 서비스의 Custom Instructions(또는 System Prompt) 설정을 엽니다.
2. 아래 내용을 추가합니다. `<prefix>` 부분은 원하는 단어로 변경하세요. (예: `my-summary`, `dev-summary`)

   ````text
   When I input `<prefix>-summary`, output a SINGLE Markdown code block serving as BOTH a mid-session summary AND a context recovery prompt. Summarize clearly using Markdown headings (##):

   - ## 1. Core Goal: Detailed description of the main objective.
   - ## 2. Architecture & Key Context (Optional): Explicitly capture technical designs, data pipelines, etc.
   - ## 3. Current Status: Use ✅ for completed and ⏳ for pending tasks.
   - ## 4. Key Decisions & Constraints: Document important decisions and rules.
   - ## 5. Next Steps: Prioritized list of the next actions.

   You may generate additional ## headings (e.g., ## API Schema) if the context
   requires preserving deep technical details. Use paragraphs, sub-headings (###),
   code blocks, and tables as needed.

   End the block with:
   "Context loaded. Please acknowledge this summary and let me know when you are ready to proceed with the Next Steps."

   Wrap everything in one ```markdown``` block.
   ````

3. Custom Instructions에 추가한 뒤, 대화 중 `<prefix>-summary`를 입력하면 작동합니다.

## Guidelines

- 출력은 반드시 **언어를 `markdown`으로 지정한 단 하나의 코드 블록**이어야 합니다. 블록 외부에 추가 텍스트를 출력하지 마세요.
- 표준 헤더의 순서를 지키되, 필요에 따라 유연하게 내용을 확장하세요.
- 간결함보다는 **컨텍스트의 완전한 복구**를 최우선으로 하여 충분한 정보를 포함하세요.

---

**Updated At:** 2026. 4. 9.
