from src import report


def test_sec_section_does_not_claim_no_new_reports_when_fetch_failed():
    totals = {
        "total_value": 0,
        "thb_value": 0,
        "usd_value": 0,
        "usdthb": 33,
        "fx_ok": True,
        "total_pl": 0,
        "total_pl_pct": 0,
    }

    html = report.render("now", totals, [], [], [], ["r59 2026-06-29"], "29/06/2569", [])

    assert "ตรวจข้อมูล ก.ล.ต. ไม่ครบ" in html
    assert "ไม่มีรายงานใหม่" not in html
