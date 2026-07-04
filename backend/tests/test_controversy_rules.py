"""controversy_rules — 블랙리스트 2티어 결정론 감지."""
from app.core.controversy_rules import load_blacklist, evaluate


def test_load_blacklist_returns_entries():
    entries = load_blacklist()
    assert isinstance(entries, list) and len(entries) >= 15
    assert all("id" in e and "tier" in e and "signals" in e for e in entries)


def test_tier1_slur_alone_is_critical():
    """Tier-1(사전 미등재 슬러 '짱깨')은 단독 신호만으로 critical."""
    out = evaluate({"ko": {"headline": "짱깨 어쩌고"}})
    assert out and out[0]["severity"] == "critical"
    assert out[0]["location"] == {"slot": "controversy", "lang": "ko"}


def test_tier1_symbol_alone_is_critical():
    """Tier-1 상징(욱일기)도 단독 critical, category=other_sensitive."""
    out = evaluate({"ko": {"headline": "욱일기 느낌의 배경"}})
    assert out and out[0]["severity"] == "critical"
    assert out[0]["category"] == "other_sensitive"


def test_tier2_needs_combination():
    """Tier-2(홍어=음식, 사전 표제어)는 지역 co_signal 결합 시에만 warning."""
    combo = evaluate({"ko": {"headline": "전라도 홍어 종자들"}})
    assert combo and combo[0]["severity"] == "warning"
    assert combo[0]["category"] == "other_sensitive"


def test_tier2_single_signal_is_clean():
    """Tier-2 단독 신호는 무탐 — 음식 '홍어'·지명 '전라도'만은 통과(중립어 오탐 방지)."""
    assert evaluate({"ko": {"body": "홍어 초밥 맛집 추천"}}) == []
    assert evaluate({"ko": {"body": "전라도 지점 신규 오픈"}}) == []


def test_disaster_date_combo_is_critical():
    """참사 날짜(5·18) + 경솔 모티프(탱크) 결합 → critical(스타벅스 탱크데이류)."""
    out = evaluate({"ko": {"headline": "5·18 탱크데이 기념 이벤트"}})
    assert out and any(o["severity"] == "critical" for o in out)


def test_clean_copy_no_findings():
    """clean 카피는 무탐(중립성·오탐 가드)."""
    assert evaluate({"ko": {"headline": "쉽고 빠른 정기예금", "cta": "지금 가입"}}) == []


def test_finding_carries_evidence_and_no_political_label():
    out = evaluate({"ko": {"headline": "1488 캠페인"}})
    assert out and out[0]["severity"] == "critical"
    # 근거(why_risky) 포함, 정치 진영 라벨링 없음
    assert "극단주의" in out[0]["evidence"]
