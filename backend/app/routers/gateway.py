"""[gateway] POST /gateway/run + WS /ws/{run_id} (spec §8.1).

connections(run_id→WebSocket set)와 _publish는 app.state.connections를 공유 —
gateway_run의 이벤트 릴레이와 WS 수명주기가 같은 dict를 봐야 한다
(test_golden_passthrough의 artifact 이벤트가 게이트).
"""
from __future__ import annotations

import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from ..auth import AuthError, resolve_user_id
from ..gateway.harness import HarnessRequest
from ..gateway.registry import select_harness
from ..gateway.video.render import ComplianceError
from ..providers.wrappers import tracked_provider
from ..schemas import ErrorOut, GatewayRunOut, OWNER_RESPONSES
from .deps import get_user_id, require_owner

router = APIRouter(tags=["gateway"])


class GatewayRun(BaseModel):
    run_id: str
    # studio 어휘 = 프론트 발신 3종 + deploy(세션 어휘 LIFECYCLE_STUDIOS 정합·미래 호환)
    studio: Literal["brainstorming", "design", "review", "video", "deploy"]
    prompt: str
    # provider 어휘 = providers/registry.PROVIDER_NAMES와 양방향 동기(test_openapi_contract.py)
    provider: Literal["fake", "demo", "anthropic", "openai", "google"] = "fake"
    is_marker: bool = False
    answer: str | None = None
    # action 어휘 = 하네스 소비 전수 — design: advance·confirm·regenerate·remediate
    # (gateway/pipeline.py — confirm 게이트가 GATE_ACTIONS=["confirm","regenerate"]를 선언;
    #  remediate는 done 전용 D2 폐루프 트리거 — harness_design.py._remediate_copy),
    # review: restart·ack·regenerate (harness_review.py)
    # ask 게이트의 actions=["answer"]는 action이 아니라 answer 필드로 응답(wire 관례).
    action: Literal["advance", "confirm", "regenerate", "restart", "ack", "render", "remediate"] | None = None
    bypass_map: dict | None = None
    # 프론트 advance/confirm 등은 medium을 미지정 → lib/api가 `medium ?? null`로 null 전송.
    # Literal 기본값은 '키 부재'에만 먹으므로 명시적 null도 허용하고 아래서 'image'로 정규화.
    medium: Literal["image", "video"] | None = "image"  # 브레인스토밍 매체 — demo 라우팅용
    mock: bool = False   # 시연용 전역 Mock — true면 전 provider를 fake로 강제(요청 단위)


def _now_ms() -> int:
    return int(time.time() * 1000)


async def _publish(connections: dict[str, set[WebSocket]], run_id: str, event: dict) -> None:
    for ws_conn in list(connections.get(run_id, set())):
        try:
            await ws_conn.send_json(event)
        except Exception:
            connections.get(run_id, set()).discard(ws_conn)


@router.post("/gateway/run", response_model=GatewayRunOut,
             summary="스튜디오 하네스 1턴 실행(게이트 봉투·세션 터치·WS 릴레이)",
             responses={**OWNER_RESPONSES, 402: {"model": ErrorOut}})
async def gateway_run(body: GatewayRun, request: Request,
                      user_id: str = Depends(get_user_id)) -> dict:
    state = request.app.state
    require_owner(request, body.run_id, user_id)
    # 시연용 Mock: provider/미디어를 demo로, 그리고 Marker 하네스를 강제한다.
    # mock인데 is_marker=false(프론트 기본 모델 Claude)면 PassthroughHarness로 빠져
    # 빈 echo만 남아 시연이 깨졌다 → mock=true는 항상 Marker 하네스로 라우팅하고,
    # 유료 게이트는 gateway.run(req.mock)이 우회한다.
    marker = True if body.mock else body.is_marker
    provider_name = "demo" if body.mock else body.provider
    req = HarnessRequest(run_id=body.run_id, studio=body.studio,
                         user_prompt=body.prompt, provider=provider_name,
                         is_marker=marker, answer=body.answer,
                         action=body.action, user_id=user_id,
                         bypass_map=body.bypass_map, medium=body.medium or "image",
                         mock=body.mock)
    media_name = "demo" if body.mock else "google"

    def _media_provider():
        # 주입형 image/vision provider도 usage 추적 래핑 (spec §7-2).
        return tracked_provider(media_name, state.settings, store=state.store,
                                run_id=body.run_id, step=body.studio)

    harness = select_harness(body.studio, marker,
                             media_provider_factory=_media_provider)
    try:
        # gateway.run은 동기 블로킹(provider 호출·ffmpeg 렌더가 분 단위일 수 있음).
        # async 핸들러에서 직접 호출하면 이벤트루프를 점유해 WS 하트비트·동시 요청이
        # 전부 정지한다(라이브 데모 치명). 스레드풀로 오프로딩해 루프를 비운다.
        result = await run_in_threadpool(state.gateway.run, req, harness)
    except PermissionError as e:
        raise HTTPException(402, str(e))
    except ComplianceError as e:
        raise HTTPException(422, str(e))
    now = _now_ms()
    kind = "ask_answer" if body.answer is not None else "user_turn"
    hb = state.session_store.heartbeat(body.run_id, body.studio, now)
    reactivated = bool(hb.get("exists")) and hb.get("status") != "active"
    state.session_store.touch(body.run_id, body.studio, now, kind=kind)
    if reactivated:
        result.meta["session_event"] = "restored"
        await _publish(state.connections, body.run_id,
                       {"type": "session", "event": "restored",
                        "studio": body.studio, "run_id": body.run_id})
    for ev in result.events:
        await _publish(state.connections, body.run_id, ev)
    return {"output_path": result.output_path, "text": result.text,
            "gate": result.gate.to_dict() if result.gate else None,
            "meta": result.meta}


@router.websocket("/ws/{run_id}")
async def ws(websocket: WebSocket, run_id: str):
    token = websocket.query_params.get("token")
    try:
        uid = resolve_user_id(f"Bearer {token}" if token else None,
                              websocket.app.state.settings)
        m = websocket.app.state.store.get_manifest(run_id)
        if m is None or m.user_id != uid:
            await websocket.close(code=4404)
            return
    except AuthError:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    websocket.app.state.connections.setdefault(run_id, set()).add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket.app.state.connections.get(run_id, set()).discard(websocket)
