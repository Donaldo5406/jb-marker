"""GoogleProvider (live) — google-genai SDK."""
from __future__ import annotations

from .base import Message, Provider, ProviderResponse


# gemini-2.5-flash-image(Nano Banana)가 지원하는 종횡비. 그 외 값은 image_config를
# 생략해 모델 에러를 피한다(미지원 비율 전달 시 호출측 try/except가 placeholder 폴백).
_SUPPORTED_ASPECTS = {"1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"}

# Veo가 지원하는 종횡비(보수적). 그 외는 config 생략(generate_image 전례).
_SUPPORTED_VIDEO_ASPECTS = {"9:16", "16:9", "1:1"}


class GoogleProvider(Provider):
    name = "google"

    def __init__(self, api_key: str | None, *,
                 image_model: str = "gemini-3-pro-image") -> None:
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

    def generate_image(self, prompt: str, *, aspect: str = "1:1",
                       image: bytes | None = None) -> bytes:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=self._api_key)
        # 종횡비는 프롬프트 텍스트로는 무시되므로 image_config로 전달해야 실제 적용된다
        # (이전엔 항상 1:1 정사각으로 생성돼 4:5 세로 포스터가 깨졌다).
        cfg = None
        if aspect in _SUPPORTED_ASPECTS:
            cfg = types.GenerateContentConfig(
                image_config=types.ImageConfig(aspect_ratio=aspect))
        # image 주어지면 image-to-image 편집(입력 이미지 Part를 prompt 앞에 둔다).
        # 프롬프트는 호출측이 소유 — 여기서 글자금지 등 suffix를 덧붙이지 않는다.
        if image is not None:
            contents = [types.Part.from_bytes(data=image, mime_type="image/png"), prompt]
        else:
            contents = prompt
        resp = client.models.generate_content(
            model=self._image_model, contents=contents, config=cfg)
        for part in resp.candidates[0].content.parts:
            inline = getattr(part, "inline_data", None)
            if inline and getattr(inline, "data", None):
                return inline.data   # bytes (PNG)
        raise RuntimeError("Nano Banana 응답에 이미지 파트가 없습니다")

    def generate_video(self, prompt: str, *, aspect: str = "9:16",
                       duration_sec: int = 15, fps: int = 30,
                       video_model: str = "veo-3.0-generate-001") -> bytes:
        import time
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=self._api_key)
        full = (
            "프리미엄 금융 브랜드 광고용 시네마틱 영상입니다. 추상 배경이 아니라 "
            "실제 광고 같은 장면(인물·표정·제품 사용·공간·자연스러운 동작)을 "
            "영화적 조명·카메라 무빙·얕은 심도·고급 무드로 연출하세요.\n\n"
            f"{prompt}\n\n"
            "CRITICAL: 영상에 어떤 글자/숫자/로고/워터마크도 렌더하지 마세요. "
            "특히 인물이 든 폰·노트북·태블릿 등 기기 화면은 카메라에 보이지 않게 하거나 "
            "꺼진/블랭크 상태로 두고, 화면 속 앱·UI·텍스트를 절대 만들지 마세요"
            "(가짜 잔글씨가 광고 품질을 망칩니다). 가능하면 화면이 보이지 않는 연출을 택하세요. "
            "텍스트·로고는 후속 레이어로 합성됩니다. 장면 자체를 광고 품질로 생성하세요."
        )
        # Veo는 generate_videos(long-running operation). 미지원 aspect는 config 생략.
        cfg = (types.GenerateVideosConfig(aspect_ratio=aspect)
               if aspect in _SUPPORTED_VIDEO_ASPECTS else None)
        op = client.models.generate_videos(model=video_model, prompt=full, config=cfg)
        while not getattr(op, "done", False):
            time.sleep(5)
            op = client.operations.get(op)
        videos = getattr(getattr(op, "response", None), "generated_videos", None) or []
        for gv in videos:
            v = getattr(gv, "video", None)
            if v is None:
                continue
            data = getattr(v, "video_bytes", None)
            # Veo는 영상을 파일 uri로 반환한다(video_bytes는 비어 옴) — files.download로 채운다.
            if not data and getattr(v, "uri", None):
                client.files.download(file=v)
                data = getattr(v, "video_bytes", None)
            if data:
                return data
        raise RuntimeError("Veo 응답에 영상 파트가 없습니다")

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
