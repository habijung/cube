---
name: cube-summary
description: 현재 대화 세션의 진행 상황을 요약하고, 새 세션에서 컨텍스트를 복구할 수 있는 프롬프트를 생성합니다.
argument-hint: ""
disable-model-invocation: false # Claude, User 모두 사용 가능
allowed-tools: None
compatibility: claude
---

# Session Summary Generator

사용자가 `/cube:summary`를 입력하면 이 스킬이 트리거됩니다.

## Instructions

언어를 `markdown`으로 지정한 단 하나의 코드 블록을 출력하세요. 이 블록은 두 가지 역할을 동시에 수행해야 합니다:
1. 사용자가 읽기 위한 세션 요약
2. 새 채팅 세션에서 컨텍스트를 복구하기 위한 프롬프트

대화 주제와 관계없이 아래 5가지 항목을 빠짐없이 작성하세요:

1. **Core Goal** — 이 세션에서 달성하려는 핵심 목표
2. **Current Status** — 완료된 작업(✅)과 진행 중/미완료 작업(⏳) 구분
3. **Key Decisions** — 세션 중 내려진 주요 결정 사항
4. **Limitations / Constraints** — 작업 시 지켜야 할 제약 사항
5. **Next Steps** — 다음에 수행할 작업 목록 (우선순위 순)

블록 마지막에 반드시 다음 문장을 포함하세요:

> Context loaded. Please acknowledge this summary and let me know when you are ready to proceed with the Next Steps.

## Web Usage Guide

Gemini(Web), Claude.ai 등 슬래시 커맨드를 지원하지 않는 환경에서도 동일한 기능을 사용할 수 있습니다.

**설정 방법:**

1. 사용 중인 AI 서비스의 Custom Instructions(또는 System Prompt) 설정을 엽니다.
2. 아래 내용을 추가합니다. `<prefix>` 부분은 원하는 단어로 변경하세요. (예: `my:summary`, `dev:summary`)

```
When I input `<prefix>:summary`, output a SINGLE Markdown code block. This output
MUST serve as BOTH a mid-session summary for me to read, AND a context recovery
prompt for a new chat session. Regardless of the conversation topic, summarize
the following clearly:

1. Core Goal
2. Current Status (use ✅ for done, ⏳ for pending)
3. Key Decisions
4. Limitations / Constraints
5. Next Steps

End the block with:
"Context loaded. Please acknowledge this summary and let me know when you are ready to proceed with the Next Steps."

Wrap everything in one ```markdown``` block.
```

3. Custom Instructions에 추가한 뒤, 대화 중 `<prefix>:summary`를 입력하면 작동합니다.

## Guidelines

- 출력은 반드시 **언어를 `markdown`으로 지정한 단 하나의 코드 블록**이어야 합니다. 블록 외부에 추가 텍스트를 출력하지 마세요.
- 항목을 생략하거나 순서를 바꾸지 마세요.
- 간결하고 명확하게 작성하되, 다음 세션에서 컨텍스트를 완전히 복구할 수 있을 만큼 충분한 정보를 포함하세요.

---
**Updated At:** 2026. 4. 3.
