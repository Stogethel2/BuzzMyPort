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
