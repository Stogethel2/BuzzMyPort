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


def _row(changes=None):
    row = {
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
    if changes is not None:
        row["changes"] = changes
    return row


def test_price_cell_shows_three_horizons_without_pushing_out_momentum():
    html = report.render("now", TOTALS, [_row({"d1": 1.2, "w1": -3.4, "m1": 8.1})], [])

    assert "+1.2%" in html and "-3.4%" in html and "+8.1%" in html
    assert "Bull ↑" in html and "Bear ↓" in html  # momentum ต้องอยู่ครบเหมือนเดิม
    assert ">50</span>" in html


def test_missing_horizon_shows_dash_not_zero():
    html = report.render("now", TOTALS, [_row({"d1": 0.0, "w1": None, "m1": None})], [])

    assert "0.0%" in html
    assert '<span style="color:#bbb">-</span>' in html


def test_rows_without_changes_still_render():
    """แถวที่ยังไม่มี changes (df สั้นเกิน/ของเก่า) ต้องไม่ทำให้เมลทั้งฉบับพัง"""
    html = report.render("now", TOTALS, [_row()], [])

    assert "Bull ↑" in html


def test_portfolio_change_line_shows_baht_and_percent():
    changes = {"d1": {"pct": 0.8, "diff": 9876.0},
               "w1": {"pct": -1.2, "diff": -1.0},
               "m1": {"pct": 4.5, "diff": 1.0}}

    html = report.render("now", TOTALS, [], [], changes=changes)

    assert "วันนี้" in html
    assert "+฿9,876 (+0.8%)" in html
    assert "-1.2%" in html and "+4.5%" in html


def test_portfolio_change_line_shows_minus_sign_on_a_down_day():
    changes = {"d1": {"pct": -0.8, "diff": -9876.0}, "w1": {"pct": None, "diff": None},
               "m1": {"pct": None, "diff": None}}

    html = report.render("now", TOTALS, [], [], changes=changes)

    assert "-฿9,876 (-0.8%)" in html


def test_portfolio_change_line_hidden_when_no_position_has_history():
    changes = {"d1": {"pct": None, "diff": None}, "w1": {"pct": None, "diff": None},
               "m1": {"pct": None, "diff": None}}

    html = report.render("now", TOTALS, [], [], changes=changes)

    assert "วันนี้" not in html


def test_tiny_negative_move_is_not_shown_as_minus_zero():
    """ราคาขยับ -0.04% ปัดแล้วได้ -0.0 — ต้องขึ้น 0.0% สีเทา ไม่ใช่ "-0.0%" สีแดง"""
    changes = {"d1": {"pct": -0.04, "diff": -25.0}, "w1": {"pct": None, "diff": None},
               "m1": {"pct": None, "diff": None}}

    html = report.render("now", TOTALS, [_row({"d1": -0.04, "w1": None, "m1": None})], [],
                         changes=changes)

    assert "-0.0%" not in html
    assert "0.0%" in html


def test_flat_portfolio_day_is_neutral_not_green_plus_zero():
    changes = {"d1": {"pct": 0.0, "diff": 0.0}, "w1": {"pct": None, "diff": None},
               "m1": {"pct": None, "diff": None}}

    html = report.render("now", TOTALS, [], [], changes=changes)
    line = html.split("วันนี้")[1].split("</div>")[0]

    assert "฿0 (0.0%)" in line
    assert "+฿" not in line and "#1e8e3e" not in line  # ไม่ใส่เครื่องหมายบวกและไม่ทาเขียว
