"""FastAPI 앱 — 헬스 + runs + VFS CRUD + 게이트웨이 + WS _publish."""
from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from . import entitlement
from .auth import make_user_id_dep
from .config import load_settings
from .deploy.adapters.base import Package, ScheduleSpec
from .deploy.adapters.registry import get_adapter
from .deploy.eligibility import build_eligibility
from .deploy.ledger import load_ledger
from .deploy.packager import package_channel
from .deploy.providers import get_provider as get_deploy_provider
from .deploy.rules_engine import load_policies
from .gateway.gateway import MarkerGateway
from .gateway.harness import HarnessRequest, PassthroughHarness
from .gateway.harness_advisor import AdvisorHarness
from .gateway.harness_brainstorming import BrainstormingHarness
from .gateway.harness_design import DesignHarness
from .history.gallery import build_gallery
from .history.preview import build_preview_html
from .observability import usage as usage_log
from .providers.registry import get_provider
from .vfs.factory import get_vfs_store


class RunCreate(BaseModel):
    title: str | None = None
    languages: list[str] = []


class GatewayRun(BaseModel):
    run_id: str
    studio: str
    prompt: str
    provider: str = "fake"
    is_marker: bool = False
    answer: str | None = None
    bypass: bool = False
    action: str | None = None


class PutText(BaseModel):
    content: str
    mime: str | None = None
    # "base64" → 백엔드가 디코드해 bytes로 저장 (PNG 등 바이너리 라운드트립용)
    content_encoding: str | None = None


class EntitlementPut(BaseModel):
    marker: bool


# === M6 DeployStudio request bodies ===
class DeploySetupBody(BaseModel):
    selected_providers: list[str]
    languages: list[str]


class DeployPackageBody(BaseModel):
    channel: str
    lang: str
    original_copy: str
    visual_path: str


class AdvisorChatBody(BaseModel):
    package_id: str
    message: str


class DispatchBody(BaseModel):
    confirmed: bool = False


def _node_dict(n) -> dict[str, Any]:
    return {"path": n.path, "mime": n.mime, "source": n.source,
            "content_text": n.content_text, "meta": n.meta}


def _require_run_owner_factory(store):
    """run 소유권 가드. 소유자 불일치/부재 → 404(존재 노출 회피)."""
    from fastapi import HTTPException

    def _guard(run_id: str, user_id: str):
        m = store.get_manifest(run_id)
        if m is None or m.user_id != user_id:
            raise HTTPException(404, "run not found")
        return m
    return _guard


def create_app() -> FastAPI:
    app = FastAPI(title="JB Marker API")
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    settings = load_settings()
    store = get_vfs_store(settings)

    user_id_dep = make_user_id_dep(settings)
    require_owner = _require_run_owner_factory(store)

    from .entitlement import set_store
    from .entitlement_store import get_entitlement_store
    set_store(get_entitlement_store(settings))

    # provider_factory: settings의 모델 매핑 주입
    model_map = {"anthropic": settings.anthropic_model, "openai": settings.openai_model,
                 "google": settings.google_model, "fake": "fake-1"}

    class _ModelBoundProvider:
        def __init__(self, name: str):
            self.name = name  # legal_search.search_and_filter가 provider.name 사용
            self._p = get_provider(name, settings)
            self._model = model_map.get(name, "fake-1")

        def complete(self, messages, *, model=None, system=None, **kw):
            return self._p.complete(messages, model=self._model, system=system, **kw)

        def generate_image(self, prompt, *, aspect="1:1"):
            return self._p.generate_image(prompt, aspect=aspect)

        def review_image(self, image_bytes, prompt, *, mime="image/png"):
            return self._p.review_image(image_bytes, prompt, mime=mime)

    class _TrackedProvider:
        """ModelBoundProvider wrapper — 각 LLM/이미지 호출 직후 usage 영속."""

        def __init__(self, inner, *, run_id: str, step: str) -> None:
            self._inner = inner
            self._run_id = run_id
            self._step = step
            # legal_search 등이 .name 속성을 검사하므로 노출.
            self.name = getattr(inner, "name", "unknown")

        def _model_for(self, fallback: str | None = None) -> str:
            return getattr(self._inner, "_model", None) or fallback or "unknown"

        def complete(self, messages, *, model=None, system=None, **kw):
            resp = self._inner.complete(messages, model=model, system=system, **kw)
            usage_log.record_usage(
                store, run_id=self._run_id, step=self._step,
                model=getattr(resp, "model", None) or self._model_for(),
                kind="text", usage=getattr(resp, "usage", None),
            )
            return resp

        def generate_image(self, prompt, *, aspect="1:1"):
            out = self._inner.generate_image(prompt, aspect=aspect)
            usage_log.record_usage(
                store, run_id=self._run_id, step=self._step,
                model="gemini-2.5-flash-image" if self.name == "google" else self._model_for(),
                kind="image", images=1, meta={"aspect": aspect},
            )
            return out

        def review_image(self, image_bytes, prompt, *, mime="image/png"):
            resp = self._inner.review_image(image_bytes, prompt, mime=mime)
            usage_log.record_usage(
                store, run_id=self._run_id, step=self._step,
                model=getattr(resp, "model", None) or self._model_for(),
                kind="vision", usage=getattr(resp, "usage", None),
            )
            return resp

    def _wrap_for_usage(provider, req):
        return _TrackedProvider(provider, run_id=req.run_id, step=req.studio or "gateway")

    entitlement_state = {"marker": settings.entitlement_override}
    gateway = MarkerGateway(store,
                            entitlement_override=lambda: entitlement_state["marker"],
                            provider_factory=_ModelBoundProvider,
                            wrap_provider=_wrap_for_usage)

    connections: dict[str, set[WebSocket]] = {}

    async def _publish(run_id: str, event: dict) -> None:
        for ws in list(connections.get(run_id, set())):
            try:
                await ws.send_json(event)
            except Exception:
                connections.get(run_id, set()).discard(ws)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/entitlement")
    def get_entitlement() -> dict:
        return {"marker": entitlement_state["marker"]}

    @app.put("/entitlement")
    def put_entitlement(body: EntitlementPut) -> dict:
        entitlement_state["marker"] = body.marker
        return {"marker": entitlement_state["marker"]}

    @app.post("/runs")
    def create_run(body: RunCreate, user_id: str = Depends(user_id_dep)) -> dict:
        run_id = uuid.uuid4().hex[:12]
        m = store.create_run(run_id, user_id=user_id, title=body.title, languages=body.languages)
        return {"run_id": m.run_id, "title": m.title}

    @app.get("/runs")
    def list_runs(user_id: str = Depends(user_id_dep)) -> dict:
        runs = store.list_runs(user_id=user_id)
        return {"runs": [{"run_id": m.run_id, "title": m.title,
                          "created_at": m.created_at,
                          "step_status": m.step_status} for m in runs]}

    @app.post("/gateway/run")
    async def gateway_run(body: GatewayRun, user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(body.run_id, user_id)
        req = HarnessRequest(run_id=body.run_id, studio=body.studio,
                             user_prompt=body.prompt, provider=body.provider,
                             is_marker=body.is_marker, answer=body.answer, bypass=body.bypass,
                             action=body.action)
        if body.studio == "brainstorming" and body.is_marker:
            harness = BrainstormingHarness()
        elif body.studio == "design" and body.is_marker:
            harness = DesignHarness(image_provider=_ModelBoundProvider("google"))
        elif body.studio == "review" and body.is_marker:
            from .gateway.harness_review import ReviewHarness
            harness = ReviewHarness(vision_provider=_ModelBoundProvider("google"))
        else:
            harness = PassthroughHarness()
        try:
            result = gateway.run(req, harness)
        except PermissionError as e:
            raise HTTPException(402, str(e))
        for ev in result.events:
            await _publish(body.run_id, ev)
        ask = None
        if result.ask is not None:
            ask = {"trigger": result.ask.trigger, "question": result.ask.question, "options": result.ask.options}
        return {"output_path": result.output_path, "text": result.text,
                "ask": ask, "meta": result.meta}

    @app.get("/vfs/{run_id}")
    def vfs_list(run_id: str, prefix: str | None = None,
                 user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(run_id, user_id)
        nodes = store.list(prefix or f"/{run_id}")
        return {"nodes": [_node_dict(n) for n in nodes]}

    @app.get("/vfs/{run_id}/{rest:path}")
    def vfs_get(run_id: str, rest: str, user_id: str = Depends(user_id_dep)):
        require_owner(run_id, user_id)
        node = store.get(f"/{run_id}/{rest}")
        if node is None:
            raise HTTPException(404, "노드 없음")
        if node.blob is not None or node.blob_path is not None:
            # node.blob 은 store.get()이 이미 로드함(Local·Supabase 공통) — 재조회 불필요.
            return Response(content=node.blob or b"", media_type=node.mime or "application/octet-stream")
        return _node_dict(node)

    @app.put("/vfs/{run_id}/{rest:path}")
    def vfs_put(run_id: str, rest: str, body: PutText,
                user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(run_id, user_id)
        mime = body.mime or ("application/json" if rest.endswith(".json") else "text/markdown")
        # base64 인코딩 본문이면 bytes로 디코드해 저장 (PNG 등 바이너리 라운드트립).
        # 미지정 시 기존 텍스트 경로 유지(하위호환).
        if body.content_encoding == "base64":
            import base64
            try:
                raw = base64.b64decode(body.content, validate=True)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"base64 decode failed: {e}")
            node = store.put(f"/{run_id}/{rest}", raw, source="frontend", mime=mime)
        else:
            node = store.put(f"/{run_id}/{rest}", body.content, source="user", mime=mime)
        return _node_dict(node)

    # === M6 DeployStudio routes ===
    @app.post("/runs/{run_id}/deploy/setup")
    def deploy_setup(run_id: str, body: DeploySetupBody,
                     user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(run_id, user_id)
        matrix = [{"channel": p, "lang": l}
                  for p in body.selected_providers for l in body.languages]
        store.put_text(
            f"/{run_id}/deploy/inputs/selected_providers.json",
            json.dumps(body.selected_providers, ensure_ascii=False),
        )
        store.put_text(
            f"/{run_id}/deploy/inputs/matrix.json",
            json.dumps(matrix, ensure_ascii=False),
        )
        store.set_step_status(run_id, "deploy", "in_progress")
        return {"matrix": matrix, "step_status": "in_progress"}

    @app.post("/runs/{run_id}/deploy/eligibility")
    def deploy_eligibility(run_id: str, user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(run_id, user_id)
        ledger = load_ledger()
        policies = load_policies()
        result = build_eligibility(ledger, policies, send_hour=10)
        # rules_engine.evaluate_recipient: primary["all_blocks"] = blocks
        # where blocks contains primary → 자기참조. 직렬화 전 단일 단계만 펼친다.
        sanitized_excluded = []
        for ex in result["excluded"]:
            flat_blocks = [
                {k: v for k, v in b.items() if k != "all_blocks"}
                for b in ex.get("all_blocks", [])
            ]
            sanitized_excluded.append({
                **{k: v for k, v in ex.items() if k != "all_blocks"},
                "all_blocks": flat_blocks,
            })
        store.put_text(
            f"/{run_id}/deploy/eligibility/recipients.json",
            json.dumps(result["recipients"], ensure_ascii=False),
        )
        store.put_text(
            f"/{run_id}/deploy/eligibility/excluded.json",
            json.dumps(sanitized_excluded, ensure_ascii=False),
        )
        store.put_text(
            f"/{run_id}/deploy/eligibility/calendar.json",
            json.dumps(result["calendar"], ensure_ascii=False),
        )
        return {
            "total": result["total"],
            "eligible_count": result["eligible_count"],
            "excluded_count": len(result["excluded"]),
        }

    @app.post("/runs/{run_id}/deploy/packages")
    def deploy_packages(run_id: str, body: DeployPackageBody,
                        user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(run_id, user_id)
        provider = get_deploy_provider(body.channel)
        pkg = package_channel(
            channel=body.channel,
            lang=body.lang,
            original_copy=body.original_copy,
            provider=provider,
            visual_path=body.visual_path,
        )
        package_id = f"{body.channel}_{body.lang}"
        if pkg["status"] == "ok":
            store.put_text(
                f"/{run_id}/deploy/packages/{package_id}/copy.md",
                pkg["copy_text"],
            )
        store.put_text(
            f"/{run_id}/deploy/packages/{package_id}/copy.meta.json",
            json.dumps(pkg, ensure_ascii=False),
        )
        store.put_text(
            f"/{run_id}/deploy/packages/{package_id}/package.meta.json",
            json.dumps(
                {
                    "channel": body.channel,
                    "lang": body.lang,
                    "spec_id": provider.id,
                    "adapter_status": provider.adapter_status,
                },
                ensure_ascii=False,
            ),
        )
        return {"package_id": package_id, "status": pkg["status"], "reason": pkg.get("reason")}

    class _ScriptedAdvisorProvider:
        """AdvisorHarness 계약(.chat) 충족용 데모 advisor — ctx·channel 주입.

        키워드(압축·짧·줄여·shorten·shorter·compress) 감지 시 채널 한도에 맞게
        원본을 공백 단위 truncate(부분집합 보장) → write_d2_copy tool_call.
        실 LLM 배선은 M7 또는 ANTHROPIC_API_KEY 도입 시 별도 wrapper로 교체.
        """

        SHORTEN_KEYWORDS = ("압축", "짧", "줄여", "shorten", "shorter", "compress")
        LIMITS = {"sms": 90, "email": 600, "kakao": 1000, "naver": 400, "google": 400, "instagram": 400}

        def __init__(self, *, ctx: dict, channel: str) -> None:
            self._ctx = ctx
            self._channel = channel

        def chat(self, *, system, messages, tools):
            last = messages[-1].get("content", "") if messages else ""
            wants_short = any(k in last for k in self.SHORTEN_KEYWORDS) or any(k in last.lower() for k in ("shorten", "shorter", "compress"))
            original = self._ctx.get("original_text", "")
            if wants_short and original:
                limit = self.LIMITS.get(self._channel, 90)
                tokens = original.split()
                adapted = ""
                for tok in tokens:
                    candidate = (adapted + " " + tok).strip() if adapted else tok
                    if len(candidate) > limit:
                        break
                    adapted = candidate
                return {
                    "text": f"원본 {len(original)}자 → {self._channel} 한도 {limit}자에 맞게 다듬었습니다.",
                    "tool_calls": [{"name": "write_d2_copy", "input": {"adapted_text": adapted}}],
                }
            return {
                "text": f"카드 컨텍스트를 불러왔어요. '{last}'에 대해 더 구체적으로 말씀해 주시면 카피를 다듬어 드릴게요.",
                "tool_calls": [],
            }

    def _make_advisor_provider(ctx: dict, channel: str):
        """advisor_mode 분기 — auto: 키 있으면 live, scripted: 강제 scripted, live: 키 필수.

        실LLM 배선 실패(SDK import / 호출 예외)는 호출부에서 잡아 422로 변환.
        """
        mode = settings.advisor_mode
        has_key = bool(settings.anthropic_api_key)
        if mode == "live" or (mode == "auto" and has_key):
            if not has_key:
                raise HTTPException(422, "ADVISOR_MODE=live but ANTHROPIC_API_KEY is empty")
            from .deploy.advisor.live import AnthropicAdvisorProvider
            return AnthropicAdvisorProvider(
                api_key=settings.anthropic_api_key,
                model=settings.anthropic_advisor_model,
                ctx=ctx,
                channel=channel,
            )
        return _ScriptedAdvisorProvider(ctx=ctx, channel=channel)

    @app.post("/runs/{run_id}/deploy/advisor/chat")
    def deploy_advisor_chat(run_id: str, body: AdvisorChatBody,
                            user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(run_id, user_id)
        if not entitlement.check(user_id):
            raise HTTPException(402, "Payment required (entitlement)")
        ctx_raw = store.get_text(f"/{run_id}/deploy/packages/{body.package_id}/copy.meta.json")
        ctx = json.loads(ctx_raw) if ctx_raw else {}
        channel = body.package_id.split("_", 1)[0] if "_" in body.package_id else "sms"
        provider = _make_advisor_provider(ctx, channel)
        h = AdvisorHarness(provider=provider, vfs_store=store, run_id=run_id)
        result = h.handle_turn(package_id=body.package_id, user_message=body.message)
        # advisor live LLM이 usage 노출 시 영속(scripted는 _usage 없음 → skip).
        if "_usage" in result:
            usage_log.record_usage(
                store, run_id=run_id, step="advisor",
                model=result.get("_model") or settings.anthropic_advisor_model,
                kind="text", usage=result["_usage"],
                meta={"package_id": body.package_id},
            )
        return result

    @app.get("/runs/{run_id}/usage")
    def get_usage(run_id: str, user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(run_id, user_id)
        return usage_log.summarize(store, run_id=run_id)

    @app.get("/runs/{run_id}/gallery")
    def get_gallery(run_id: str, user_id: str = Depends(user_id_dep)) -> dict:
        man = require_owner(run_id, user_id)
        nodes = store.list(f"/{run_id}")
        return build_gallery(man, nodes)

    @app.get("/runs/{run_id}/preview")
    def get_preview(run_id: str, user_id: str = Depends(user_id_dep)):
        require_owner(run_id, user_id)
        markup = build_preview_html(run_id, store)
        return Response(content=markup, media_type="text/html")

    @app.post("/runs/{run_id}/deploy/dispatch")
    def deploy_dispatch(run_id: str, body: DispatchBody,
                        user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(run_id, user_id)
        if not body.confirmed:
            raise HTTPException(400, "user confirm required")
        if not entitlement.check(user_id):
            raise HTTPException(402, "Payment required (entitlement)")

        selected = json.loads(
            store.get_text(f"/{run_id}/deploy/inputs/selected_providers.json") or "[]"
        )
        recipients = json.loads(
            store.get_text(f"/{run_id}/deploy/eligibility/recipients.json") or "[]"
        )
        if len(recipients) == 0:
            raise HTTPException(400, "no eligible recipients")
        if len(selected) == 0:
            raise HTTPException(400, "no provider selected")

        matrix = json.loads(store.get_text(f"/{run_id}/deploy/inputs/matrix.json") or "[]")
        plan = {"send_hour": 10, "channels": selected, "recipients_count": len(recipients)}
        simulation: list[dict] = []
        for cell in matrix:
            adapter = get_adapter(cell["channel"])
            copy_meta_raw = store.get_text(
                f"/{run_id}/deploy/packages/{cell['channel']}_{cell['lang']}/copy.meta.json"
            )
            if not copy_meta_raw:
                continue
            meta = json.loads(copy_meta_raw)
            if meta.get("status") == "needs_advisor" and meta.get("grounding_check") != "ok":
                simulation.append({
                    "channel": cell["channel"], "lang": cell["lang"],
                    "status": "skipped",
                    "reason": "grounding_fail or needs_advisor",
                })
                continue
            pkg = Package(
                channel=cell["channel"],
                lang=cell["lang"],
                visual_path=meta.get("visual_path", ""),
                copy_text=meta.get("copy_text", meta.get("adapted_text", "")),
                meta=meta,
            )
            recs_for_lang = [r for r in recipients if r["lang"] == cell["lang"]]
            res = adapter.dispatch(cell["channel"], pkg, ScheduleSpec(send_hour=10), recs_for_lang)
            simulation.append({
                "channel": cell["channel"], "lang": cell["lang"],
                "status": res.status, "message": res.message,
                "recipients_count": res.recipients_count,
            })

        store.put_text(
            f"/{run_id}/deploy/dispatch/plan.json",
            json.dumps(plan, ensure_ascii=False),
        )
        store.put_text(
            f"/{run_id}/deploy/dispatch/simulation.json",
            json.dumps(simulation, ensure_ascii=False),
        )

        report = (
            f"# Deploy Report\n\n## Eligibility\n- Eligible: {len(recipients)}\n\n"
            f"## Channels\n{json.dumps(simulation, ensure_ascii=False, indent=2)}\n"
        )
        store.put_text(f"/{run_id}/deploy/report.md", report)
        store.set_step_status(run_id, "deploy", "PASS")
        return {"step_status": "PASS", "simulation": simulation}

    @app.post("/runs/{run_id}/deploy/demo-payment")
    def deploy_demo_payment(run_id: str, user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(run_id, user_id)
        entitlement.set_dev_pass(user_id)
        return {"dev_pass": True}

    @app.get("/runs/{run_id}/deploy/_state")
    def deploy_state(run_id: str, user_id: str = Depends(user_id_dep)) -> dict:
        m = require_owner(run_id, user_id)
        return {
            "step_status": m.step_status.get("deploy", "idle"),
            "selected_providers": json.loads(
                store.get_text(f"/{run_id}/deploy/inputs/selected_providers.json") or "[]"
            ),
            "matrix": json.loads(
                store.get_text(f"/{run_id}/deploy/inputs/matrix.json") or "[]"
            ),
            "dev_pass": entitlement.check(user_id),
        }

    @app.websocket("/ws/{run_id}")
    async def ws(websocket: WebSocket, run_id: str):
        token = websocket.query_params.get("token")
        from .auth import resolve_user_id, AuthError
        try:
            uid = resolve_user_id(f"Bearer {token}" if token else None, settings)
            m = store.get_manifest(run_id)
            if m is None or m.user_id != uid:
                await websocket.close(code=4404)
                return
        except AuthError:
            await websocket.close(code=4401)
            return
        await websocket.accept()
        connections.setdefault(run_id, set()).add(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            connections.get(run_id, set()).discard(websocket)

    return app


app = create_app()
