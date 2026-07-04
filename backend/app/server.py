"""FastAPI 앱 팩토리 — 조립 전용. 전 라우트는 routers/ (P4 §8.1 분해 완료)."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

from . import entitlement
from .config import load_settings
from .gateway.gateway import MarkerGateway
from .observability import tracing
from .providers.wrappers import ModelBoundProvider, TrackedProvider
from .routers import deploy as deploy_router
from .routers import gateway as gateway_router
from .routers import history as history_router
from .routers import meta as meta_router
from .routers import observability as observability_router
from .routers import runs as runs_router
from .routers import session as session_router
from .routers import vfs as vfs_router
# re-export — test_owner_guard가 app.server 경유로 import (행동 보존)
from .routers.deps import require_owner_factory as _require_run_owner_factory  # noqa: F401
from .session.liveness import Thresholds
from .session.store import SessionStore
from .vfs.factory import get_vfs_store


def _log_render_readiness() -> None:
    """부팅 시 영상 렌더 환경(ffmpeg·CJK 폰트) 건강을 로그로 노출한다.

    라이브 데모 전에 배포 로그만 보고 렌더 가능 여부를 알 수 있게 — 그러지 않으면
    ffmpeg/폰트 부재를 렌더 순간에야 stub 폴백으로 알게 된다(조용한 실패). 로그 전용이라
    부팅을 절대 막지 않는다(예외는 삼킴)."""
    try:
        from .gateway.video.render import _AUTO, _resolve_ffmpeg, _resolve_font
        ff = _resolve_ffmpeg(_AUTO)
        font = _resolve_font()
        if not ff:
            logger.warning("렌더 준비 경고: ffmpeg 미탐지 → 영상이 stub로 폴백됩니다. "
                           "라이브 렌더에는 ffmpeg 설치가 필요합니다.")
        elif not font:
            logger.warning("렌더 준비: ffmpeg=%s, 그러나 CJK(한글) 폰트 미탐지 → "
                           "자막 한글이 깨질 수 있습니다.", ff)
        else:
            logger.info("렌더 준비 OK: ffmpeg=%s, CJK폰트=%s", ff, font)
    except Exception as e:                       # 헬스 로그는 부팅을 막지 않는다
        logger.warning("렌더 준비 점검 실패(무시): %s", e)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    _log_render_readiness()                      # 부팅 시 렌더 환경 건강 로그(A3)
    yield
    # HF Spaces 컨테이너 종료 시 Langfuse 배치 유실 방지
    tracing.flush()


def create_app() -> FastAPI:
    app = FastAPI(
        lifespan=_lifespan,
        title="JB Marker API",
        version="0.4.0",  # pyproject.toml version과 동기 유지
        description="JB marker 마케팅 스튜디오 백엔드 — brainstorming/design/review 하네스 게이트웨이 + VFS + deploy.",
        openapi_tags=[
            {"name": "meta", "description": "헬스체크·엔타이틀먼트"},
            {"name": "runs", "description": "run 수명주기"},
            {"name": "gateway", "description": "하네스 게이트웨이 (GateEnvelope 봉투 반환)"},
            {"name": "session", "description": "세션 liveness (UI 미연결 — 헤드리스 계약)"},
            {"name": "vfs", "description": "run 파일시스템 CRUD"},
            {"name": "deploy", "description": "배포 스튜디오 — 패키징·어드바이저·디스패치"},
            {"name": "observability", "description": "usage 집계"},
            {"name": "history", "description": "갤러리·프리뷰"},
        ],
    )
    settings = load_settings()
    if settings.sentry_dsn:
        try:
            import sentry_sdk
            # FastAPI/Starlette 통합 자동 활성 — 미처리 예외 캡처.
            # APM·PII는 spec Non-goal: traces 0, default PII 끔.
            sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.0,
                            send_default_pii=False)
        except Exception:
            pass  # 관측성 실패가 부팅을 막지 않는다
    # 분리형 배포: env로 명시한 origin(예: https://*.vercel.app) 화이트리스트 +
    # localhost regex 폴백. allow_credentials=True라 wildcard("*") 불가 → 명시 리스트.
    _dev_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    _origins = list(settings.cors_allow_origins) or _dev_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    store = get_vfs_store(settings)

    session_store = SessionStore(store, Thresholds(
        stall_ms=settings.session_stall_ms,
        suspend_ms=settings.session_suspend_ms,
        retention_ms=settings.session_retention_ms,
    ))

    # 라우터 공유 상태 — 모듈 싱글턴 금지, 전부 app.state 경유 (spec §8.1)
    app.state.settings = settings
    app.state.store = store
    app.state.session_store = session_store

    app.include_router(meta_router.router)
    app.include_router(runs_router.router)
    app.include_router(session_router.router)
    app.include_router(vfs_router.router)
    app.include_router(observability_router.router)
    app.include_router(history_router.router)
    app.include_router(deploy_router.router)

    from .entitlement import set_store
    from .entitlement_store import get_entitlement_store
    set_store(get_entitlement_store(settings))
    entitlement.set_override_source(lambda: settings.entitlement_override)

    # provider_factory: settings의 모델 매핑 주입
    def _provider_factory(name: str):
        return ModelBoundProvider(name, settings)

    def _wrap_for_usage(provider, req):
        tracing.tag_run(req.run_id, settings)
        return TrackedProvider(provider, store=store, run_id=req.run_id,
                               step=req.studio or "gateway", settings=settings)

    # connections(run_id→WebSocket set)·gateway는 routers/gateway.py가
    # app.state 경유로 공유 — 이벤트 릴레이와 WS 수명주기가 같은 dict를 본다.
    app.state.connections = {}
    app.state.gateway = MarkerGateway(store,
                                      entitlement_check=entitlement.is_entitled,
                                      provider_factory=_provider_factory,
                                      wrap_provider=_wrap_for_usage)

    app.include_router(gateway_router.router)

    return app


app = create_app()
