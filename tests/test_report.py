from src import report


TOTALS = {
    "total_value": 0,
    "thb_value": 0,
    "usd_value": 0,
    "usdthb": 33,
    "fx_ok": True,
    "total_pl": 0,
    "total_pl_pct": 0,
}


def test_sec_section_does_not_claim_no_new_reports_when_fetch_failed():
    html = report.render("now", TOTALS, [], [], [], ["r59 2026-06-29"], "29/06/2569", [])

    assert "ตรวจข้อมูล ก.ล.ต. ไม่ครบ" in html
    assert "ไม่มีรายงานใหม่" not in html


def test_stoch_cell_shows_bull_bear_summary_before_numbers():
    rows = [
        {
            "ticker": "PTT.BK",
            "price": 35,
            "currency": "THB",
            "pl": 1,
            "pl_pct": 1,
            "xd_days": None,
            "signals": {
                "d1": {"stoch_k": 50, "stoch_d": 33, "stoch_bias": "bull", "stoch_cross": "up", "rsi": 45},
                "w1": {"stoch_k": 70, "stoch_d": 73, "stoch_bias": "bear", "stoch_cross": "down", "rsi": 55},
            },
        }
    ]

    html = report.render("now", TOTALS, rows, [])

    assert "Stoch" in html
    assert "Bull ↑" in html
    assert "Bear ↓" in html
    assert "K</span>" in html
    assert "/ D</span>" in html
    assert ">50</span>" in html
    assert ">73</span>" in html


def test_stoch_numbers_keep_overbought_oversold_colors():
    rows = [
        {
            "ticker": "PTT.BK",
            "price": 35,
            "currency": "THB",
            "pl": 1,
            "pl_pct": 1,
            "xd_days": None,
            "signals": {
                "d1": {"stoch_k": 85, "stoch_d": 81, "stoch_bias": "bull", "stoch_cross": None, "rsi": 45},
                "w1": {"stoch_k": 15, "stoch_d": 18, "stoch_bias": "bear", "stoch_cross": None, "rsi": 55},
            },
        }
    ]

    html = report.render("now", TOTALS, rows, [])

    assert "#e53935" in html
    assert "#22c55e" in html
    assert ">85</span>" in html
    assert ">18</span>" in html


def test_stoch_bias_wins_over_rounded_numbers_that_tie():
    """K/D ปัดเศษแล้วเท่ากันแต่จริง ๆ ตัดลง -> ต้องขึ้น Bear ↓ ไม่ใช่ Flat"""
    rows = [
        {
            "ticker": "CPNREIT.BK",
            "price": 13.3,
            "currency": "THB",
            "pl": 1,
            "pl_pct": 1,
            "xd_days": None,
            "signals": {
                "d1": {"stoch_k": 90.6, "stoch_d": 90.6, "stoch_bias": "bear", "stoch_cross": "down", "rsi": 45},
                "w1": {"stoch_k": 90.6, "stoch_d": 90.6, "stoch_bias": "bear", "stoch_cross": "down", "rsi": 55},
            },
        }
    ]

    html = report.render("now", TOTALS, rows, [])

    assert "Bear ↓" in html
    assert "Flat" not in html


def test_xd_fetch_failure_is_visible_instead_of_silently_dropping_badge():
    html = report.render("now", TOTALS, [], [], [], [], "", [], ["PTT.BK", "SCB.BK"])

    assert "เช็ควัน XD ไม่ได้ 2 ตัว" in html
    assert "PTT.BK, SCB.BK" in html
