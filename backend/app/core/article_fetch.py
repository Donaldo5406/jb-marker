"""리서치 인용 URL에서 기사 본문을 best-effort로 스크랩한다(실모드용).

브레인스토밍 Stage A의 web_search 인용은 url/title/snippet(한 줄)만 준다. 파일 트리의
research 산출물이 한 줄짜리로 빈약해 보이지 않도록, 가능하면 원문 기사 본문을 긁어 채운다.
의존: httpx(이미 백엔드 의존성). 표준 라이브러리 HTMLParser로 태그를 제거(추가 의존 없음).

실패(타임아웃·비-HTML·네트워크)는 빈 문자열을 돌려 호출부가 snippet으로 폴백하게 한다.
mock 경로는 fixture가 body를 직접 제공하므로 이 함수를 타지 않는다(결정성 보존).
"""
from __future__ import annotations

import logging
import re
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

# 본문에서 제외할 비가시/구조 태그.
_SKIP_TAGS = {"script", "style", "noscript", "head", "nav", "footer", "header", "svg"}
_BLOCK_TAGS = {"p", "div", "section", "article", "li", "br", "h1", "h2", "h3", "h4", "tr"}
_MAX_CHARS = 6000   # 산출물이 비대해지지 않도록 본문 상한.


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip += 1
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip:
            self._skip -= 1
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip and data.strip():
            self.parts.append(data)


def _html_to_text(html: str) -> str:
    p = _TextExtractor()
    try:
        p.feed(html)
    except Exception:
        return ""
    text = "".join(p.parts)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)   # 빈 줄 3개+ → 2개
    return text.strip()


def fetch_article_text(url: str, *, timeout: float = 8.0) -> str:
    """url의 기사 본문 텍스트(태그 제거)를 반환. 실패 시 빈 문자열."""
    if not url or not url.startswith("http"):
        return ""
    try:
        import httpx
        r = httpx.get(url, timeout=timeout, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0 (compatible; JBMarker/1.0)"})
        if r.status_code != 200 or "html" not in r.headers.get("content-type", "").lower():
            return ""
        text = _html_to_text(r.text)
        return text[:_MAX_CHARS] if text else ""
    except Exception:
        logger.debug("article fetch 실패: %s", url, exc_info=True)
        return ""
