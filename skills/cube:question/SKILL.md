---
name: cube:question
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

1. 각 주제마다 별도의 Explore agent를 background로 실행
2. 모든 agent를 parallel로 실행
3. 결과를 종합해서 보고

실행 예시:

```
- Task 사용
- subagent_type: "Explore"
- run_in_background: true
- 모든 Task를 단일 메세지에서 병렬 호출
```

## Guidelines

- **주의:** 질의 응답 과정에서 파일 내용을 읽을 수는 있지만(Read 도구 등 활용), 어떤 코드도 수정(Write/Replace 도구 등 활용)해서는 안 됩니다.
- 항상 사용자에게 가장 도움이 되는 정확한 문맥을 바탕으로 답변하세요.

---
**Updated At:** 2026. 4. 3.
