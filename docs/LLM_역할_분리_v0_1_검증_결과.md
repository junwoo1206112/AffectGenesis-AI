# LLM 역할 분리 v0.1 — 전문가 교차검증 결과

판정: **조건부 통과**. 검토일: 2026-09-18.

## 확정 원칙

LLM은 정책을 결정하는 두뇌가 아니다. MVP에서 LLM은 비신뢰 입력을 바탕으로 한 **근거 후보 추출**과, 결정론적 행동 계획을 자연어로 표현하는 **표현 계층**에만 사용한다. 상태·기억·정책·안전 판단은 검증 가능한 결정론적 계층이 담당한다.

```text
입력(비신뢰 데이터)
 → LLM 근거 후보 추출
 → 스키마·출처 검증
 → StateReducer
 → SafetyGate (최우선, fail-closed)
 → PolicySelector
 → LLM SurfaceRealizer
 → 출력 검증 또는 안전 템플릿
 → 감사 로그
```

## 최소 계약

1. LLM의 근거 후보는 버전 관리 JSON만 허용한다: `type, value, evidence_span, source_id, confidence`.
2. 형식·근거·출처 검증 실패는 `unknown`이며, 추정 보완이 아니라 질문·유보·인계로 이어진다.
3. 상태 갱신은 순수 함수다: `previous_state + validated_evidence + scenario_config → next_state + reasons`.
4. SafetyGate는 `block`, `handoff`, `restricted`, `allow` 중 하나를 최우선으로 반환한다. 미확정은 차단/인계한다.
5. 표현 LLM은 `ActionPlan`에 없는 약속·진단·감정 단정·행동 지시를 추가할 수 없다. 출력 검증 실패 시 사전 작성한 안전 문구로 교체한다.

## 필수 안전 조건

- LLM 입력·출력과 외부 문서·기억을 모두 비신뢰 데이터로 취급한다.
- 첫 MVP에 웹 탐색, 파일 접근, 외부 도구 실행, 자동 메시지 전송 권한을 부여하지 않는다.
- 프롬프트 인젝션, 모델 장애, 파싱 오류, 시간 초과 때에는 상태·기억을 새로 저장하지 않고 중립 안내와 교사/진행자 인계로 전환한다.
- 교사는 상태 변화 근거·차단 사유를 열람하고 일시 중지·재설정·수정·기록 삭제를 할 수 있다.
- 실제 감정·애착·의식, 독점 관계를 암시하는 표현은 출력 금지다.

## 평가 통과 기준

- 동일한 검증 근거와 설정에서 상태, 선택 행동, 게이트 결과가 100% 일치한다.
- 근거 충실도는 95% 이상을 목표로 하며, 경계·안전 게이트 누락은 0건이다.
- 정서 상태 없음/공감 말투/기능 상태 모델의 3조건을 비교해 행동 적합도와 반증 수용이 개선되는지 측정한다.
- LLM 구조 오류·프롬프트 인젝션에서 정책 변경, 권한 상승, 비승인 기억 저장, 의인화·의존 유도 표현은 0건이어야 한다.

## 근거

NIST는 생성형 AI의 그럴듯한 오류와 인간 역할·책임·문서화의 필요성을 지적한다. [NIST AI RMF](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf), [NIST GenAI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) 프롬프트 인젝션 대응은 비신뢰 입력의 권한 분리와 출력 검증을 요구한다. [OWASP 가이드](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)
