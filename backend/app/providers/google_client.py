"""GoogleProvider (live) — google-genai SDK."""
from __future__ import annotations

from .base import Message, Provider, ProviderResponse


# gemini-2.5-flash-image(Nano Banana)가 지원하는 종횡비. 그 외 값은 image_config를
# 생략해 모델 에러를 피한다(미지원 비율 전달 시 호출측 try/except가 placeholder 폴백).
_SUPPORTED_ASPECTS = {"1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"}


class GoogleProvider(Provider):
    name = "google"

    def __init__(self, api_key: str | None, *,
                 image_model: str = "gemini-2.5-flash-image") -> None:
        self._api_key = api_key
        self._image_model = image_model

    def complete(self, messages: list[Message], *, model: str | None = None,
                 system: str | None = None, tools: list[dict] | None = None,
                 meta: dict | None = None, **kwargs) -> ProviderResponse:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=self._api_key)
        prompt = (f"{system}\n\n" if system else "") + "\n".join(m.content for m in messages)
        cfg = types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]) if tools else None
        resp = client.models.generate_content(model=model, contents=prompt, config=cfg)
        text = getattr(resp, "text", "") or ""
        citations = []
        try:
            chunks = resp.candidates[0].grounding_metadata.grounding_chunks or []
            for ch in chunks:
                w = getattr(ch, "web", None)
                if w:
                    citations.append({"url": getattr(w, "uri", None), "title": getattr(w, "title", None), "snippet": None})
        except Exception:
            pass
        usage = _extract_google_usage(resp)
        return ProviderResponse(text=text, model=model, raw=resp, citations=citations, usage=usage)

    def generate_image(self, prompt: str, *, aspect: str = "1:1") -> bytes:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=self._api_key)
        full = (f"{prompt}\n\n"
                "CRITICAL: 이미지에 어떤 글자/숫자/로고/워터마크도 렌더하지 마세요. "
                "텍스트는 별도 레이어로 처리됩니다. 배경/키비주얼만 생성.")
        # 종횡비는 프롬프트 텍스트로는 무시되므로 image_config로 전달해야 실제 적용된다
        # (이전엔 항상 1:1 정사각으로 생성돼 4:5 세로 포스터가 깨졌다).
        cfg = None
        if aspect in _SUPPORTED_ASPECTS:
            cfg = types.GenerateContentConfig(
                image_config=types.ImageConfig(aspect_ratio=aspect))
        resp = client.models.generate_content(
            model=self._image_model, contents=full, config=cfg)
        for part in resp.candidates[0].content.parts:
            inline = getattr(part, "inline_data", None)
            if inline and getattr(inline, "data", None):
                return inline.data   # bytes (PNG)
        raise RuntimeError("Nano Banana 응답에 이미지 파트가 없습니다")

    def review_image(self, image_bytes: bytes, prompt: str, *,
                     mime: str = "image/png") -> ProviderResponse:
        """Gemini 멀티모달 호출 — image_bytes + prompt → JSON findings 텍스트.

        spec §9: 라이브 키 부재·SDK 실패 시 RuntimeError raise → caller(T8/T9)가
        try/except로 vision_failed=true setter 호출하도록 위임.
        google-genai SDK 패턴(complete/generate_image와 동일) — types.Part로 이미지 첨부.
        """
        from google import genai
        from google.genai import types
        model_name = "gemini-2.5-flash"
        try:
            client = genai.Client(api_key=self._api_key)
            resp = client.models.generate_content(
                model=model_name,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime),
                    prompt,
                ],
            )
            text = getattr(resp, "text", "") or "{}"
            return ProviderResponse(text=text, model=model_name, raw=resp, usage=_extract_google_usage(resp))
        except Exception as e:
            raise RuntimeError(f"google review_image 실패: {e}") from e


def _extract_google_usage(resp) -> dict | None:
    """google-genai 응답에서 토큰 카운트 추출 (usage_metadata.prompt/candidates_token_count)."""
    u = getattr(resp, "usage_metadata", None)
    if u is None:
        return None
    return {
        "input_tokens": int(getattr(u, "prompt_token_count", 0) or 0),
        "output_tokens": int(getattr(u, "candidates_token_count", 0) or 0),
    }
