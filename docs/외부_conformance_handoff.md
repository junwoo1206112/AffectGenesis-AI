# 외부 conformance handoff

공유 가능한 package는 `external_reproduction_handoff_manifest_v2.json`이 고정한 behavior fixture, 제출 template, CC BY 카드 권리 결정과 attribution 문서다. project card corpus, source tree, internal-only signal family, artifact는 이 handoff에 포함하지 않는다.

외부 구현자는 fixture의 여섯 행동 규칙을 독립 구현하고 submission template에 language/runtime, implementation·dependency·fixture SHA-256, 모든 case output을 기입한다. `behavioral_fixture_only:true`와 `project_card_corpus_received:false`는 필수다.

제출 후에는 local `submission`, `review`, `intake` 검증을 순서대로 사용한다. 이 과정의 통과는 behavior conformance의 자기진술 형식 검증일 뿐, 구현자의 독립성·환경·미수령 사실을 외부에서 검증한 결과는 아니다.
