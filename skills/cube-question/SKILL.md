---
name: cube-question
description: 코드에 대한 질문을 하면 그에 대한 답을 설명합니다. 코드를 수정하지 않습니다.
argument-hint: "[질문1] [질문2] [질문3] ..."
disable-model-invocation: false # Claude, User 모두 사용 가능
allowed-tools: Task, Read
compatibility: opencode, claude, gemini
---

# 질의 응답 스킬

사용자가 코드나 프로젝트에 대한 질문을 하면, 그에 대한 답을 조사하고 설명할 때 사용합니다. 질문에 답하기 위한 목적이므로 절대 코드를 수정하지 않습니다.

## Instructions

사용자가 요청한 질문을 다음과 같이 조사하고 답변하세요:

- **Investigation Strategy:** 여러 질문(주제)이 주어졌을 경우, 각 환경에서 제공하는 자체 서브 에이전트(예: Gemini의 `generalist`, Claude의 `Task/Explore` 등) 또는 탐색 도구를 백그라운드(Background) 혹은 병렬(Parallel)로 실행하여 정보를 수집합니다.
- **Consolidated Reporting:** 수집된 결과를 종합하여 한 번에 사용자에게 보고합니다.

## Guidelines

- **Modification Block:** 질의 응답 과정에서 파일 내용을 읽을 수는 있지만(Read 도구 등 활용), 어떤 코드도 수정(Write/Replace 도구 등 활용)해서는 안 됩니다.
- **Context Awareness:** 항상 사용자에게 가장 도움이 되는 정확한 문맥을 바탕으로 답변하세요.

---
**Updated At:** 2026. 4. 5.
