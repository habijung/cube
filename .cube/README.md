# .cube/ — Runtime Output Directory

Cube 스킬(`cube-plan`, `cube-review`, `cube-summary`)이 타겟 프로젝트에 자동으로 생성하는 런타임 출력 디렉토리입니다. 멀티 에이전트 간 핸드오프와 세션 영속성을 위한 공유 저장소 역할을 합니다.

## 📂 Directory Layout

```text
.cube/
├── .gitignore          # Git 추적 정책 관리
├── plans/
│   ├── index.md        # 활성 계획 목록 (테이블)
│   └── <task-id>/      # 개별 계획 디렉토리
│       ├── plan.md     # 구현 계획서 (Phase/Task 체크리스트)
│       ├── context.md  # 프로젝트 컨텍스트 스냅샷
│       ├── progress.md # 진행 상황 추적
│       └── decisions.md# 의사결정 기록
├── review.md           # 코드 리뷰 결과 (gitignored)
└── summary.md          # 세션 요약 (gitignored)
```

## 🔒 Git Tracking Policy

`.cube/.gitignore`에 의해 내부적으로 관리됩니다.

| 항목           | 추적 여부     | 설명                                                    |
| :------------- | :-----------: | :------------------------------------------------------ |
| `plans/`       | ✅ Tracked    | 멀티 에이전트 핸드오프를 위한 영속 데이터               |
| `review.md`    | ❌ Ignored    | 리뷰 세션마다 재생성되는 임시 출력                      |
| `summary.md`   | ❌ Ignored    | 요약 세션마다 재생성되는 임시 출력                      |
| `.gitignore`   | ✅ Tracked    | 추적 정책 자체를 버전 관리                              |
| `README.md`    | ✅ Tracked    | 이 문서                                                 |

## 📋 Plans Structure

`plans/` 디렉토리는 `cube-plan` 스킬이 생성하고, `cube-plan-dev` 스킬이 로드하여 개발을 이어가는 구조입니다.

### index.md

모든 계획의 목록을 테이블로 관리합니다:

```markdown
| Task ID | Status | Branch | Created | Description |
```

### 개별 계획 디렉토리 (`<task-id>/`)

각 계획은 4개의 파일로 구성됩니다:

| 파일             | 역할                                                              |
| :--------------- | :---------------------------------------------------------------- |
| `plan.md`        | Phase별 Task 체크리스트를 포함한 구현 계획서                      |
| `context.md`     | Git 정보, 기술 스택, 아키텍처 등 프로젝트 컨텍스트 스냅샷        |
| `progress.md`    | 체크박스 기반 진행 상황 추적 및 요약                              |
| `decisions.md`   | 날짜, 결정 사항, 근거, 영향을 기록한 의사결정 로그               |

> 참고: `plans/example-agents-directory/`에 예시 문서가 포함되어 있습니다.

## 🎯 For Target Projects

Cube 스킬을 다른 프로젝트에서 사용하면 해당 프로젝트 루트에 `.cube/`가 자동 생성됩니다.

- `.cube/.gitignore`가 내부적으로 `review.md`와 `summary.md`를 ignore 처리하므로, **별도 설정 없이 `plans/`만 자동으로 추적**됩니다.
- 계획 추적이 불필요한 프로젝트라면, 프로젝트 루트 `.gitignore`에 `.cube/`를 추가하세요.

```gitignore
# 프로젝트 루트 .gitignore
.cube/
```

---

**Updated At:** 2026. 4. 9.
