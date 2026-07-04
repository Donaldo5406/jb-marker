"""JB 브랜드 지식 팩 로더 — 저변동 계층(identity·palette·tone_hints)만 S1 참조 블록으로 렌더.

products 등 고변동 정보는 여기서 렌더하지 않는다 — 수치·상품 상태의 SSOT는
plan.md 팩트시트와 Stage A 웹리서치(시의성 오류의 구조적 차단, spec 2026-07-04 D2).
팩 부재·파싱 실패는 None 강하 — 파이프라인은 기존 제네릭 동작으로 계속된다."""
import logging
import os

import yaml

log = logging.getLogger(__name__)

_BRAND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "references", "brand")

_HEADER = (
    "[brand_context — JB금융그룹] 아래는 참고용 브랜드 컨텍스트입니다. "
    "사용자 지시와 기획 토큰(tokens)이 항상 우선하며, 이 컨텍스트는 "
    "비어 있는 결정을 채울 때만 참고하세요."
)


def load_brand_pack(brand_id: str = "jb_group") -> dict | None:
    p = os.path.join(_BRAND_DIR, f"{brand_id}.yaml")
    try:
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        return None
    except yaml.YAMLError:
        log.warning("brand pack 파싱 실패(제네릭 동작으로 강하): %s", p)
        return None
    return data if isinstance(data, dict) else None


def render_brand_block(pack: dict | None) -> str | None:
    if not pack:
        return None
    lines: list[str] = []
    ident = pack.get("identity") or {}
    pal = pack.get("palette") or {}
    tone = pack.get("tone_hints") or {}
    if ident.get("ci_concept"):
        lines.append("CI 컨셉: " + " / ".join(ident["ci_concept"]))
    if ident.get("slogan"):
        lines.append(f"슬로건: {ident['slogan']}")
    navy = (pal.get("wordmark_navy") or {}).get("hex")
    blues = pal.get("symbol_blues") or []
    if navy or blues:
        lines.append("브랜드 팔레트(공식 로고 실측): "
                     + " ".join([c for c in [navy, *blues] if c]))
    if tone.get("keywords"):
        lines.append("톤 키워드: " + " · ".join(tone["keywords"]))
    if not lines:
        return None
    return _HEADER + "\n" + "\n".join(lines)
