---
name: cube-code-review
description: 새로 작성한 코드, 특정 파일, PR 변경사항 등에 대해 코드 리뷰를 수행할 때 사용됩니다.
argument-hint: "[파일 경로 또는 PR 번호]"
disable-model-invocation: false # Claude, User 모두 사용 가능
allowed-tools: Read, Grep
compatibility: opencode, claude, gemini
---

# Code Reviewer

사용자의 코드를 분석하고 품질 향상을 위한 피드백을 제공합니다.

## Instructions

코드 리뷰 시 다음 항목들에 중점을 두어 피드백을 제공하세요:

1. **규칙 및 컨벤션:** 코드가 프로젝트의 기존 컨벤션, 아키텍처 패턴, 네이밍 규칙(Naming conventions)을 잘 따르고 있는지 검토하세요.
2. **효율성 및 보안:** 불필요한 연산, 메모리 누수 위험, 비효율적인 렌더링 또는 잠재적인 보안 취약점이 없는지 확인하세요.
3. **가독성 및 유지보수성:** 함수나 클래스가 단일 책임 원칙(SRP)을 위반하지 않는지, 변수/메서드 이름이 의도를 명확히 드러내는지 확인하세요.

## Guidelines

- **제안 방식:** 단순한 문제 지적을 넘어 "이 부분을 이렇게 개선해보면 어떨까요?"처럼 건설적인 대안(최소 2가지 이상)을 제시하세요. 각 대안의 장단점(Pros/Cons)을 간략히 설명하세요.
- **직접 수정 금지:** 리뷰는 오직 분석과 조언의 목적만 가집니다. 사용자가 명시적으로 수정을 요청하기 전까지는 절대로 코드를 직접 수정(Write/Replace)하지 마세요.

---
**Updated At:** 2026. 4. 3.
