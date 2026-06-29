"""เทสต์ parser แบบ 59/246-2 กับ fixture HTML จริงจากเว็บ ก.ล.ต."""
from pathlib import Path

from bs4 import BeautifulSoup

from src import sec_filings

FIX = Path(__file__).parent / "fixtures"


def _soup(name):
    return BeautifulSoup((FIX / name).read_text(encoding="utf-8"), "html.parser")


def test_form59_parse():
    rows = sec_filings._parse_form59(_soup("form59_sample.html"), "2026-06-24")
    assert rows, "ควร parse ได้อย่างน้อย 1 แถว"
    gtb = next(r for r in rows if r["symbol"] == "GTB")  # row0: เจตาแบค บมจ.(GTB)
    assert gtb["form"] == "59"
    assert gtb["action"] == "ซื้อ"
    assert gtb["shares"] == 95400.0          # '95,400' -> ตัด comma
    assert gtb["price"] == 0.69
    assert gtb["security_type"] == "หุ้นสามัญ"
    assert gtb["txn_date"] == "23/06/2569"   # คงรูปแบบ พ.ศ. ไว้แสดง
    assert gtb["recv_date"] == "2026-06-24"
    assert gtb["filing_id"].startswith("59:")
    # ชื่อไทย UTF-8 ไม่เพี้ยน
    assert "นาย" in gtb["name"]
    # ทุกแถวต้อง parse symbol ได้ (รูปแบบ (SYM) สม่ำเสมอ)
    assert all(r["symbol"] for r in rows)


def test_form59_skips_revoked():
    # fixture มีแถว 'Revoked by Reporter' (NAM/UAC) ที่ทำให้ shares parse เป็น None
    # ต้องถูกกรองทิ้ง: ไม่มี revoke leak และไม่มีแถว shares=None หลงเหลือ
    rows = sec_filings._parse_form59(_soup("form59_sample.html"), "2026-06-24")
    assert not any("Revoked" in str(r) for r in rows)
    assert all(r["shares"] is not None for r in rows)


def test_form59_transfer_has_no_price():
    rows = sec_filings._parse_form59(_soup("form59_sample.html"), "2026-06-24")
    transfers = [r for r in rows if r["action"] == "โอน"]
    if transfers:
        assert transfers[0]["price"] is None  # 'โอน' ราคา '-' -> None
        assert transfers[0]["security_type"] == "ใบสำคัญแสดงสิทธิที่จะซื้อหุ้น"


def test_form246_parse():
    rows = sec_filings._parse_form246(_soup("form246_sample.html"), "2026-06-26")
    assert rows
    assert all(r["form"] == "246" for r in rows)
    assert all(r["shares"] is None and r["price"] is None for r in rows)  # 246 ไม่มีราคา/จำนวน
    gulf = next(r for r in rows if r["symbol"] == "GULF")
    assert gulf["action"] == "จำหน่าย"
    assert gulf["pct_change"] == 2.7845   # คอลัมน์ % รายบุคคล (ไม่ใช่ % กลุ่ม)
    assert gulf["pct_after"] == 4.9494
    assert gulf["filing_id"].startswith("246:")


def test_to_be_date():
    from datetime import date
    assert sec_filings._to_be(date(2026, 6, 24)) == "24/06/2569"


def test_report_dates_window():
    from datetime import date
    tue = sec_filings.report_dates(date(2026, 6, 30))
    assert [d.isoformat() for d in tue] == ["2026-06-27", "2026-06-28", "2026-06-29"]

    wed = sec_filings.report_dates(date(2026, 7, 1))
    assert [d.isoformat() for d in wed] == ["2026-06-30"]

    sat = sec_filings.report_dates(date(2026, 7, 4))
    assert [d.isoformat() for d in sat] == ["2026-07-03"]


def test_txn_recency_filter():
    # filing ที่กรอกวันทำรายการเก่ากว่าวันรับเอกสารมาก (เช่น KBANK 2555) ต้องถูกตัด
    assert sec_filings._txn_is_recent("15/02/2555", "2026-06-27") is False
    # รายการปกติ: ทำรายการก่อนรับเอกสารไม่กี่วัน -> ผ่าน
    assert sec_filings._txn_is_recent("25/06/2569", "2026-06-27") is True
    assert sec_filings._txn_is_recent("27/06/2569", "2026-06-27") is True  # วันเดียวกัน
    # เกิน 7 วันพอดี -> ตัด
    assert sec_filings._txn_is_recent("19/06/2569", "2026-06-27") is False
    # parse ไม่ได้ -> ไม่ตัดทิ้ง
    assert sec_filings._txn_is_recent("", "2026-06-27") is True


def test_fetch_filings_falls_back_to_company_queries_when_form59_day_hits_cap():
    from datetime import date

    calls = []

    def fake_fetch_day(session, path, base_fields, parser, d):
        calls.append((path, dict(base_fields), d))
        if path == "r59" and base_fields["ctl00$CPH$ddlCompany"] == "":
            return [], True
        return [], False

    old_report_dates = sec_filings.report_dates
    old_fetch_day = sec_filings._fetch_day
    sec_filings.report_dates = lambda today: [date(2026, 6, 5)]
    sec_filings._fetch_day = fake_fetch_day
    try:
        rows, failed = sec_filings.fetch_filings(["AP", "SIRI"], today=date(2026, 6, 29))
    finally:
        sec_filings.report_dates = old_report_dates
        sec_filings._fetch_day = old_fetch_day

    assert rows == []
    assert failed == []
    form59_company_ids = [
        fields["ctl00$CPH$ddlCompany"]
        for path, fields, _ in calls
        if path == "r59" and fields["ctl00$CPH$ddlCompany"]
    ]
    assert form59_company_ids == [
        sec_filings.FORM59_COMPANY_IDS["AP"],
        sec_filings.FORM59_COMPANY_IDS["SIRI"],
    ]
    assert any(path == "r59" and fields["ctl00$CPH$ddlCompany"] == "" for path, fields, _ in calls)
    assert sum(1 for path, _, _ in calls if path == "r246") == 1
    assert next(fields for path, fields, _ in calls if path == "r246")["ctl00$CPH$BsCompany"] == ""


def test_fetch_filings_warns_when_form59_cap_has_no_company_id():
    from datetime import date

    def fake_fetch_day(session, path, base_fields, parser, d):
        if path == "r59":
            return [], True
        return [], False

    old_report_dates = sec_filings.report_dates
    old_fetch_day = sec_filings._fetch_day
    sec_filings.report_dates = lambda today: [date(2026, 6, 5)]
    sec_filings._fetch_day = fake_fetch_day
    try:
        rows, failed = sec_filings.fetch_filings(["DIF"], today=date(2026, 6, 29))
    finally:
        sec_filings.report_dates = old_report_dates
        sec_filings._fetch_day = old_fetch_day

    assert rows == []
    assert failed == ["r59 DIF 2026-06-05 (>100 แถว ไม่มี company id)"]


def test_fetch_filings_merges_repeated_form59_global_fetches():
    from datetime import date

    attempts = {"r59_global": 0}

    def row(symbol, filing_id):
        return {
            "form": "59",
            "symbol": symbol,
            "name": "name",
            "relationship": "ผู้รายงาน",
            "action": "ซื้อ",
            "shares": 1.0,
            "price": 1.0,
            "pct_change": None,
            "pct_after": None,
            "txn_date": "01/06/2569",
            "recv_date": "2026-06-02",
            "source_url": None,
            "filing_id": filing_id,
        }

    def fake_fetch_day(session, path, base_fields, parser, d):
        if path == "r59" and base_fields["ctl00$CPH$ddlCompany"] == "":
            attempts["r59_global"] += 1
            if attempts["r59_global"] == 1:
                return [row("AP", "59:ap")], False
            return [row("SIRI", "59:siri")], False
        return [], False

    old_report_dates = sec_filings.report_dates
    old_fetch_day = sec_filings._fetch_day
    sec_filings.report_dates = lambda today: [date(2026, 6, 2)]
    sec_filings._fetch_day = fake_fetch_day
    try:
        rows, failed = sec_filings.fetch_filings(["AP", "SIRI"], today=date(2026, 6, 29))
    finally:
        sec_filings.report_dates = old_report_dates
        sec_filings._fetch_day = old_fetch_day

    assert failed == []
    assert {r["symbol"] for r in rows} == {"AP", "SIRI"}
    assert attempts["r59_global"] == sec_filings.R59_GLOBAL_ATTEMPTS


def test_num():
    assert sec_filings._num("95,400") == 95400.0
    assert sec_filings._num("-") is None
    assert sec_filings._num("") is None
    assert sec_filings._num("0.69") == 0.69


if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok", fn.__name__)
    print(f"\n{len(fns)} passed")
