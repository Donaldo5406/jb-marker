"""Provider 래퍼 — 모델 바인딩 + usage 추적 (server.py 클로저에서 추출, spec §8.1).

클로저가 캡처하던 상태(model_map·store·settings)는 전부 생성자 주입으로 치환.
"""
from __future__ import annotations

from ..observability import tracing
from ..observability import usage as usage_log
from .registry import get_provider


def _model_map(settings) -> dict[str, str]:
    return {"anthropic": settings.anthropic_model, "openai": settings.openai_model,
            "google": settings.google_model, "fake": "fake-1"}


class ModelBoundProvider:
    """이름→Provider 해석 + settings 모델 바인딩. complete의 model 인자는 무시하고 강제."""

    def __init__(self, name: str, settings):
        self.name = name  # legal_search.search_and_filter가 provider.name 사용
        self._p = get_provider(name, settings)
        self._model = _model_map(settings).get(name, "fake-1")

    def complete(self, messages, *, model=None, system=None, **kw):
        return self._p.complete(messages, model=self._model, system=system, **kw)

    def generate_image(self, prompt, *, aspect="1:1"):
        return self._p.generate_image(prompt, aspect=aspect)

    def review_image(self, image_bytes, prompt, *, mime="image/png"):
        return self._p.review_image(image_bytes, prompt, mime=mime)


def _msg_dump(messages) -> list[dict]:
    """Message dataclass/dict 혼용 입력을 Langfuse input용 dict 리스트로 정규화."""
    out = []
    for m in messages or []:
        if isinstance(m, dict):
            out.append({"role": m.get("role"), "content": m.get("content")})
        else:
            out.append({"role": getattr(m, "role", None),
                        "content": getattr(m, "content", None)})
    return out


class TrackedProvider:
    """래핑 provider의 각 LLM/이미지 호출 직후 usage 영속."""

    def __init__(self, inner, *, store, run_id: str, step: str, settings) -> None:
        self._inner = inner
        self._store = store
        self._run_id = run_id
        self._step = step
        self._settings = settings
        # legal_search 등이 .name 속성을 검사하므로 노출.
        self.name = getattr(inner, "name", "unknown")

    def _model_for(self, fallback: str | None = None) -> str:
        return getattr(self._inner, "_model", None) or fallback or "unknown"

    def complete(self, messages, *, model=None, system=None, **kw):
        resp = self._inner.complete(messages, model=model, system=system, **kw)
        used_model = getattr(resp, "model", None) or self._model_for()
        entry = usage_log.record_usage(
            self._store, run_id=self._run_id, step=self._step,
            model=used_model, kind="text", usage=getattr(resp, "usage", None),
        )
        tracing.record_generation(
            self._settings, run_id=self._run_id, step=self._step,
            model=used_model, kind="text",
            input_payload={"system": system, "messages": _msg_dump(messages)},
            output_text=getattr(resp, "text", None),
            usage=getattr(resp, "usage", None),
            meta={"cost_usd": entry["cost_usd"]},
        )
        return resp

    def generate_image(self, prompt, *, aspect="1:1"):
        out = self._inner.generate_image(prompt, aspect=aspect)
        used_model = (self._settings.google_image_model if self.name == "google"
                      else self._model_for())
        entry = usage_log.record_usage(
            self._store, run_id=self._run_id, step=self._step,
            model=used_model, kind="image", images=1, meta={"aspect": aspect},
        )
        tracing.record_generation(
            self._settings, run_id=self._run_id, step=self._step,
            model=used_model, kind="image",
            input_payload={"prompt": prompt, "aspect": aspect},
            output_text=f"<image {len(out)} bytes>",
            meta={"cost_usd": entry["cost_usd"]},
        )
        return out

    def review_image(self, image_bytes, prompt, *, mime="image/png"):
        resp = self._inner.review_image(image_bytes, prompt, mime=mime)
        used_model = getattr(resp, "model", None) or self._model_for()
        entry = usage_log.record_usage(
            self._store, run_id=self._run_id, step=self._step,
            model=used_model, kind="vision", usage=getattr(resp, "usage", None),
        )
        tracing.record_generation(
            self._settings, run_id=self._run_id, step=self._step,
            model=used_model, kind="vision",
            input_payload={"prompt": prompt, "mime": mime,
                           "image_bytes": len(image_bytes)},
            output_text=getattr(resp, "text", None),
            usage=getattr(resp, "usage", None),
            meta={"cost_usd": entry["cost_usd"]},
        )
        return resp


def tracked_provider(name: str, settings, *, store, run_id: str, step: str) -> TrackedProvider:
    """주입형 provider 표준 조립 — 모델 바인딩 + usage 추적 (spec §7-2)."""
    return TrackedProvider(ModelBoundProvider(name, settings),
                           store=store, run_id=run_id, step=step, settings=settings)
