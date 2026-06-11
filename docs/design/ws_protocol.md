# WS 프로토콜 단일 레퍼런스 — `/ws/{run_id}`

> 작성: 2026-06-11 (T1-P5) · 코드 정본: `backend/app/routers/gateway.py`
> 관련: @marker_api.md(HTTP 표면) · @harness_audit.md(T1 점검 보고서 — 같은 PR에서 생성)
> 배경: T1 교정(P1~P4)으로 WS 이벤트가 3종(artifact·gate·session)으로 통일되었다. 정의가 spec들에 파편화되어 있던 것을 이 문서로 단일화한다 — WS 프로토콜에 관한 한 이 문서가 단일 레퍼런스다.

---

## 0. 한눈에

- WS 라우트는 `/ws/{run_id}` **단일**(routers/gateway.py:98) — backend 전체에서 `@router.websocket`은 이 1곳뿐.
- 전달 모델: **post-turn echo**(턴 완료 후 일괄 발행, 스트리밍 아님) + **완전 단방향**(서버→클라이언트만).
- 서버→클라이언트 이벤트 3종: `artifact` · `gate` · `session`. 서버 능동 close 코드 2종: `4401` · `4404`.

## 1. 접속·인증

| 항목 | 내용 | 근거 |
| --- | --- | --- |
| 라우트 | `@router.websocket("/ws/{run_id}")`, 핸들러 `ws()` | routers/gateway.py:98, :99 |
| URL | `/ws/{run_id}?token=<JWT>` — token은 **쿼리 파라미터** | routers/gateway.py:100 |
| 인증 | `resolve_user_id(f"Bearer {token}" if token else None, websocket.app.state.settings)` — HTTP와 동일한 auth.py:40 함수 재사용(Bearer 접두를 수동 부착) | routers/gateway.py:102-103 |
| 로컬 폴백 | `vfs_backend != "supabase"` 또는 `supabase_url` 부재면 토큰 없이 무조건 `"demo"` — **로컬 모드에서 4401은 발생 불가** | auth.py:41-43 |
| 소유자 검사 | `store.get_manifest(run_id)`의 `user_id` 대조 | routers/gateway.py:104-105 |
| 등록 | 통과 시 accept 후 `app.state.connections.setdefault(run_id, set()).add(ws)` | routers/gateway.py:111-112 |
| 레지스트리 | `connections`(run_id→WebSocket set)는 server.py:91에서 단일 생성, HTTP 핸들러와 공유 | server.py:91 |

프론트 측 URL 생성·토큰 획득:

- `wsUrl(runId, token)` — `http`→`ws` 치환 + `?token=` `encodeURIComponent` (frontend/lib/api.ts:89-92).
- token 획득: `getAccessToken()`(supabase 세션) — useRunSocket.ts:35.

## 2. close 코드

서버 능동 close는 **accept 이전 2곳뿐**이다.

| 코드 | 의미 | 발생 조건 | 근거 |
| --- | --- | --- | --- |
| `4401` | 인증 실패 | `except AuthError: close(4401)`. supabase 모드에서 token 부재(auth.py:45-46) · 헤더 파싱 실패(auth.py:49-52) · JWKS 서명 검증 실패(auth.py:62-63) · sub 클레임 부재 등 | routers/gateway.py:108-109 |
| `4404` | run 부재 **또는** 소유자 불일치 | manifest 없는 run과 타인 run을 **구분하지 않음**(존재 여부 비노출) | routers/gateway.py:104-107 |

- 정상 disconnect: `except WebSocketDisconnect` → 레지스트리 discard만 수행(서버발 close 코드 없음) — routers/gateway.py:116-117.
- 부수: `_publish` 송신 실패 소켓은 discard(routers/gateway.py:48-52, close 미호출) — 죽은 소켓 청소.

## 3. 전달 모델

### post-turn echo — 스트리밍 아님

`gateway_run`(routers/gateway.py:58)이 하네스 **턴 전체 완료**(`state.gateway.run(req, harness)` :78) 후에 발행한다:

1. session restored 발행(:87-90)
2. `result.events` 순차 발행(:91-92)
3. HTTP 4키 응답 `{output_path, text, gate, meta}`(:93-95)

턴 중간 이벤트·토큰 스트리밍은 없다.

### 완전 단방향

- 서버 수신 루프는 drain 전용 — 클라이언트→서버 메시지를 전부 무시(routers/gateway.py:113-115).
- 프론트도 발신 0건 — useRunSocket.ts 전문에 `ws.send` 없음. **클라이언트 발신 프로토콜 자체가 없다.**

### 발행처 전수

backend/app에서 `_publish`·`connections` 사용처는 routers/gateway.py와 server.py:89-91(초기화)뿐 — 하네스·게이트웨이 코어·DeployAdvisor는 WS 직접 발행이 없다. WS 라우트는 `/ws/{run_id}` 단일.

## 4. 이벤트 3종

| type | wire 형식(키 전수) | 발행 경로 |
| --- | --- | --- |
| `artifact` | `{"type":"artifact","path":str}` 2키 고정 | 하네스 `HarnessResult.events` → 라우터 릴레이(:91-92) |
| `gate` | `{"type":"gate","gate":GateEnvelope.to_dict()}` 2키 | brainstorming 하네스만(아래 비대칭 참고) |
| `session` | `{"type":"session","event":"restored","studio":str,"run_id":str}` 4키 고정 | 라우터 직발행(:88-90) |

### 4.1 artifact

- `path` = VFS 절대 경로(`/{run_id}/{studio}/...`) 또는 디렉터리 접두(review `legal/`·`i18n/` — trailing slash)·폴더 경로(design `design-system/components/headline`).
- 하네스가 `HarnessResult.events`(harness.py:68)에 담아 반환 → 라우터가 릴레이(routers/gateway.py:91-92).
- 생성처 전수:

| 하네스 | 발생 지점 | path |
| --- | --- | --- |
| Passthrough | harness.py:105 | `_passthrough.md` |
| brainstorming | harness_brainstorming.py:252 | `spec.md` |
| brainstorming | harness_brainstorming.py:306 · :335 | `plan.md` |
| design S0 | harness_design.py:527 | `design-system/tokens.json` |
| design S1 | harness_design.py:325 | `rough/layout.spec.json` |
| design S2a | harness_design.py:349 | `design-system/components/visual/v1.png` |
| design S2b | harness_design.py:389 | `design-system/components/headline` |
| design S2c | harness_design.py:431-432 | `design-system/components/disclosure` |
| design S3 | harness_design.py:473 | `metadata.md` |
| review R0 | harness_review.py:179 | `_state.json` |
| review R1 | harness_review.py:381 | `legal/` |
| review R2 | harness_review.py:476 | `i18n/` |
| review R3 | harness_review.py:598 | `report.md` |
| review ack | harness_review.py:629-630 | `_state.json` |

- design은 게이트 정지 턴에도 그 턴까지 누적된 artifact를 `_gate_result(events=)` 경유로 송신한다(harness_design.py:205 · :223-225 · :243).

### 4.2 gate

- `{"type":"gate","gate":GateEnvelope.to_dict()}` 2키. 봉투 직렬화는 §5.
- **⚠️ WS gate 이벤트는 brainstorming(kind="ask")만 발행한다** — harness_brainstorming.py:276(Stage A) · :359(Stage B). 같은 봉투가 HTTP 응답 `gate`에도 동시 탑재된다(:278 · :361).
- design confirm·review status 게이트는 **HTTP 응답 `gate` 필드 전용** — harness_design.py:239-243 · harness_review.py:594-598에 `events.append` 없음(grep 전수 확인된 비대칭). 즉 confirm/status 봉투는 WS로는 절대 오지 않고 HTTP 응답으로만 도착한다.
- 발생 시점(brainstorming):
  - Stage A: LLM이 직접 낸 ask(trigger `"a"` 등)는 그대로 게이트로 패스스루(harness_brainstorming.py:241). 합성 게이트(c/b)는 `ready and document and not ask`일 때만(:260) — `critic_spec` 누락 → trigger `c`(보충) / 충족 → `b`(확정 확인) (:260-268).
  - Stage B: 계약 검증 누락 → `c`(:344-346) · `ready` → `b`(:347-349) · LLM ask 패스스루(:351).

### 4.3 session

- `{"type":"session","event":"restored","studio":str,"run_id":str}` 4키 고정.
- 유일 발행처: routers/gateway.py:88-90 — **라우터 직발행**(하네스 events보다 먼저 송신).
- 발생 조건(모든 스튜디오 공통): 턴 완료 후 heartbeat 결과 `exists==True and status != "active"`(routers/gateway.py:83-84) — 즉 suspended(유휴 1h+, session/liveness.py:44-46) 또는 archived 세션이 이번 턴 touch(:85)로 재활성될 때.
- 동시에 HTTP `meta["session_event"]="restored"`(routers/gateway.py:87).
- status 어휘: `active | suspended | archived`(session/record.py:8-10). 전이 임계: stall 15m · suspend 1h · retention 7d(session/liveness.py:22-24).

## 5. GateEnvelope 직렬화

정의: harness.py:29-59. `to_dict()`는 **`kind`·`actions`를 항상 포함**하고 None 필드는 생략한다(:51-59).

| kind | 동반 필드 | actions | 근거 |
| --- | --- | --- | --- |
| `ask` | `trigger`(`"a"`\|`"b"`\|`"c"`) · `question` · `options` | `["answer"]` | harness_brainstorming.py:74-81 `_to_gate` |
| `confirm` | `step`(`"S1"`…) · `critic`(CriticVerdict.to_dict: `{passed, issues[, scores]}` — critic.py:11-15) · `auto_advanced`(None이면 생략) | `["confirm", "regenerate"]` | harness_design.py:240-242 |
| `status` | `status`(`"PASS"`\|`"WARN"`\|`"BLOCKED"`) · `critical_count` · `warning_count` | `_actions_for(status)` | harness_review.py:594-597 |

- ask 회신은 action이 아니라 **`answer` 필드**로 한다(routers/gateway.py:33 · :37 wire 관례).
- design done은 `gate=null` + `meta.auto_advanced`(harness_design.py:194-203).
- status별 actions 테이블(harness_review.py:42-48): `WARN`→`["ack","regenerate","restart"]` · `BLOCKED`→`["regenerate","restart"]` · `PASS`→`[]`.
- 요청측 action 어휘: `GatewayRun` Literal 5종 `advance | confirm | regenerate | restart | ack`(routers/gateway.py:38).

## 6. 프론트 소비

- 훅: `frontend/lib/useRunSocket.ts`. `RunEvent = { type, path?, gate?, event? }`(:8). GateEnvelope 프론트 타입은 api.ts:23-29(백엔드와 1:1).
- 재연결: `onclose` 시 지수 백오프 `min(1000 * 2**retry, 15000)`ms(:44-50), `onopen`에서 `retry=0`(:40), `onerror`→close 경유(:51).
- 폴링 폴백: WS 단절 동안 `pollMs` 간격으로 합성 이벤트 `{type:"poll"}` 주입(:27-31 · :39 · :46) — **wire 이벤트가 아니라 프론트 합성**(프로토콜 외)임에 주의.
- 소비처(유일): frontend/components/cockpit/CockpitProvider.tsx:775-790
  - `gate` → `applyGate`(:776-777)
  - `artifact` → 캐시 무효화 + 열린 파일 재오픈 + `refreshTree`(:778-786)
  - `poll` → `refreshTree`만(:787-788)
  - **`session` 이벤트는 분기 부재 — 현재 프론트 미소비**(O3 UI는 T2 백로그).
- 게이트 적용: **`applyGate` 단일 적용점(:393-413) + kind별 상태 3분배** — `ask`→`setPendingGate`, `confirm`→`setDesignGate({step, critic, auto_advanced})`, `status`→`setReviewGate({status, critical, warning})`, default→`setPendingGate(null)`. HTTP 응답 `gate`(:427 · :472 · :538 · :614)와 WS `gate`가 동일 적용점을 거친다.
