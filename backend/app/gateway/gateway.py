"""MarkerGateway — 모든 AI 호출의 경유점.

흐름: 엔타이틀먼트 검사 → 하네스 조립 → provider 호출 → VFS 영속(+meta.grounds) → 결과.
raw 프롬프트 직행 금지: 항상 하네스(최소 Passthrough) + 게이트웨이 경유.
"""
from __future__ import annotations

from typing import Callable

from ..providers.base import Provider
from ..vfs.base import VfsStore
from .entitlement import check_entitlement
from .harness import Harness, HarnessRequest, HarnessResult


class MarkerGateway:
    def __init__(self, store: VfsStore, *,
                 entitlement_override: "bool | Callable[[], bool]",
                 provider_factory: Callable[[str], Provider]) -> None:
        self._store = store
        self._override = entitlement_override
        self._provider_factory = provider_factory

    def run(self, req: HarnessRequest, harness: Harness) -> HarnessResult:
        override = self._override() if callable(self._override) else self._override
        check_entitlement(is_marker=req.is_marker, override=override)
        system, messages = harness.build_messages(req)
        system = system or harness.system_prompt()
        provider = self._provider_factory(req.provider)
        resp = provider.complete(messages, model=req.provider, system=system)
        text = harness.critic(resp.text)
        source = "marker" if req.is_marker else "raw"
        meta = {"source": source, "provider": req.provider, "grounds": []}
        path = harness.output_path(req)
        self._store.put(path, text, meta=meta, source=source, mime="text/markdown")
        return HarnessResult(text=text, output_path=path, meta=meta)
