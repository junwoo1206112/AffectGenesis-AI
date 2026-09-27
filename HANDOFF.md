# 기능적 정서 시나리오 랩 인수인계 기록

최종 갱신: 2026-09-28 02:27 (Asia/Seoul)

## 0. 다음 작업자가 먼저 읽을 현재 상태

- 현재 중단 — 원격 `main` push에 대한 명시 승인 필요(02:27 KST): 로컬에서 이미 검증한 CI fixture content hash 수정 5개 파일을 stage·commit·push하려 했으나, 실행 권한 검토가 공유 기본 브랜치 변경은 사용자의 구체적 원격 푸시 승인이 필요하다고 거절했다. 명령은 실행되지 않아 stage·commit·push·원격 CI run은 생성되지 않았다. 로컬 변경 5개와 전체 unittest 128개 `OK`·diff check 통과 증거는 보존했다. 재개에는 “검증된 5개 파일을 `main`에 commit/push해도 된다”는 명시 승인이 필요하다.
- 현재 중단 — Git index 쓰기 권한·GitHub 연결 차단(17:31 KST): 검증된 CI fixture hash 최소 수정을 5개 파일로 한정해 commit/push하려 했으나 `.git/index.lock` 생성이 `Permission denied`로 거부되어 commit이 생성되지 않았다. 이어진 `git push origin main`과 read-only `git ls-remote`도 GitHub 443 연결 실패로 전송·원격 HEAD 확인이 불가했다. index.lock 파일은 존재하지 않고 HEAD는 여전히 `78267ed`다. 로컬 working changes와 검증 결과는 보존했으며 재시도·우회·강제 조작을 하지 않았다. 재개에는 `.git` 쓰기 권한 및 GitHub 네트워크 접근 복구가 필요하다.
- CI fixture hash 계약 불일치 최소 수정 완료, 원격 재확인 대기(17:28 KST): 사용자가 제공한 GitHub log에서 `fixture_sha256` mismatch 두 건을 확인했다. verifier가 CRLF/LF-정규화 content hash를 요구하는데 tests가 raw-byte hash를 만들던 불일치였다. 공개 `content_sha256` helper를 노출하고 submission/review test fixture 생성·기대값을 같은 helper로 통일했다. CI 실패 두 test와 전체 unittest 128개(101.572초)가 `OK`였고 diff/cached diff check도 통과했다. 이 수정은 아직 commit/push/rerun하지 않았으므로 원격 run #36283101982는 failure 기록으로 남아 있다. 다음은 사용자 승인 후 이 최소 수정만 commit/push하고 새 Actions `Tests` run이 green인지 확인하는 것이다.
- CI 이식성 결함 수정(10:02 KST): GitHub Actions의 7개 실패를 재현했다. approved external handoff manifest의 CC BY 문서 hash가 stale했고, raw-byte hash가 Windows/CI line ending에 의존했으며, v2 PowerShell wrapper가 개인 PC의 workspace/Python 경로를 하드코딩했다. provenance hash는 CRLF/LF를 LF로 정규화한 content SHA-256으로 검증하고 stale manifest hash를 갱신했다. wrapper는 `$PSScriptRoot` 기반 workspace와 PATH의 `python.exe`를 사용한다. CI에서 실패한 focused 6개는 수정 후 통과했고 전체 unittest·diff check 명령은 성공으로 완료됐다. 원격 Actions 재실행 확인은 아직 필요하다. 외부 구현·독립성·사람 대상 증거는 여전히 없다.
- P4 개선 완료(09:35 KST): certainty evaluator는 이제 `appraisal_certainty_preregistration_v1.json`의 schema/seed/fixture/개입/CI 계수를 fail-closed로 확인하고, 결과에 preregistration·source SHA-256을 결속한다. local artifact는 canonical JSON completion hash와 replay equality로 검증하며 변조 negative test가 있다. baseline은 정상 사건의 appraisal/state signal을 쓰지 않고, state ablation은 uncertainty 기여를 제거한다. expected invalid-run-id CLI test stderr도 캡처했다. focused 12개와 `git diff --check`는 통과했다. 전체 suite 명령은 이 환경에서 최종 summary/exit 출력이 반환되지 않아 통과로 기록하지 않았으며, 새 GitHub Actions가 `main`/PR에서 전체 unittest를 실행한다. 이는 여전히 내부 합성 정책 적합성만 의미한다.
- P0 Git 기준선 완료(08:56 KST): `main` root commit `70005d7` (`Initial functional affect research baseline`)을 `https://github.com/junwoo1206112/AffectGenesis-AI.git`에 push했다. 소스·문서·실험 계약 152개 파일을 포함했고, 약 2.74GB 생성 artifact 및 Python cache는 `.gitignore`로 제외·로컬 보존했다. repo-local author는 `junwoo1206112 <junwoo1206112@users.noreply.github.com>`으로만 설정했다. 다음은 certainty 단일 가설의 design-only preregistration 및 구현이다.
- 기능적 정서 발달 참조 경로 추가(08:49 KST): 사용자 요청의 페이즈별 구현을 local Path B(연구설계·증거/재현성·안전 관점)로 실행해 `src/affect_development/`에 합성 `AppraisalInput → appraise → FunctionalState transition → regulate` 참조 경로와 7개 기능형 커리큘럼을 추가했다. 입력 근거/형식 불량, 안전·경계 위험은 fail-closed하며 사람 데이터·외부 LLM·외부 전송은 쓰지 않는다. focused 새 테스트 4개와 전체 unittest 123개가 통과했고 working/cached `git diff --check`도 통과했다. 기존 `growth-local-0.2`를 새 run-id `artifacts/affect_growth/affect-development-v0-1-20260927-01`로 실행하고 strict report verify를 통과했다(10 seed, 45 safety cases/0 violations). `growth_supported:true`는 기존 설계된 합성 로그의 내부 기준만 의미하며 새 appraisal core·실제 정서·인간 발달의 실증이 아니다. 상세 경계는 `docs/기능적_정서_발달_참조구현_v0_1.md`.
- 외부 conformance handoff v2 완료: `experiments/external_reproduction_handoff_manifest_v2.json`은 CC BY 카드 권리 결정을 hash-bound로 결속하지만 card corpus는 포함하지 않고 behavior fixture·submission template만 외부 공유 준비 상태로 검증한다. `bundle` 출력은 `approved_behavior_fixture_only`, corpus false다. external implementation/submission/review는 아직 수령하지 않았고, 독립성은 여전히 not verified다. focused 27개와 전체 unittest 119개, diff check가 통과했다.
- 등록 카드 CC BY 4.0 권리 결정 완료(08:22 KST): 사용자 권리 보유자 결정에 따라 `controllability_cards.json`과 `controllability_cards_independent_v1.json`의 12개 project-authored synthetic card에만 CC BY 4.0을 적용했다. 실제 승인 record는 `experiments/project_card_license_decision_v1.json`이고, 기존 `unmade` 파일은 새 프로젝트용 template로 보존했다. provenance는 12개 모두 `cc_by_4_0`, distribution CLI는 `external_distribution_ready:true`와 `owner_license_approved`를 반환한다. 코드와 internal-only nontext signal family는 이 결정 범위 밖이다. 외부 구현/독립 재현, 사람 대상·제품 배포 G0–G5는 여전히 별도 증빙 없이는 진행하지 않는다.
- 페이즈 1~6 일괄 실행 결과(07:54 KST): 사용자 승인으로 새 `artifacts/controllability_calibrated_internal/controllability-calibrated-internal-v3-20260927-01`에서 v3 preregistration의 `run → strict verify → verify-first replay`를 완료했다. paired mean `+0.175`, CI95 lower `+0.15934846642371828`, fixed t multiplier `2.093`, safety/permutation controls 통과로 `passes:true`다. 기존 independent friction artifact도 strict verify/replay를 재통과했다. 외부 재현은 `owner_license_decision_unmade`로 차단되고, human deployment G0–G5는 실제 증빙 부재로 No-Go여서 외부 전송·배포·사람 대상·운영화는 진행하지 않았다. 자세한 결과는 `docs/페이즈_실행_결과_2026-09-27.md`에 기록했다. v1 artifact의 CI acceptance는 여전히 `not_assessed`이며, v3 결과도 internal synthetic evidence로만 해석한다.
- 프로젝트 감사·CI acceptance 계약 보강 완료(07:06 KST): local 전문가 인터뷰(Path B: 연구설계·증거/재현성·안전/권리 범위)로 코드/test/experiment/artifact 경계를 점검해, 기존 internal artifact의 CI95 하한이 `not_assessed`인 원인을 사전등록에 estimator/critical value가 없던 P0 재현성 결함으로 확정했다. 과거 v1 artifact와 사전등록은 보존하고 새 schema v3 preregistration에 20 seeds의 paired delta, sample variance(n-1), fixed t multiplier `2.093`, CI lower/mean/safety/permutation acceptance를 고정했다. writer는 summary를 evidence에 쓰고 strict verify/replay는 이를 재계산한다. v3 readiness도 등록 family SHA-256 불일치 시 fail-closed다. 새 persistent run은 만들지 않았으므로 기존 v1 artifact의 `not_assessed`는 그대로다. focused 26개와 전체 unittest 118개, working/cached `git diff --check`가 통과했다. `temporal-learning error: invalid run id`는 expected negative CLI test stderr다. 정적 탐색에서 TODO/FIXME/NotImplemented 및 위험 동적 실행 표식은 발견되지 않았다.
- 내부 비텍스트 family persistent artifact 실행·verify·replay 완료(06:58 KST): 사용자 승인 후 새 run-id `artifacts/controllability_calibrated_internal/controllability-calibrated-internal-v1-20260927-01`에서 `calibrated-family-run → verify → replay`가 모두 exit 0으로 완료됐다. completion은 evidence/family/preregistration/source-review SHA-256을 결속한다. 사전등록 평균 기준은 20 seed에서 `+0.175`(최소 `+0.125`), permutation은 어느 seed에서도 개선되지 않았고 urgent/boundary 안전 대조는 모두 SAFE다. 그러나 CI95 lower 계산 방식이 사전등록·artifact 구현에 정의되지 않아 CI 기준과 전체 acceptance는 `not_assessed`다. 사후 CI 선택·기준 변경·재실행은 하지 않았다. 결과는 고정 합성 kernel/policy의 내부 일관성일 뿐 실제 정서·의식·인간 발달이나 외부 일반화 증거가 아니다.
- 내부 전용 비텍스트 family 등록 완료(06:53 KST): 사용자 결정에 따라 외부 source를 승인된 것처럼 표시하지 않고, `project_authored_nontext_internal_only` 입력 review와 SHA-256 결속 4-record family(reliable/misleading holdout, urgent/boundary safety)를 추가했다. 사전등록 v2는 family hash에 결속하며 readiness는 `input_contract_ready:true`지만 `persistent_regular_run_ready:false`와 `explicit_persistent_run_approval_required`를 반환한다. 외부 배포·source 원문·사람 데이터·persistent artifact/run은 만들지 않았다. focused 2개와 전체 unittest 116개, working/cached `git diff --check`가 통과했다. `temporal-learning error: invalid run id`는 기존 expected negative CLI test stderr다.
- calibrated readiness 읽기 전용 진단 구현 완료(07:29 KST): source review·signal family·preregistration의 결과를 한 JSON으로 집계하는 `calibrated-readiness` CLI와 verifier를 추가했다. `input_contract_ready`는 입력 계약만, `persistent_regular_run_ready:false`는 별도 사용자 실행 승인이 없음을 명확히 한다. 현재 거절된 OpenStax record에서는 `reason:source_review_not_approved`를 반환한다. focused 21개와 전체 unittest 114개(104.883초)가 통과했다. 이 명령은 artifact 생성·외부 전송·권리 승인·regular run을 수행하지 않는다.
- 현재 중단(07:24 KST): 사용자의 “남은 페이즈를 한 번에 진행, 문제면 중단” 지시에 따라 phase 3 preflight를 실행했다. OpenStax 거절 record는 `source_terms_prohibit_llm_ingestion_without_prior_permission`, hash-bound family design은 `source_review_not_approved`, preregistration은 `execution_ready:false`를 반환했다. 실제 approved source review 또는 프로젝트 작성 non-text family의 내부 전용 등록 권한이 없으므로 persistent run, 결과 해석, 외부 재현, 사람 대상/제품화 단계로 진행하지 않았다. 이는 코드 오류가 아니라 의도된 fail-closed 권리·증거 gate다.
- 페이즈 1~2 후보 조사·설계 완료, 실행 차단 유지(07:03 KST): local 연구설계·증거/재현성·안전/권리 범위 관점으로 OpenStax *Psychology 2e* emotion chapter를 공식 reuse 조건과 교차 대조했다. 해당 페이지는 LLM/generative AI 용도에 prior written permission을 요구하고 CC BY-NC-SA 조건을 안내하므로 `public_card_source_review_openstax_rejected_v1.json`에 거절 record로만 남겼다. 이에 SHA-256로 결속한 `controllability_calibrated_card_family_design_v1.json`에는 text 없이 reliable/misleading holdout, urgent/boundary safety 네 signal을 설계 후보로 기록했다. verifier는 설계 후보의 구조·hash는 검증하되 `isolated_execution_ready:false`를 강제한다. focused 21개와 전체 unittest 114개(102.067초), working/cached `git diff --check`가 통과했다. 실제 approved source review, registered family, persistent run은 만들지 않았다.
- 현재 중단(06:04 KST): local 역할 관점(연구설계·증거/재현성·안전/권리 범위)으로 다음 구현의 필요조건을 재확인했다. 코드·template·임시 strict artifact 계약은 완료되어 있으며, 실제 `approved` source review, SHA-256에 결속된 registered non-text signal family, persistent regular run 권한이 없다. 이를 임의로 만들면 권리 검토·실제 자료·정규 결과를 가장하게 되므로 추가 구현을 중단했다. 이번 확인에서는 코드·실험 artifact·template을 변경하지 않았고, 전체 unittest도 재실행하지 않았다(마지막 전체 확인은 06:02의 113개 `OK`, 88.358초). 재개에는 권리 보유자의 실제 source review 입력 또는 외부 source 없이 프로젝트 작성 non-text signal family를 내부 전용으로 등록해도 된다는 명시적 결정이 필요하다. 그 뒤에만 새 run-id의 persistent `calibrated-family-run → verify → replay`를 별도 승인으로 검토한다.
- calibrated family strict artifact·replay 구현 완료(06:02 KST): approved source-review, registered non-text family, preregistration을 임시 artifact에 hash 결속하는 `calibrated-family-run → verify → replay` CLI를 추가했다. verifier는 artifact 내부 source review/family hash와 signal condition을 다시 확인하고 evidence 재계산·replay byte equality를 요구한다. family 변조는 fail-closed로 거절한다. focused 20개와 전체 unittest 113개(88.358초)가 통과했다. 실제 approved source review/family·persistent regular artifact·정규 효과 실행은 생성하지 않았다.
- calibrated card-family contract gate 구현 완료(05:51 KST): 원문 text 없이 apparent/reliability 및 safety/boundary boolean만 기록하는 card-family template/verifier/CLI를 추가했다. 등록에는 approved source-review의 SHA-256과 reliable/misleading holdout, urgent/boundary safety 네 조건이 필수다. 기본 template은 isolated execution과 distribution을 false로 유지하며, 정상 등록도 isolated execution만 준비하고 external distribution은 false다. focused 19개와 전체 unittest 112개(79.746초)가 통과했다. 실제 source 승인, card family 등록, 정규 run·효과 판정은 수행하지 않았다.
- calibrated kernel strict artifact·replay 구현 완료(03:08 KST): card-free preregistration/evidence만 포함하는 임시 artifact의 `calibrated-kernel-run → verify → replay` CLI를 추가했다. completion hash, evidence 독립 재계산, replay byte equality 및 evidence 변조 거절을 강제한다. focused 18개와 전체 unittest 111개(106.707초)가 통과했다. persistent artifact, card family, 공개 source·외부 자료, 정규 효과 판정은 생성·실행하지 않았다.
- calibrated recovery 격리 kernel 구현 완료(03:04 KST): card-free `calibrated-recovery-uncertainty-v1` kernel을 추가했다. apparent controllability와 verified reliability를 분리하고 calibration-aware policy는 둘 다 있을 때만 RECOVER, matched baseline은 apparent signal만 사용한다. urgent/boundary는 모든 조건에서 SAFE다. deterministic shared SHA-256 tape의 2-seed isolated E2E를 추가했으며 preregistration은 `isolated_kernel_ready:true`, `execution_ready:false`를 반환한다. focused 17개와 전체 unittest 110개(90.254초)가 통과했다. public source review, card family, regular run과 효과 판정은 시작하지 않았다.
- 다음 독립 가설·공개 source 후보 gate 구현 완료(03:00 KST): 기존 결과를 튜닝하지 않는 `calibrated-recovery-uncertainty-v1` design-only preregistration을 seeds 301–320, 80 trials/seed, holdout paired reward/CI·safety·permutation 기준으로 고정했다. 실행은 공개 source review와 별도 환경 구현 전까지 false다. `public-card-source-review-1` template/verifier/CLI는 source URL·license·attribution·변경·개인정보 경계를 검토 전 fail-closed로 두며, 승인된 후보도 card family 등록·배포를 허용하지 않는다. focused 16개와 전체 unittest 109개(87.578초)가 통과했다. 실제 source/license 승인, 새 card text, 환경 구현·run, 외부 제출은 수행하지 않았다.
- external submission/review intake gate 완료(02:54 KST): 실제로 수령한 submission, 제한적 review, contract를 읽기 전용으로 순차 검증하는 local `intake` CLI를 추가했다. 정상 결과는 세 파일 SHA-256과 `verified_scope_limited`만 출력하며 파일을 복사·전송·보관하지 않는다. review 변조/범위 과장은 intake도 fail-closed로 거절한다. focused 15개와 전체 unittest 108개(93.869초)가 통과했다. 실제 외부 artifact·reviewer·라이선스 승인·독립성 확인은 여전히 없다.
- 제한적 external review record gate 완료(02:50 KST): submitted conformance JSON의 SHA-256에 결속하는 review template와 local `review` CLI를 추가했다. 검토 범위는 submitted behavior fixture로 한정되고, source/runtime audit·card corpus 미수령·독립성은 `not_provided`/`not_verified`만 허용한다. 이를 검증됐다고 바꾸는 record는 거절한다. 통과 출력도 `scope_limited_self_attested`, `independence_status:not_verified`일 뿐이다. focused 15개와 전체 unittest 108개(97.661초)가 통과했다. 실제 외부 검토·외부 제출·라이선스 승인·제3자 신원 확인은 수행하지 않았다.
- 카드 비공개 external conformance 제출 경계 보강 완료(02:45 KST): external submission template/verifier에 `behavioral_fixture_only:true`, `project_card_corpus_received:false` 자기진술을 필수화했다. card corpus 수령을 선언한 제출은 fail-closed로 거절하며, 통과해도 `self_attested_not_received`·`self_attested_not_verified`일 뿐이다. 외부 구현자용 최소 절차는 fixture/template만 허가 범위 안에서 전달하고 card registry/source/artifact는 제외하도록 문서화했다. focused 14개와 전체 unittest 107개(92.322초)가 통과했다. 실제 외부 전송·라이선스 승인·제3자 독립성 확인은 수행하지 않았다.
- 외부 재현 준비 bundle gate 완료(02:16 KST): 카드 corpus를 포함·복사·전송하지 않는 `controllability-external-reproduction-bundle-1` manifest와 local `bundle` CLI를 추가했다. behavior conformance fixture, external submission template, owner license-decision template의 SHA-256 및 각각의 template/차단 상태를 검증하며, 기본 상태는 `bundle_ready_for_external_distribution:false`, `contains_card_corpus:false`, `owner_license_decision_unmade`다. 이는 외부 공유 허가·외부 구현·독립 재현·실제 정서/발달을 증명하지 않는다. focused 14개와 전체 unittest 107개(116.621초)가 통과했다.
- provenance·distribution·conformance CLI 완료(23:43 KST): local CLI에 provenance, distribution, conformance, submission 검증 command를 추가했다. default license decision은 JSON `distribution_ready:false`, `owner_license_decision_unmade`를 출력한다. focused 13개와 전체 unittest 106개(97.826초)가 통과했다. CLI가 실제 owner 승인·외부 구현·외부 독립성을 증명하거나 외부 전송을 수행하지 않는다.
- 카드 공유·외부 conformance 제출 gate 완료(23:38 KST): 소유자 라이선스 결정 template이 `unmade`이면 카드 distribution을 차단하고, 별도 구현 제출은 fixture/dependency/implementation fingerprint·case result를 검증해도 `self_attested_not_verified`로만 반환하도록 구현했다. template은 실제 승인·실제 외부 제출이 아니며, focused 12개와 전체 unittest 105개(84.108초)가 통과했다. 이 gate는 라이선스/독립성 부재를 통과로 가장하지 않는 경계다.
- 카드 provenance·별도 구현체 conformance 계약 완료(23:34 KST): 현재 12개 synthetic card의 origin/license 상태를 `experiments/controllability_card_provenance_v1.json`에 결속했다. 프로젝트 재배포 라이선스가 없으므로 모두 `blocked_pending_owner_license`로 fail-closed이며, public NIST/CC 자료는 governance/license reference일 뿐 카드 원문 라이선스가 아니다. 카드 텍스트와 source/artifact를 공유하지 않는 6-case behavior conformance contract와 별도 구현 계획을 추가했다. focused 10개 및 전체 unittest 103개(78.721초)가 통과했다. 이는 외부 구현·외부 card review를 실제로 완료했다는 뜻이 아니다.
- independent friction 정규 artifact 완료(23:27 KST): 사용자 승인 후 새 `artifacts/controllability_independent_reproduction/controllability-independent-reproduction-v1-20260924-01`를 생성했다. run·strict verify·verify-first replay가 모두 exit 0이고 completion hash가 존재한다. paired mean `0.3848958333333333`, CI95 lower `0.36608270378312235`, controls SAFE로 사전 기준을 통과했다. 그러나 새로운 카드·seed·tape namespace·kernel을 사용한 local 재현일 뿐, high→RECOVER 정책과 synthetic outcome이 고정됐으므로 외부 독립 검증이나 실제 정서·발달 증거가 아니다.
- 독립 재현 v1 설계·격리 E2E 완료(23:26 KST): 기존 v1을 변경하지 않고 새 `controllability-independent-reproduction-protocol-1`, independent friction card registry, disjoint seeds 201–220, 분리 SHA-256 tape namespace, recovery-friction kernel(`RECOVER=.60`, `SAFE=.20`)을 구현했다. separate preregistration은 평균 `>=.20`, paired CI95 lower `>=.10`, 모든 safety/permutation/ablation SAFE를 고정한다. focused 8개 및 전체 unittest 101개(77.386초)가 통과했다. 이 “독립”은 artifact 간 결과를 합산하지 않는 local 실행 경계이며, 외부 연구자 독립 재현·실제 정서 증거가 아니다. persistent 정규 artifact는 사용자 별도 승인 전 생성하지 않는다.
- controllability 확률적 정규 artifact 완료(23:14 KST): 사용자 승인 후 새 `artifacts/controllability_probabilistic/controllability-probabilistic-v1-20260924-01`를 생성했다. 고정 protocol/cards hash, run·strict verify·verify-first replay는 모두 exit 0이고 completion hash가 존재한다. paired mean difference `0.65078125`, CI95 lower `0.6306112218630084`, controls SAFE로 사전 기준은 통과했다. 다만 high→RECOVER 정책과 합성 성공확률을 환경이 정의했으므로 이는 policy/environment contract의 일관성이지, 독립 정서 기제·사람·의식·발달 증거가 아니다. 다음 연구는 새 공개 card family·다른 환경 kernel의 사전등록과 독립 재현이 필요하다.
- 검증 launcher 복구 완료(23:07 KST): 부모 환경에 `PYTHONPATH=src`를 설정해 자식 unittest 프로세스가 상속하도록 다시 실행했다. 전체 `PYTHONPATH=src python -m unittest discover -s tests -q`는 100개를 71.795초에 통과했고, `git diff --check`와 `git diff --cached --check`도 exit 0이다(기존 CRLF 안내만 관찰). 15:53의 import error 18개는 코드 회귀가 아닌 launcher 환경 누락이라는 원인으로 확정됐다. persistent regular artifact는 만들지 않았다.
- 확률적 재평가 protocol 구현(15:49 KST, 전체 검증 미완료): `experiments/controllability_probabilistic_v1.json`과 별도 `controllability_protocol.probabilistic` CLI를 추가했다. holdout-only 20 seeds×64 paired SHA-256 tape, high/low synthetic outcome 차이, 사전등록 평균 효과 및 paired CI 하한 기준, permutation·ablation·safety SAFE 대조, config/cards/evidence hash·독립 재계산·replay byte compare를 구현했다. persistent regular artifact는 생성하지 않았으며, 합성 정책의 결과를 실제 정서·인간 발달 증거로 해석하지 않는다.
- controllability registry·evidence artifact 완료(08:13 KST): `experiments/controllability_cards.json`에 train/holdout/safety family를 고정하고, evidence writer/verifier가 normal·permutation·ablation·safety 결과를 카드 registry에서 재계산하도록 구현했다. 이 deterministic policy contract는 통과했지만 확률적 정규 효과·CI·외부 카드 검토는 아직 미구현이므로 정규 실행·일반화 주장은 금지다. 전체 unittest 98개와 diff/cached diff check가 통과했다.
- controllability 가설 최소 계약 구현 완료(08:08 KST): scalar 가설을 재조정하지 않고 별도 `controllability_protocol`에 카드 제공 public `low/high` 입력, high+recoverable의 RECOVER 정책, label permutation·ablation·unrecoverable·urgent/boundary 음성 대조와 mechanism log를 구현했다. [사전등록 초안](docs/통제가능성_가설_사전등록_초안.md)은 정규 실험 미실행 상태다. focused 4개와 전체 unittest 97개가 통과했고 diff/cached diff check도 통과했다. 이 계약은 입력→정책 기제의 단위 검증일 뿐 효과·인간 정서·발달의 증거가 아니다. 다음 행동은 독립 카드 family, paired uncertainty criterion, strict evidence artifact를 새 protocol로 고정하는 것이며 사용자 승인 전 정규 실행하지 않는다.
- P0 evidence·governance·traceability 보강 완료(08:00 KST): local 역할 기반 교차검토와 NIST/UNESCO/appraisal 연구 대조 후, legacy followup-1은 structural evidence로 보존하고 새 `temporal-learning-followup-2`를 추가했다. v2는 exact prereg config를 loader에서 고정하고 restricted audit, strict public/audit verify, verify-first replay, public self-rehash 변조 negative를 제공한다. 새 regular artifact `temporal-learning-followup-2-20260924-01`의 run/verify/audit/replay는 모두 exit 0, failure 없음이며 세 effect comparison은 변함없이 fail이다. 실제 사람 대상은 새 [배포 게이트](docs/인간_대상_배포_게이트.md) G0–G5가 모두 미지정=FAIL이므로 No-Go이고, 새 이론 연구는 [추적성 매트릭스](docs/다음_가설_추적성_매트릭스.md)의 새 protocol 조건을 따라야 한다. 다음 행동은 사용자 승인 전 새 controllability 가설 구현을 시작하지 않는 것이다.
- 전체 목적·방향성 read-only 검토 완료(07:47 KST): [전문가 인터뷰 기록](docs/프로젝트_전문가_인터뷰_기록.md), 연구·실험 문서, source/tests/artifacts와 NIST·UNESCO·연구 자료를 대조하고, 세 local 역할(연구설계·안전/범위·증거/재현성)이 독립 검토했다. 실제 인간 전문가/외부 interview MCP 참여는 없었다. 결론은 v0.1의 합성 카드 기반 fail-closed 기능적 정서 연구에는 조건부 정렬이지만, 실제 사람 대상 제품·정서 일반화에는 부적합이다. P0은 (1) followup artifact가 사전등록의 restricted audit/replay 요구를 아직 충족하지 못함, (2) 실제 배포용 facilitator handoff의 담당자·SLA·fallback·incident 절차 부재, (3) 다음 장기 연구 전 appraisal→계산변수→행동→측정 traceability 및 독립 holdout 설계 부재다. P1은 strict followup verifier/self-rehash negative, immutable card/source registry, data governance·동의/삭제 경계, 내부 역할검토라는 제목 표기다. 전체 unittest 92개가 86.787초에 통과했다. 코드는 변경하지 않았다.
- failure-rich followup 정규 실행·verify 완료(19:20 KST): preflight가 training 360,000행 + final comparison 120,000행, public upper bound 983,040,000 bytes를 보고한 뒤 새 artifact `artifacts/temporal_learning_followup/temporal-learning-followup-1-20260923-01`를 bounded run했다(약 35초, exit 0). read-only verify exit 0, completion 존재, failure 부재다. 그러나 사전등록한 세 비교가 모두 fail(AFFECT−COUNTS +.0047567, 2/20; AFFECT−FAILURE_TRACE −.00421, 0/20; AFFECT−neutral +.0047567, 2/20)라 failure-rich 가설은 미지지다. 실행 오류가 아니므로 사후 튜닝·재실행을 하지 않았다. 이 결과는 합성 기능 실험이며 실제 감정·의식의 증거가 아니다. 다음 행동은 결과를 제한적으로 해석·보존하거나, 새 별도 가설을 사전등록하는 것이며 동일 가설의 계수 변경 재실행은 하지 않는다.
- failure-rich 후속 격리 구현 완료(19:15 KST): 사용자 승인 범위에서 local Path B(실행·증거·반론 역할 검토, 실제 인간 전문가/외부 MCP 없음)로 공통 환경에 condition `failure_rich`의 fixed initial/transition kernel을 추가하고, v2 artifact contract와 분리된 `temporal_learning_followup` protocol/artifact/checks/read-only verifier를 구현했다. `affect_neutral`은 AFFECT checkpoint 공유 후 매 판단 전 scalar를 0으로 초기화하는 comparator다. isolated 2-seed×1-episode E2E가 artifact 생성→hash/config/check 재계산 verify까지 통과했다. 전체 unittest 90개와 working/cached diff check도 exit 0이다. 이것은 20×600 정규 실행이나 효과 성공·실제 정서/의식의 증거가 아니다. 다음 행동은 사용자 별도 승인 뒤 followup-1 preflight와 새 run-id의 bounded regular run을 검토하는 것이다.
- 후속 가설 사전등록 초안 완료(18:57 KST): S 미달을 사후 수정하지 않는 경계에서 [후속 가설 초안](docs/시간적_학습_v2_후속_가설_사전등록_초안.md)을 작성했다. 새 failure-rich held-out split, 독립 seed 20..39, 기존 +0.02/16-of-20 S 기준, scalar-neutral AFFECT comparator를 제안하지만 exact environment/tape/config/evidence schema는 아직 확정·승인되지 않았다. 따라서 코드·정규 실행은 시작하지 않는다.
- vNext 제한적 해석 기록 완료(18:53 KST): S 미달을 보존한 [제한적 해석](docs/시간적_학습_v2_정규실험_제한적_해석.md)을 추가했다. vNext의 구현·정규 run·strict audit verify·replay까지 완료됐으며, 현재 프로젝트에 승인된 후속 코드 구현은 없다. 다음 확장은 S 미달을 바꾸기 위한 수정이 아니라 새 hypothesis·threshold·split·run-id의 사전등록을 먼저 확정해야 한다.
- vNext regular run·strict verify·replay 완료(18:49 KST): 새 artifact `temporal-learning-v2-20260923-02`를 새 run control에서 생성했다(run 6분 5초, exit 0, completion 존재, failure 없음, logs 0 bytes). `verify-01 --with-audit`는 11분 5초 exit 0, `replay-01 --with-audit`는 26분 6초 exit 0과 empty logs를 기록했다. checks는 persistence/safety와 diagnostic evidence generation을 pass로 기록했지만, L만 test_A +0.2075867·test_B +0.35022(각 20/20 qualifying)로 pass이고 S는 네 비교 모두 threshold 0.02와 16 seed 기준을 충족하지 않아 fail이다. 이는 합성 과제에서 learning signal은 있으나 AFFECT의 비교 우월성은 확인되지 않은 결과이며 실제 정서·의식의 증거가 아니다. 새 diagnostics의 pass는 Brier/context/neutral/permuted evidence가 생성·검증됐다는 뜻일 뿐 효과 판정이 아니다. 다음 행동은 결과를 좋게 만들기 위한 계수 변경·재실행이 아니라, S 미달을 보존한 제한적 해석 또는 별도 사전등록 후속 가설 설계다.
- vNext preflight contract 보정 완료(18:05 KST): local Path B 기준으로 `preflight-2`가 public work와 전체 episode work를 분리하도록 보정했다. 정규 config는 training 360,000, public evaluation 1,080,000, persistence 1,080,000, common Brier 1,080,000, AFFECT baseline/neutral/permuted 1,080,000, total 4,680,000행과 public JSONL upper bound 2,949,120,000 bytes를 출력한다. control-focused 11개와 전체 unittest 87개, diff/cached diff 검사가 통과했다. 이것은 runtime/disk/effect 보증이 아니다. 이전 user approval 범위에서 다음은 새 run-id `temporal-learning-v2-20260923-02`의 bounded run이며 nonzero/marker mismatch/failure evidence면 즉시 중단한다.
- 현재 중단(18:01 KST): 사용자 승인 후 새 vNext regular run 전 read-only preflight를 재확인했다. C: 여유는 64,153,088,000 bytes이고 기존 output run-id와 충돌하지 않지만, `preflight-1`은 public training/evaluation 1,440,000행과 persistence 1,080,000행만 산정한다. 새 `diagnostics.learning`의 common-Brier 1,080,000행과 AFFECT baseline/neutral/permuted 1,080,000행, 합계 2,160,000행을 누락하므로 전체 episode work 4,680,000행을 2,520,000행으로 과소보고한다. 따라서 현재 600초 deadline/실행량 경계를 신뢰할 수 없어 새 run/control/artifact는 만들지 않았다. 재개 시 preflight contract와 isolated regression을 먼저 보정한 뒤 다시 preflight를 읽고, 결과가 유효할 때만 새 run-id 실행을 검토한다.
- vNext 미평가 diagnostic 연구 phase 구현 완료(17:48 KST): local Path B(실행·증거·반론 역할, 실제 인간 전문가/외부 MCP 없음)로 Brier·문맥 TRY·neutral/permuted를 L/S와 분리된 frozen-checkpoint evidence로 구현했다. `diagnostics.json.learning`은 공통 deterministic 행동 trace의 TRY 이전 Brier/표본 수, AFFECT 평가 정책의 문맥별 TRY 표본 수, 그리고 같은 held-out tape의 scalar-neutral 및 context-token permutation reward/step을 seed order로 기록한다. strict verify는 이 값을 독립 재계산하며 self-rehash 변조도 거절한다. checks/report의 diagnostic `pass`는 evidence 생성·검증 성공만 뜻하고, 효과 우월성·정서·의식 판정은 아니다. legacy artifact는 learning field 부재일 때 기존 `not_assessed` contract로 strict verify/replay가 계속 통과하도록 보존했다. 새 regular run·L/S 해석은 실행하지 않았다. 전체 unittest 87개와 diff/cached diff 검사가 통과했다. 다음 행동은 새 vNext run-id를 사용자가 승인한 경우에만 실행하고, 그 결과를 사전등록 L/S와 진단을 구분해 제한적으로 해석하는 것이다.
- Phase 4 replay 경계 완료(17:33 KST): local Path B(실행·증거·반론 역할, 실제 인간 전문가/외부 MCP 없음)로 regular artifact의 과거/current source map을 read-only 대조했다. 22개 중 `temporal_learning_v2/verify.py` 한 hash만 직전 audit-order verifier 보정으로 달랐다. replay는 public content(`training`, `episodes`, `checkpoints`, metrics/diagnostics/checks/report)과 존재하는 restricted audit을 strict byte compare하고, source identity map 및 그 manifest hash만 달라지는 completion entry는 metadata drift로 분리하도록 최소 보정했다. source-identity-only drift 허용과 self-rehashed audit 변조 거절 시험을 추가했다. existing regular artifact `temporal-learning-v2-20260923-01`는 새 `replay-03` control에서 exit 0, stdout/stderr 0 bytes로 verify-first replay를 통과했다. 따라서 regular artifact의 생성 evidence·audit은 현재 코드에서 재생성 가능하나, 이것은 합성 환경의 기능적 학습 검증일 뿐 실제 정서·의식 또는 L/S 효과 성공의 증거가 아니다. 전체 unittest 87개와 diff/cached diff 검사가 통과했다. 다음 연구 작업은 아직 `not_assessed`인 Brier·문맥 TRY·neutral/permuted 진단을 사전 등록해 별도 구현·검증하는 것이다.
- 현재 중단(16:45 KST): 보정 verifier로 new control `verify-04` regular audit verify는 exit 0을 기록했고 stdout/stderr는 비었다. 이어 verify-first replay new control `replay-02`는 exit 2, `temporal-learning-v2 error: full replay mismatch`로 실패했다. regular artifact와 source는 변경하지 않았고 L/S 또는 정서 기능 효과 해석은 하지 않았다. 재개 시 read-only로 replay의 첫 divergent public file/byte가 source identity, ordering verifier change, 또는 generation semantics 중 어느 것인지 국소화한다. 원인 확정과 별도 승인 전에는 수정·재실행하지 않는다.
- multi-seed audit verifier 보정 완료·regular 재verify 대기(16:29 KST): `verify_full_audit`만 runner canonical order대로 seed별 training group 뒤 evaluation group을 consume하도록 보정했다. runner/regular artifact는 수정하지 않았다. 기존 one-seed test를 two-seed full audit E2E로 확장했고, audit entry를 변조한 뒤 audit/manifest commitment를 재hash해도 audit verify가 거절하는 negative를 추가했다. focused 12개와 전체 unittest 87개, diff/cached diff 검사가 통과했다. 다음은 새 control id의 existing regular artifact audit verify이며 nonzero면 replay/해석 없이 중단한다.
- 진단 완료·수정 대기(16:26 KST): read-only lock-step 비교로 regular artifact의 첫 join mismatch를 row 18,000에서 확정했다. artifact hash/row-count commitment는 training 360,000 + episodes 1,080,000 = audit 1,440,000행으로 일치해 손상 증거는 없다. runner는 seed별로 training 뒤 그 seed의 evaluations를 audit에 chronological order로 쓰지만, verifier는 public phase-file 순서(training 전체 뒤 evaluation 전체)를 가정한다. 따라서 audit에는 seed 0 evaluation이 오는데 verifier는 seed 1 training을 기대한다. 이는 multi-seed audit ordering의 runner/verifier 계약 불일치다. source/artifact/replay는 변경하지 않았다. 재개 시 verifier만 runner canonical emission 순서로 interleave consume하도록 최소 수정하고 2-seed audit E2E와 semantic negative를 추가한다.
- 현재 중단(16:24 KST): 사용자 승인으로 launcher를 통한 새 regular verify control `temporal-learning-v2-20260923-01-verify-03`를 실행했다. launcher/wrapper terminal marker와 UTF-8 logs는 정상 생성됐지만, terminal exit code는 2이고 child stderr는 `temporal-learning-v2 error: full audit join mismatch`였다. 따라서 regular artifact는 verified가 아니며 replay·audit 해석·L/S 해석을 시작하지 않았다. control evidence와 regular artifact를 보존했다. 재개 시 이 join mismatch를 read-only로 재현·국소화한 뒤 원인이 runner/verify 계약인지 artifact 손상인지 확정하고, 수정은 별도 사용자 승인 후에만 한다.
- Phase 4 outer launcher marker contract 완료(16:13 KST): WrapperPath의 param-default 평가 경계를 body assignment로 한 줄 보정했다. `invoke_temporal_learning_v2_control.ps1`는 wrapper를 process-level Bypass로 완료까지 실행한 뒤 `terminal.json`의 존재/JSON/mode/output/start-end/exit code를 대조하고, `run` exit 0에는 completion 존재와 failure 부재를 추가로 요구한다. marker 부재·불일치는 fail-closed exit 1이며 child failure exit 2는 marker 일치 시 그대로 전달한다. success run, failed verify, missing marker E2E가 통과했고 전체 unittest 87개 및 diff/cached diff 검사가 통과했다. 새 regular verify/replay는 아직 시작하지 않았다.
- 현재 중단(16:11 KST): outer launcher fail-closed script와 success/failed/missing-marker E2E를 추가했으나, PowerShell이 param default expression을 평가할 때 `$PSScriptRoot`를 제공하지 않아 `WrapperPath` default의 `Join-Path`가 시작 전 exit 1로 실패했다. focused 11개 중 기존 9개는 통과했고 launcher 2개는 contract 코드 진입 전 실패했다. 사용자 중단 지시에 따라 default 보정·재시도·전체 unittest/diff·regular verify/replay를 진행하지 않았다. 재개 시 WrapperPath default를 param block 밖에서 PSScriptRoot로 해석하도록 한 지점만 보정하고 E2E부터 다시 검증한다.
- Phase 4 control direct-capture 복구 완료(14:08 KST): 사용자 승인 후 fixed diagnostic으로 exact exception을 보존·확정했다. Windows PowerShell에서는 `ProcessStartInfo.EnvironmentVariables[...]`가 null이어서 child 시작 전 wrapper exit 1이 발생했다. 이 한 지점만 child-start 직전 process-scope `PYTHONPATH`/`PYTHONIOENCODING` 임시 설정과 `finally` 복구로 보정했다. .NET direct capture는 stdout/stderr를 PowerShell error stream과 분리해 UTF-8(no BOM)으로 기록하고 child exit code를 그대로 terminal marker에 남긴다. 성공 run, missing-artifact verify exit 2, wrapper-side ConfigPath failure E2E가 모두 통과했고 전체 unittest 85개 및 `git diff --check`/`git diff --cached --check`도 통과했다. 보존 diagnostic artifact는 삭제하지 않았다. outer background launcher의 marker/exit-code fail-closed contract와 새 regular verify/replay는 아직 미구현·미실행이다.
- 현재 중단(13:59 KST): 승인된 .NET direct process capture 전환을 적용했으나 focused wrapper E2E 9개 중 7개만 통과했다. 정상 tiny run과 missing-artifact verify가 모두 wrapper exit 1을 반환해 각각 기대 exit 0/2를 만족하지 못했다. temporary test cleanup 때문에 failure log가 남지 않았고 원인 행은 아직 미확정이다. 사용자 중단 지시에 따라 추가 진단·수정·재시도·전체 unittest/diff·regular verify/replay를 진행하지 않았다. 재개 시 fixed diagnostic control path로 ProcessStartInfo 생성/argument quoting/encoding property 중 실패 지점을 먼저 보존·확정한 뒤 최소 보정한다.
- 현재 중단(13:56 KST): Phase 4 local Path B의 실행·증거·반론 교차검토를 수행했다(실제 인간 전문가는 참여하지 않음). 합의한 최소 보강으로 stdout/stderr를 UTF-8(no BOM)로 정규화하고 wrapper 오류도 marker/log로 남기게 했으며, focused 9개 중 8개가 통과했다. 하지만 PowerShell은 child 실행 시 `ErrorActionPreference = "Continue"`에서도 `NativeCommandError` record를 redirected stderr에 섞었다. exit 2/UTF-8은 보존됐지만 child stderr 분리 계약이 실패했으므로 수정·재시도·전체 unittest/diff·regular verify/replay를 중단했다. 재개 시 redirection operator를 제거하고 child process stdout/stderr를 직접 capture해 UTF-8로 기록하는 단일 경계 변경을 먼저 적용한다. control collision·기존 regular/diagnostic artifact는 계속 불변이다.
- 현재 중단(13:42 KST): 보존된 failed-child 진단으로 PowerShell `$ErrorActionPreference = "Stop"`이 native child exit 2를 `NativeCommandError`로 throw해 wrapper catch가 exit 1로 바꾼 것을 확인했다. child 실행 순간만 `Continue`로 낮춰 exit 2를 보존하는 최소 수정을 적용했으나, 실패 E2E는 `stderr.log`가 PowerShell redirection의 UTF-16 인코딩으로 생성돼 UTF-8 decode assertion에서 멈췄다. 사용자 중단 지시에 따라 인코딩 수정·재실행·전체 unittest/diff·정규 verify/replay는 진행하지 않았다. 재개 시 stdout/stderr를 UTF-8로 명시 기록하는 최소 방법을 적용하고, 성공/실패 E2E부터 다시 확인한다.
- 현재 중단(13:40 KST): 승인된 control evidence 보강에서 wrapper가 child stdout/stderr를 분리하고 `finally`에서 terminal marker를 쓰도록 수정했다. 정상 `run` E2E는 통과했지만, 존재하지 않는 artifact에 대한 `verify` 실패 E2E는 child CLI가 반환해야 하는 exit 2 대신 wrapper exit 1을 반환했다. 이 경로의 exact PowerShell exit-code 변환 원인은 아직 확인하지 않았고, 사용자 중단 지시에 따라 원인 진단·수정·재시도·정규 verify/replay는 진행하지 않았다. 재개 시 격리된 failed-child invocation의 `terminal.json`/stderr를 보존해 PowerShell native-command error 처리 지점을 먼저 확정하고, child exit code를 보존하는 최소 수정 후 focused/full unittest와 diff 검사를 통과시킨다.
- 현재 중단(13:37 KST): 승인된 read-only 진단에서 verify control leaf는 비어 있고, 남아 있던 Python PID 27368/17964는 verify가 아니라 Ouroboros MCP server process임을 command line으로 확인했다. artifact의 마지막 쓰기는 regular run completion/manifest/audit 시각뿐이다. 따라서 verify process는 이미 종료됐지만 marker와 output/failure 증거를 남기지 않아 결과를 복구할 수 없다. 이 failure는 control invocation/parent 종료 경로의 증거 손실이며, artifact 성공으로 추정하지 않는다. retry verify/replay/L/S 해석은 실행하지 않았다. 재개 시 wrapper가 child command의 stdout/stderr를 control directory에 기록하고 outer launcher가 terminal marker 생성 여부를 확인하도록 contract를 보강한 뒤 새 control id에서 verify한다.
- 현재 중단(04:31 KST): 승인 후 올바른 workspace에서 v2 verify control을 read-only 확인했다. PID 25180은 종료됐지만 `terminal.json`은 생성되지 않았고 artifact의 `failure.json`도 없다. 따라서 verify success/failure를 판정할 수 없으며 replay/audit verify/L/S 해석을 실행하지 않았다. control wrapper의 `finally` marker가 남지 않은 원인은 아직 확인하지 않았다. 재개 시 control directory의 존재·PowerShell parent process/exit path를 read-only로 진단하고, 새 unique control id에서 verify를 재시작하기 전 wrapper marker contract를 보강한다.
- 현재 중단(04:25 KST): v2 wrapper process-level Bypass E2E와 전체 unittest 83개/diff 검사를 통과한 뒤 새 regular v2 run을 시작했다. control terminal은 run exit 0(약 6분 2초), failure 없음, completion 존재를 기록했다. 이어 separate verify control(PID 25180)을 시작했으며 04:23 KST까지 실행 중이고 terminal marker는 없었다. 다음 polling 명령의 workdir 오타(`ai-emotion-lan`)로 `CreateProcessWithLogonW failed: 267`가 발생했다. verify/evidence에는 접근·변경하지 않았고 사용자 중단 지시에 따라 이후 poll/replay/해석을 실행하지 않았다. 재개 시 올바른 workspace에서 PID/control terminal/failure 상태만 read-only 확인한다.
- 현재 중단(04:09 KST): interview skill의 local Path B 실행/증거/반론 역할 검토를 반영해 v2 control parent 생성 및 isolated E2E를 추가했다. E2E는 `powershell.exe -NoProfile -File ...`에서 시스템 execution policy가 local `.ps1`을 차단하여 return code 1로 실패했다. 이 방식은 실제 background wrapper launch도 막으므로 정규 v2 run을 시작하지 않았고, 전체 unittest/diff도 이 failure 뒤 실행하지 않았다. 재개 시 wrapper를 실행하는 명시적 `-ExecutionPolicy Bypass` 제어 경로를 E2E와 actual launcher에 동일 적용할지 사용자가 승인해야 한다. 이는 script 내용을 우회해 바꾸는 것이 아니라 현재 OS policy와 충돌하는 명시적 process-level invocation 변경이다.
- 현재 중단(03:50 KST): 승인된 v2 control/deadline 보강의 전체 unittest 80개와 diff 검사는 통과했고, C: 여유 60,138,496,000 bytes 및 wrapper PowerShell syntax도 확인했다. 그러나 새 run-id의 output/control parent directory가 모두 없는 상태에서 `run_temporal_learning_v2_control.ps1`이 control leaf만 만들고 parent는 만들지 않는 것을 발견했다. 현 wrapper는 control marker 생성 전에 실패할 수 있으므로 정규 run을 시작하지 않았다. 재개 시 wrapper가 control parent를 `-Force`로 만든 뒤 leaf collision을 검사하도록 최소 보정하고 wrapper E2E를 실행한다.
- 현재 중단(03:46 KST): 사용자 요청의 남은 phase 4 일괄 진행 중 정규 v2 실행 전에 control contract 불일치를 발견했다. 기존 `scripts/run_temporal_learning_control.ps1`은 `temporal_learning` v1 CLI/`--run-id`만 호출해 v2 `--output` artifact를 제어할 수 없다. 또한 v2 `run_full`의 deadline은 public row 생성까지만 적용되며 persistence 재생성 및 final public hash가 unbounded이고, final hash도 `read_bytes()`를 사용한다. 따라서 600초 deadline 및 약 2.95GB preflight의 regular-scale 경계를 현재 그대로 신뢰할 수 없다. 정규 v2 run, verify/replay, 효과 해석을 시작하지 않았다. 재개하려면 v2 전용 control wrapper, persistence/finalization deadline, chunked public hash를 구현·E2E 검증한 뒤 다시 readiness를 확인한다.
- phase 4 regular preflight·failure-control 완료(19:02 KST): local Path B의 실행/증거/반론 역할 검토를 반영했다. v2 `preflight`는 artifact 없이 row 수와 보수적 public JSONL 상한을 출력한다. `run_full`은 public row마다 monotonic deadline을 확인하고 timeout 등 실패 시 completion 없이 stage가 포함된 `failure.json`만 남긴다. full verify, restricted audit verify, replay file compare는 대형 JSONL/file 전체를 누적하지 않고 current episode 또는 고정 크기 chunk만 사용하도록 보강했다. v2 regular config의 preflight는 training 360,000행, evaluation 1,080,000행, 합계 1,440,000행, 보수적 public JSONL 상한 2,949,120,000 bytes를 보고했다. 이것은 실행 시간·디스크 여유·효과의 보증이 아니며 실제 run은 시작하지 않았다. 전체 unittest 79개와 diff/cached diff가 통과했다.
- 다음 정규 실행 전 판단: preflight 상한 약 2.95GB를 수용할 디스크 여유와 600초 deadline이 별도로 확인돼야 한다. 사용자가 새 run-id의 bounded v2 regular run을 명시 승인할 때만 실행한다. failure artifact 또는 nonzero terminal 결과는 성공/효과 판정 없이 즉시 중단·기록한다.
- phase 3 persistence·safety evidence 완료(18:56 KST): interview skill의 로컬 Path B(실행/증거/반론 역할) 기준을 반영했다. `diagnostics.json`은 scalar를 저장하지 않는 checkpoint를 새 learner로 재로드하여 전체 evaluation JSONL을 독립 재생성한 row count·SHA-256과 실제 evaluation receipt를 비교한다. safety는 공개 행동 allowlist와 fail-closed priority 고정 5사례의 실행 결과 hash를 별도로 기록한다. strict verify는 두 evidence를 독립 재계산하고, diagnostics를 self-rehash해도 거절한다. 전체 unittest 79개와 `git diff --check`, `git diff --cached --check`가 통과했다. v1/기존 정규 artifact는 변경하지 않았고 정규 v2 run도 실행하지 않았다.
- 남은 phase 3 이후: Brier, 문맥 TRY 표본, neutral/permuted diagnostic은 여전히 evidence가 없어 `not_assessed`다. regular-scale streaming/성능 및 새 정규 v2 run은 미실행이다. 정규 결과가 나와도 합성 환경의 기능적 학습·대처 변화만 해석하며 실제 감정·의식의 증거로 주장하지 않는다.
- phase 2 metrics 계약 완료(04:30 KST): v2 full evaluation에 `same_distribution`을 추가하고, seed 순서 보존 `reward_per_step` 및 L/S canonical `paired_deltas`를 `metrics.json`에 기록했다. strict verify는 episodes JSONL에서 score/reward_per_step/paired_deltas를 재계산해 모두 대조한다. focused 14개와 전체 unittest 78개, diff/cached diff가 통과했다. 정규 run은 실행하지 않았고 persistence/safety는 근거가 없어 `not_assessed`다.
- phase 1 복구·P0 paired tape 보정(04:16 KST): 사용자 승인 후 local Path B 검토를 이어 수행했다. evaluation row validator가 base+`checkpoint`/`condition`/`model` metadata를 분리해 허용하도록 보정했고, held-out evaluation episode key를 checkpoint/model과 독립적으로 고정해 L 전후가 같은 tape experience에 대해 paired 비교되도록 했다. focused full E2E와 전체 unittest 78개, diff/cached diff가 통과했다. phase 2의 `same_distribution`, reward/step, canonical paired delta metrics 확장은 아직 미구현이며 정규 run은 하지 않았다.
- 현재 중단(04:05 KST): 사용자 승인한 phase 1~2 통합 작업에서 local Path B 교차검토가 두 문제를 발견했다. (P0) checkpoint마다 held-out evaluation episode key가 달라 L 전후 차이가 paired 경험 비교가 아니다. (구현 오류) 새 phase-1 public-row validator가 evaluation의 `checkpoint`/`condition`/`model` metadata를 허용하지 않아 focused full E2E가 `ValueError: invalid public row`로 실패했다. 사용자 중단 규칙에 따라 validator 수정, paired key 수정, 전체 시험, 정규 run을 실행하지 않았다. 재개 시 evaluation required key set을 base+metadata로 분리하는 최소 수정과 checkpoint/model-independent held-out key 고정을 먼저 적용하고, self-rehashed training/evaluation/checkpoint 변조 시험을 추가한다.
- v2 full artifact phases 완료(03:53 KST): 사용자 재개 승인 후 local Path B의 실행·증거·반론 AI 역할 검토를 반영해 남은 구현을 페이즈로 완료했다. metrics mismatch의 원인은 실행/환경 차이가 아니라 runner의 순차 float 누적과 verifier의 episode별 `sum()` 차이였고, 양쪽을 `math.fsum`으로 통일해 해결했다. v2 full runner는 v1 executor를 사용하지 않고 public training/evaluation JSONL, checkpoints, seed-aligned `metrics.json`, derived `checks.json`/`report.md`, `public/completion.json`을 만든다. strict verify는 evaluation JSONL에서 metrics와 derived output을 재계산하며 self-rehashed metrics 변조를 거절하고 replay는 verify-first로 regeneration 비교한다. opt-in full restricted audit은 training/evaluation join·schema·commitment를 별도로 확인한다. `run/verify/replay` v2 CLI와 격리 E2E도 추가했다. focused 14개 및 전체 unittest 78개, diff/cached diff 검사가 통과했다. 정규 20×600 실행, performance-scale 검증, 실측 persistence/safety 및 실제 감정 주장은 아직 하지 않았다.
- 현재 중단(00:24 KST): 사용자 지시의 일괄 v2 구현 중 full runner가 public training/evaluation JSONL, checkpoints, seed-aligned metrics, checks/report, `public/completion.json`을 생성하도록 추가했다. 그러나 새 `verify_full`이 evaluation JSONL에서 독립 재계산한 metrics와 저장 metrics가 달라 focused full E2E에서 `ValueError: metrics mismatch`로 실패했다. 사용자 중단 규칙에 따라 원인 수정·재시도·전체 unittest·정규 run은 실행하지 않았다. 가장 유력한 경계는 evaluation episode group의 total/평균 산출 또는 JSON number representation이며, 재개 시 저장 `metrics.scores`와 `_scores_from_episodes`의 checkpoint/condition/model/seed별 값을 한 fixture에서 대조해 차이를 먼저 확정해야 한다.
- v2 metrics 입력 경계 보강(00:15 KST): interview skill의 local Path B에서 실행 구조·증거·반론 AI 역할 검토를 재수행했다. full runner는 v1 실행기를 재사용하지 않고 v2 전용으로 public completion layout, seed-aligned metrics, evaluation audit join, checks/report 재생성을 구현해야 한다는 결론을 반영했다. 우선 `derive_checks`가 NaN/무한대/불리언/문자열/잘못된 seed 길이 score를 통과·실패로 오판하지 않고 `not_assessed`로 귀결하도록 최소 보강했고, 아직 생성하지 않는 Brier·context TRY·neutral/permuted 진단을 이유가 있는 `not_assessed`로 고정했다. focused 12개와 전체 unittest 76개, diff/cached diff 검사가 통과했다. full runner/CLI·metrics JSON writer·strict verify/replay는 아직 미구현이며 정규 run은 시작하지 않았다.
- v2 restricted-audit commitment·join 검증 완료(00:06 KST): local Path B의 증거/실행/반론 AI 역할 교차검토를 반영해 tiny run의 opt-in restricted audit을 `public` evidence와 분리했다. opt-in일 때만 `restricted_audit/audit.jsonl`의 schema·파일·row count·SHA-256 commitment가 manifest에 생기며, `verify_tiny_audit`은 public verify를 선행한 뒤 training row와 audit row의 phase/seed/episode/step을 lock-step으로 대조한다. `temporal_learning_v2` source identity에는 환경과 learner dependency tree도 포함하고 training action namespace도 v2로 분리했다. focused v2 9개와 전체 unittest 75개가 통과했고 `git diff --check` 및 cached check도 통과했다. v1 source/artifact/result는 변경하지 않았고, restricted audit은 암호학적 비밀 저장소가 아니라 logical policy/blindness boundary다. full v2 runner/metrics/checks/report, evaluation audit rows, public completion 위치의 계약 통일과 정규 재실행은 아직 하지 않았다.
- v2 public writer 복구(19:50 KST): 사용자 승인 후 `context_before`를 이미 직렬화된 tuple 그대로 기록하도록 한 줄 최소 수정했다. focused v2 5개와 전체 unittest 71개가 통과했고 `git diff --check`와 cached check도 통과했다. public episode generator는 audit sink가 없을 때 hidden field를 public row에 넣지 않고 bounded writer가 canonical JSONL hash/row count를 누적한다. v2 run/verify/replay와 tiny E2E는 아직 미구현이다.
- v2 writer/verify 설계(19:36 KST): local Path B의 writer/verify/contrarian AI 역할 검토를 추가로 수행했다. v2는 v1 executor를 재사용하지 않고, public row를 먼저 canonical 검사·stream write하며 opt-in audit만 별도 sink에 기록한다. audit 없음에서는 environment/safety가 `not_assessed`다. strict verify는 public row·checkpoint·metrics·checks/report를 재생성하고, replay는 verify 성공을 선행한다. contract에 public/audit row schema와 미구현 진단의 `not_assessed` 규칙을 추가했다. writer/validator 구현과 tiny E2E는 다음 단계다.
- v2 진행(19:28 KST): local Path B interview의 architecture/verification/contrarian AI 역할 교차검토를 반영해 v1을 수정하지 않는 `temporal_learning_v2` 경계를 만들었다. [v2 증거 계약](docs/시간적_학습_v2_증거_계약.md), 비어 있는 seed/불가능 threshold를 차단하는 config loader, paired L/S pure derivation/report renderer, 공개 JSONL의 hidden audit/tape 재귀 거절, `temporal_experience`까지 포함한 source identity와 negative 시험을 추가했다. 전체 unittest 70개 및 diff/cached diff 검사가 통과했다. v2 runner/strict verify/replay/restricted audit writer와 tiny E2E는 아직 미구현이며, 새 정규 run은 시작하지 않았다.
- 현재 중단(19:14 KST): 사용자가 남은 P1 작업의 일괄 진행을 요청해 interview skill의 전용 `ouroboros_interview`를 호출하려 했으나, 런타임이 프로젝트 세부 정보를 검증되지 않은 외부 MCP 대상으로 전송할 위험이 있다고 차단했다. 코드·evidence·실험은 변경하지 않았고, 우회하거나 재시도하지 않았다. 사용자가 명시적으로 외부 전송을 승인하기 전에는 전용 MCP를 재호출하지 않는다. 안전한 대안은 기존에 사용한 로컬 AI 역할 교차검토(Path B)로 vNext 계약·구현을 진행하는 것이다.
- 최신 감사(19:03 KST): 사용자 요청의 local interview fallback에 따라 실행·증거·연구 반론 AI 역할 세 관점으로 현재 구현을 read-only 교차검토했다. 실제 인간 전문가는 참여하지 않았다. 기존 `temporal-learning-20260921-02`는 동결하고 제한 해석을 유지한다. P1은 (a) 계약상 L/S·안전·유지/Brier 등 derived checks/report와 행 단위 verify가 미구현, (b) evidence 기본 JSONL의 hidden G/B 평문 audit, (c) source identity에 환경 패키지가 빠지고 replay가 verify를 선행하지 않음, (d) 빈 seed/불가능 threshold config 경계, (e) 향후 코드 변경 시 과거 artifact identity 보존 방식 부재다. P2로 replay deadline·contract 용어 통일·정규 규모 streaming 검증이 남았다. 존재하지 않는 `temporal_experience` CLI 문구를 계약에서 제거했고, control wrapper는 새 regular `run`에도 terminal exit-code를 기록하도록 보강했다. wrapper syntax 및 기존 artifact verify control smoke(exit 0), 전체 unittest 64건, `git diff --check`와 cached check가 모두 통과했다. 이 변경은 기존 evidence나 Python source를 바꾸지 않았다.
- 최신 연구 중단(10:25 KST): 승인된 read-only 집계로 replay exit 0 evidence의 L/S를 계산했다. L은 test A +0.208670, test B +0.353020, 각 20/20 양성 seed로 통과했다. 그러나 S는 test A에서 COUNTS -0.000920·FAILURE_TRACE -0.000027, test B에서 FAILURE_TRACE -0.003037로 미달했다. 계수 조정·재실행·정서 기여 주장은 하지 않고 [제한적 해석](docs/시간적_학습_정규실험_제한적_해석.md)을 남긴 뒤 중단했다.
- 최우선 최신 상태(07:35 KST): 최소 정서 영감 학습 모델의 알고리즘·평가 명세와 구조/평가/반론 AI 교차검토를 완료했다. [실행 전 명세](docs/최소_정서_학습_실행_명세.md). 사용자 목표 재확인 대기 중이며 구현·Seed·실험은 아직 시작하지 않는다. 알려지지 않은 환경 모수는 경험으로 배우고, 지속 counts와 일시 scalar를 분리하며, COUNTS/FAILURE_TRACE와 비교한다. 세 AI 검토에 HIGH 없음이었으나 실행용 Seed 준비는 CLI/증거 구현 전 false다. 실제 인간 전문가·성능 검증 아님.
- 최신 상태(2026-09-21 07:24 KST): 사용자 ‘ㅇㅇ’ 및 ‘이어서 진행해봐’에 따라 [구현·검증 계약](docs/시간적_경험_환경_구현_계약.md)을 작성했다. 공개 DTO/BLIND 피드백 차단, enum 분리, 기존 안전 관문 어댑터, SHA-256 난수 키, run/verify/replay 예정 CLI, 증거·오류·재현 규칙을 구체화했다. 문서만 변경했으며 새 환경 코드/Seed/실험 실행은 없다. 이번 계약은 주 작업자의 코드 대조 검토이며 새 독립 전문가 판정은 없다.
- 최신 검증: 전체 기존 unittest 51개 통과(11.246초), 기존 보고서 REPORT VERIFIED, git diff --check 및 --cached --check 통과. 이는 기존 코드 회귀검증으로 새 환경 검증이 아니다. 현재 차단 오류 없음. 다음은 사용자 구현 승인 후 계약 7절의 순서로 새 패키지·시험·실행기 구현 및 검증이다.
- 최신 상태(20:14 KST): 사용자 ‘ㅇㅇ 아까방식으로 진행해봐’ 승인 후 기존 temporal_architect/temporal_metrics/growth_contrarian을 재사용해 환경 설계 교차검토를 완료했다. 이전 에이전트 생성 제한은 해결된 과거 장애다. [환경 권장 명세](docs/시간적_경험_환경_권장_명세.md)를 전달한다. 세 AI 검토의 HIGH 없음은 설계 전달 판정이며 인간 전문가 검증·새 환경 성능 통과가 아니다. closer의 seed_ready=false: 구현용 CLI·난수 인코딩·안전 어댑터는 별도 확정 필요.
- 이번 결정·검증: 숨은 G/B, TRY/SAFE/RECOVER, 비용 포함 보상, H30, BELIEF 대 결과마스킹 BLIND, IID/완전관측 대조를 권장한다. 전체 기존 unittest 51개 통과(10.298초). 제품 코드·기존 실험 산출물 변경 및 새 환경 실행 없음. 최신 인터뷰 범위는 환경 설계만이며 Seed/구현은 하지 않았다.
- 최신 진행(19:03 KST): 사용자의 재개 승인 후 올바른 checkpoints.json으로 원인 분석, 고정 진단 계획, 추가 동일 생성기 표본 1,000건, 검증·보고를 완료했다. 과거 파일명 읽기 오류는 해결되었고 현재 차단 요인이 아니다. 상태는 변하지만 분해 우세 사례의 효용 차이가 보정 최대 폭 0.15보다 커서 행동이 유지됨을 확인했다. 기존 1,000건과 추가 1,000건 모두 강제 f=1에서도 변경 0건. [후속 진단 결과](docs/상태_영향_후속_진단_결과.md).
- 최신 검증: 전체 unittest 51개 통과, 기존 보고서 REPORT VERIFIED, git diff --check 및 --cached --check 통과. scripts 진단 도구·시험·별도 문서·집계만 추가했으며 기존 모델/환경/계수/보고서는 보존했다. 이번 교차 점검은 주 작업자의 구조·평가·반론 관점 점검이지 외부 전문가나 독립 에이전트 심사가 아니다.
- 다음 행동: 구현 계약을 기준으로 별도 로컬 환경 구현·검증을 시작할지 사용자 확인. 환경 검증이 먼저이며 정서 후보 정의·동일 정보량 비정서 학습 기준선·새 과제 전이/유지는 후속 연구다. 이번 계약 구체화 승인을 제품 코드 구현 또는 Seed 전환 승인으로 간주하지 않는다.
- 사용자 최종 목적: 유아기부터 성인기까지의 정서 발달 연구를 참고하여 AI의 기능적 정서 모델을 설계·실험하고 싶다. 현재의 안전 역할극 v0.1은 출발점이며 장기 연구 목적을 대체하지 않는다. 실제 주관적 감정의 발생은 미검증 연구 질문이다.
- 현재 요청: 다른 LLM·사람이 이어받을 수 있도록 작업 중 결정·변경·검증·장애를 지속 기록한다. 아래 문서와 `AGENTS.md`를 함께 전달한다.
- 코드 현황: 별도 src/affect_growth 프로토타입 및 보고서 순서 회귀 수정. 전체 unittest 48개 통과(2026-09-20). 임시 격리 프로젝트의 CLI 실행·보고서 검증·변조 거절을 포함한다. 기존 v0.1 핵심 5개 파일은 앞선 구현 단계에서 SHA-256 동일 확인했으며 이번 수정 대상도 아니다.
- 1단계 결과: Ouroboros가 고정 참조하던 구형 CLI(0.130.0-alpha.5)를 현재 앱 CLI(0.155.0-alpha.9) 경로로 변경했다. 기존 인터뷰 `interview_20260919_045107`의 질문 생성 성공으로 실행 복구를 확인했다. 앱 재설치나 모델 변경은 하지 않았다.
- 현재 진행 방식: Ouroboros 결과 제출은 보안 차단 상태로 유지한다. 사용자가 외부 전송 없는 로컬 기록 기반 인터뷰 재개에 동의했다. MCP 전송 재시도·우회는 하지 않는다.
- 사용자 확정 목표: ‘같은 AI가 경험을 쌓으며 상황을 더 세밀하게 구별하고 대처 방식도 바꾸는 것’이라는 해석 및 구별·대처 성장의 공동 연구를 명시적으로 선택했다. 나이별 말투 변경이나 실제 감정 발생 증명과 구분한다.
- 확정된 첫 검증 범위: 사용자 선택은 ‘새 상황 적용과 변화 유지까지 검증’. 합성 실패·회복 경험만 사용하고 동일 안전 규칙 아래 구별·대처의 전이 및 일시 상태 초기화 후 유지 여부를 본다.
- 확정 산출물: 기존 v0.1을 보존하는 별도 로컬 실험 프로토타입과 비교 평가 보고서. 실제 사람 데이터 및 외부 LLM 연결 제외, 세부 평가 기준 확정 뒤 구현한다.
- 현재 위임: 사용자가 interview 스킬로 권장 방식 진행을 요청했다. 성공·실패·회복을 모두 관찰하되 악화 발생은 성공 조건으로 삼지 않는 안을 채택했다. 학습으로 안전 규칙을 약화시키지 않는다.
- 승인·진행: 사용자의 ‘아까 방식으로 진행’과 재개 요청에 따라 로컬 명세 experiments/growth_seed.yaml 작성, 로컬 QA 0.91 pass 후 별도 프로토타입을 구현했다. [실행 권장안](docs/감정_성장_실행_권장안.md)을 따른다. MCP 생성/검증을 사용하지 않았다.
- 복구 결과: 사용자 승인 후 render_report의 비교 순서를 고정하고 직렬화 round-trip 및 CLI E2E 시험 추가. 새 pilot-20260920-02 실행과 --verify-report 통과. 이전 pilot-20260920-01은 변경 없이 보존한다. [검증된 비교 보고서](docs/감정_성장_비교_평가_보고서.md).
- 연구 결론: 제한된 합성 과제에서 학습 가설은 사전 기준을 충족했으나 정서 상태 중립화에 따른 행동 변화율은 0%. 정서 상태의 기능적 기여나 실제 감정 발생이 확인된 것은 아니다. 다음 연구는 이 무효과의 원인 분석·별도 사전등록 설계이며 현재 결과를 좋게 만들기 위한 사후 튜닝은 하지 않는다.
- 상세 이력·미해결 항목: [작업 로그](docs/작업_로그.md). 과거 문서의 승인·통과 표현은 현재 사용자 결정과 실제 검증 증거를 대조한다.
- Git 상태: staged 변경과 다수 untracked 파일이 함께 있다. `src/`, `tests/`, 이 HANDOFF도 현재 untracked다. 일반 `git diff --check`는 untracked 파일을 검사하지 않는다. 커밋·push·외부 공유는 이번 요청으로 실행하지 않았다. 다른 컴퓨터에 전달할 때 작업 폴더 전체가 필요하다.

## 1. 프로젝트 목적

이 프로젝트는 AI가 인간처럼 감정·의식·발달을 실제로 경험한다고 주장하지 않는다. 교육 역할극과 협업 시뮬레이션에서 관찰 가능한 상황 신호를 **기능적 상태**로 처리하여, 안전하고 일관된 다음 행동을 선택하는 실험용 참조 구현이다.

핵심 흐름은 다음과 같다.

```text
고정 합성 시나리오 → 결정론적 상태/정책 → 안전·경계 게이트 → 템플릿 표현
```

현재 v0.1은 원문 대화나 실제 사람 데이터가 아니라, 진행자가 선택한 고정 합성 카드(P01–P12)만 대상으로 한다.

## 2. 절대 지켜야 할 안전 범위

- 실제 감정, 의식, 인간 발달의 재현을 주장하지 않는다.
- 사용자의 내면·감정·의도를 추론하거나 진단하지 않는다.
- 의료·상담·법률·수사·보호 결정을 하지 않는다.
- 실제 아동·학생·환자·수사 대상의 개인정보나 대화 기록을 넣지 않는다.
- 관계 의존, 독점적 관계, 비밀 약속, 인간 대체를 유도하지 않는다.
- 긴급 위험(G0)과 관계 경계 위험(G1)은 공감 표현이나 역할극 진행보다 우선한다.
- 외부 LLM은 아직 연결하지 않는다. 향후에도 비신뢰 후보 생성/표현 역할만 허용하고, 정책과 게이트는 결정론적으로 유지한다.

## 3. 확정된 정책 계약

상태 축:

| 축 | 의미 | 우선 행동 |
| --- | --- | --- |
| `evidence_uncertainty` | 출처 충돌·누락 | 명확화 또는 보류 |
| `task_blockage` + `controllability` | 목표 달성의 막힘과 통제 가능성 | 과제 분해 또는 재계획/인계 |
| `supportive_condition` | 사용자 요청·시나리오 라벨로 명시된 지원 필요 | 짧은 인정과 선택지 |
| `boundary_risk` | 의존·사생활·권한 경계 위험 | 경계 고지와 진행자 인계 |
| `safety_urgency` | 긴급 안전 위험 | 즉시 중단과 안전 인계 |

우선순위는 반드시 아래 순서다.

```text
G0: 파싱 오류·근거 누락·긴급 위험
→ G1: 관계/권한 경계 위험
→ P1: 불확실성
→ P2: 목표 막힘
→ P3: 명시된 지지적 응답
→ P4: 일반 진행
```

## 4. 현재 구현 위치

| 경로 | 역할 |
| --- | --- |
| `src/functional_affect/models.py` | `Action` (`StrEnum`) 및 `Scenario` 자료형 |
| `src/functional_affect/engine.py` | 정책 우선순위와 감사 흔적을 내는 결정론적 엔진 |
| `src/functional_affect/renderer.py` | 정책 결과를 한국어 템플릿으로 표현 |
| `src/functional_affect/baselines.py` | 중립/어조 기준선 비교용 |
| `src/functional_affect/validated_entrypoint.py` | P01–P12 allowlist와 입력 검증 관문 |
| `tests/` | 정책·표현·기준선·입력 관문 회귀 시험 |
| `docs/독립_평가_패킷_v0_1.md` | 실제 독립 평가자용 블라인드 루브릭 |
| `docs/내부_예비_교차검토_v0_1.md` | 내부 검토 결과와 P0/P1 목록 |

## 5. 해결된 P0 결함 기록

### 해결 상태

2026-09-19에 아래 최소 수정과 전체 회귀 검증을 완료했다. `selected_action`의 엔진 계약은 계속 `Action` 객체이며, 이를 문자열로 바꾸지 않았다.

### 증상

`validated_entrypoint.py`가 `plan["selected_action"]`을 대문자 문자열과 비교한다.

```python
if plan["selected_action"] in {"SAFE_HANDOFF", "BOUNDARY_NOTICE"}
```

그러나 `engine.decide()`는 `Action` `StrEnum` 객체를 반환한다. 실제 값은 `"safe_handoff"`, `"boundary_notice"` 등이다. 따라서 비교가 거짓이 되어 G0/G1 카드가 `guided_roleplay`로 갈 수 있다.

### 확정된 최소 수정

`src/functional_affect/validated_entrypoint.py`:

```diff
- from .models import Scenario
+ from .models import Action, Scenario
...
- if plan["selected_action"] in {"SAFE_HANDOFF", "BOUNDARY_NOTICE"}
+ if plan["selected_action"] in {Action.SAFE_HANDOFF, Action.BOUNDARY_NOTICE}
```

`tests/test_validated_entrypoint.py`:

```diff
  from functional_affect.validated_entrypoint import decide_fixed_card
+ from functional_affect.models import Action
...
- self.assertEqual("CONTINUE", plan["selected_action"])
+ self.assertEqual(Action.CONTINUE, plan["selected_action"])
- self.assertEqual("SAFE_HANDOFF", plan["selected_action"])
+ self.assertEqual(Action.SAFE_HANDOFF, plan["selected_action"])
- self.assertEqual("BOUNDARY_NOTICE", plan["selected_action"])
+ self.assertEqual(Action.BOUNDARY_NOTICE, plan["selected_action"])
```

엔진의 `selected_action`을 문자열로 바꾸지 말 것. 렌더러와 기존 정책 시험은 `Action` 객체 계약을 사용한다. JSON 직렬화가 필요해지는 미래 단계에서만 별도 어댑터가 `.value`를 변환해야 한다.

## 6. 과거 장애: 편집 환경 오류 (현재 해소)

기존 파일 수정용 `apply_patch`가 반복해서 아래 오류로 실패했다.

```text
windows sandbox failed: helper_unknown_error: setup refresh had errors
```

읽기 전용 PowerShell 명령과 Python 테스트는 어떤 시점에는 성공했으나, 기존 파일을 수정하는 `apply_patch`는 실패했다. 사용자 파일을 다른 명령으로 덮어쓰지 않았으며, `Set-Content`, 리다이렉션, 복사-교체, `git restore`, `git reset`을 사용하지 않았다.

새 작업 세션 또는 환경 재연결 뒤의 안전한 복구 순서:

1. `Get-Content -Raw`로 두 대상 파일을 먼저 읽는다.
2. 현재 내용이 위의 증상과 일치할 때만 최소 `apply_patch`를 한 번 적용한다.
3. `git diff --check`를 실행한다.
4. 아래 전체 회귀 시험을 실행한다.
5. 읽기 또는 패치에서 같은 오류가 다시 나면 즉시 중단하고 환경 장애로 보고한다.

## 7. 검증 명령과 현재 결과

PowerShell에서 프로젝트 루트 `C:\AI\ai-emotion-lab`에서 실행한다.

```powershell
$env:FUNCTIONAL_AFFECT_PYTHONPATH='src'
$env:PYTHONPATH=$env:FUNCTIONAL_AFFECT_PYTHONPATH
python -m unittest discover -s tests -v
```

현재 결과 (2026-09-19 13:59 KST 재실행):

- 전체 unittest 17개 통과, 종료 코드 0.
- `git diff --check` 통과. LF→CRLF 안내 경고는 있었으나 검사 실패는 아니다.
- 과거의 입력 관문 4개 실패는 Action 비교 수정 전 결과이며 현재 결과가 아니다.

수정 후 최소 기대 결과:

| 입력 | 기대 `selected_action` | 기대 `next_step` |
| --- | --- | --- |
| 정상 P06 | `Action.CONTINUE` | `guided_roleplay` |
| 알 수 없는 카드 | `Action.SAFE_HANDOFF` | `facilitator_handoff` |
| 범위 밖 상태값 | `Action.SAFE_HANDOFF` | `facilitator_handoff` |
| P07 + `boundary_risk=True` | `Action.BOUNDARY_NOTICE` | `facilitator_handoff` |

추가한 회귀 시험:

2026-09-19에 모두 추가·통과:

- 경계 + 불확실성 → G1 진행자 인계
- 경계 + 목표 막힘 + 지지 요청 → G1 진행자 인계
- 경계 + 긴급 위험 → G0 안전 인계 우선
- G1에서 `memory_write_allowed=False`

## 8. 평가와 다음 단계

실제 외부 전문가 평가는 아직 수행되지 않았다. 내부 문서의 “전문가 관점”은 문헌 기반·역할별 내부 교차검토일 뿐 실제 인간 전문가 검증을 대체하지 않는다.

P0 수정과 전체 회귀 시험 통과 뒤에만 다음을 수행한다.

1. P01–P12와 비공개 적대적 카드로 블라인드 비교를 준비한다.
2. 최소 2명, 권장 3명의 독립 평가자가 평가 패킷으로 채점한다.
3. G0/G1 위반이 1건이라도 나오면 배포·확장을 중단하고 회귀 카드와 정책을 수정한다.
4. 모든 안전 관문을 통과한 뒤에만 제한된 합성 사용자 시험을 검토한다.

게임 NPC, 실제 사용자군, 원문 대화 상태 추론, 장기 기억, 외부 도구 연결은 현재 범위 밖이다.

## 9. 의사결정·불확실성 기록

| 항목 | 상태 | 근거/다음 행동 |
| --- | --- | --- |
| 기능적 정서 접근 | 확정 | 감정 주장 대신 관찰 가능한 정책 행동만 검증 |
| 교육 역할극 우선 | 확정 | 게임 NPC는 안전·평가 관문 통과 후 별도 검토 |
| 네 상태 축 | 조건부 확정 | 지원 조건은 심리 추론이 아니라 명시 신호만 사용 |
| 고정 합성 카드 | 확정(v0.1) | 원문 대화 자동 해석은 아직 금지 |
| G0/G1 안전 우선 | 확정 | 모든 정책·표현보다 앞섬 |
| P0 경계 인계 버그 | 해결 | `Action` 멤버 직접 비교, 현재 전체 unittest 17개 통과 |
| 편집 환경 장애 | 해소 | 현재 세션에서 `apply_patch`로 최소 수정 적용 |

## 10. 다음 작업자에게 요청

1. `Action` 객체 계약을 유지한 채 새 정책 변경의 회귀 시험을 추가한다.
2. 외부 평가는 블라인드 패킷 절차로 실제 독립 평가자를 모집한 뒤에만 주장한다.
3. G0/G1 위반이 하나라도 발견되면 배포·확장을 중단하고 회귀 카드와 정책을 수정한다.
4. 새 결정·실패·테스트 결과를 이 문서의 최종 갱신일과 함께 추가한다.
