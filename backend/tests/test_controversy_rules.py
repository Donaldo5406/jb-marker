"""controversy_rules — 블랙리스트 2티어 결정론 감지."""
from app.core.controversy_rules import load_blacklist, load_visual_symbols, evaluate


def test_load_blacklist_returns_entries():
    entries = load_blacklist()
    assert isinstance(entries, list) and len(entries) >= 15
    assert all("id" in e and "tier" in e and "signals" in e for e in entries)


def test_load_visual_symbols_returns_entries():
    """visual_symbols — RC 경로3(라이브 비전) 프롬프트에 주입되는 도안·제스처 참조 목록.

    텍스트/OCR로 못 잡는 욱일기 '도안'·집게손 '제스처'를 vision LLM이 판별하도록
    name+description+category+severity_hint를 실어야 한다(라이브 전용, 결정론
    매칭 대상 아님 — 여기서는 데이터+로더만 검증한다)."""
    symbols = load_visual_symbols()
    assert isinstance(symbols, list) and len(symbols) > 0
    assert all(
        "name" in s and "description" in s and "category" in s and "severity_hint" in s
        for s in symbols)
    names = [s["name"] for s in symbols]
    assert any("욱일기" in n or "도안" in n for n in names)
    assert any("집게손" in n for n in names)


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


def test_interest_rate_percent_is_not_disaster_date():
    """금리 '5.18%'는 참사 날짜 신호 '5.18'과 부분문자열이 겹치지만 숫자 경계 매칭으로 무탐이어야
    한다(회귀: 예전엔 disaster_518이 critical로 오탐해 정상 은행 마케팅 카피를 하드블록했음)."""
    out = evaluate({"ko": {"headline": "이자율 5.18% 특별판매", "cta": "가입을 축하드립니다"}})
    assert out == []


def test_promo_code_is_not_sewol_date():
    """프로모션 코드 '041678'은 세월호 신호 '0416'을 내장하지만 뒤에 숫자가 이어지므로
    숫자 경계 매칭으로 무탐이어야 한다(회귀: 예전엔 disaster_sewol이 오탐했음)."""
    out = evaluate({"ko": {"body": "이벤트 코드 041678 입력 시 할인"}})
    assert out == []


def test_disaster_518_genuine_date_still_critical_after_boundary_fix():
    """숫자 경계 매칭 도입 후에도 진짜 5·18 날짜 + 탱크 co_signal 조합은 critical을
    유지해야 한다(오탐 수정이 실제 탐지력을 훼손하지 않았는지 확인하는 회귀 가드)."""
    out = evaluate({"ko": {"headline": "5·18 탱크데이 기념 이벤트"}})
    assert out and any(o["severity"] == "critical" for o in out)


def test_real_starbucks_tank_day_5slash18_is_caught():
    """실제 스타벅스 '탱크데이 5/18' 논란 포스터(슬래시 날짜)를 잡는다 — 이 기능의 모티브 케이스."""
    left = evaluate({"ko": {"headline": "책상에 탁! 탱크 데이 5/18",
                            "body": "컬러풀 탱크 텀블러 세트", "cta": "오전 10시 오픈"}})
    right = evaluate({"ko": {"headline": "Tank Day 5/18",
                             "body": "탱크 시리즈 넉넉한 용량", "cta": "상품 보러가기"}})
    assert any(f["severity"] == "critical" for f in left), left
    assert any(f["severity"] == "critical" for f in right), right
