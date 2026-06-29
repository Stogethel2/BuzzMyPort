"""ดึงรายการซื้อขายของกรรมการ/ผู้บริหาร (แบบ 59) และผู้ถือหุ้นใหญ่ (แบบ 246-2) จากเว็บ ก.ล.ต.

เว็บ iDisc เป็น ASP.NET WebForms (postback HTML + ViewState) ไม่มี JSON API:
GET หน้า → ดึง hidden ViewState → POST กลับ → parse ตาราง HTML
query แบบ "ทุกบริษัท" (company ว่าง) ราย "วันรับเอกสาร" ทีละวัน แล้วกรองด้วย symbol ที่อยู่ในผลลัพธ์
จึงไม่ต้อง map symbol→company-id และเลี่ยง page cap 100 แถว/response ไปในตัว
"""
import re
import time
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup

BASE = "https://market.sec.or.th/public/idisc/th/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
HIDDEN = ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION")
BE_OFFSET = 543  # พ.ศ. = ค.ศ. + 543
SYMBOL_RE = re.compile(r"\(([A-Z0-9]+)\)\s*$")  # ...บมจ.(GTB)
RUN_WEEKDAYS = (1, 2, 3, 4, 5)  # วันที่ cron ส่งเมล: อังคาร-เสาร์ (จันทร์=0)


def report_dates(today):
    """วัน 'รับเอกสาร' ที่เมลฉบับนี้ต้องครอบ = ตั้งแต่เมลฉบับก่อน(วันรันตามตาราง)ถึงเมื่อวาน

    เมลฉบับก่อนครอบถึง 'เมื่อวานของมัน' แล้ว → ฉบับนี้เริ่มที่วันรันก่อนหน้าพอดี ไม่ซ้ำไม่ขาด
    เช่น อังคาร → [เสาร์, อาทิตย์, จันทร์] ; พุธ-เสาร์ → [เมื่อวาน] วันเดียว
    """
    prev = today - timedelta(days=1)
    while prev.weekday() not in RUN_WEEKDAYS:
        prev -= timedelta(days=1)
    return [prev + timedelta(days=i) for i in range((today - prev).days)]


def _to_be(d):
    """date -> 'dd/mm/yyyy' แบบ พ.ศ. (รูปแบบที่ฟอร์มต้องการ)"""
    return f"{d.day:02d}/{d.month:02d}/{d.year + BE_OFFSET}"


def _num(s):
    """'95,400' -> 95400.0 ; '-'/'' -> None (รายการ 'โอน' ไม่มีราคา)"""
    s = (s or "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _post(session, path, fields):
    """GET หน้า → แนบ ViewState → POST → คืน BeautifulSoup (retry 3 ครั้ง)"""
    last = None
    for i in range(3):
        try:
            soup = BeautifulSoup(session.get(BASE + path, timeout=30).text, "html.parser")
            payload = {}
            for name in HIDDEN:
                el = soup.find("input", {"name": name})
                payload[name] = el["value"] if el and el.has_attr("value") else ""
            payload.update(fields)
            r = session.post(BASE + path, data=payload, timeout=60)
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    raise last


def _results_table(soup):
    """ตารางผลลัพธ์คือตารางที่มีหัวคอลัมน์ภาษาไทยเฉพาะ (เลี่ยงตาราง layout)"""
    for t in soup.find_all("table"):
        text = t.get_text()
        if "ได้มา" in text and ("ความสัมพันธ์" in text or "หลักทรัพย์" in text):
            return t
    return None


def _found_count(soup):
    """จำนวน 'พบ X รายการ' ที่เว็บรายงาน (ไว้เทียบกับ cap 100)"""
    m = re.search(r"จำนวนรายการที่พบ\s*([\d,]+)", soup.get_text())
    return int(m.group(1).replace(",", "")) if m else None


def _rows(table):
    return [tr for tr in table.select("tr") if tr.find_all("td")] if table else []


def _parse_form59(soup, recv_date):
    """แบบ 59: คอลัมน์ บริษัท(SYM)|ชื่อ|ความสัมพันธ์|ประเภท|วันที่|จำนวน|ราคา|วิธีการ|หมายเหตุ"""
    out = []
    for tr in _rows(_results_table(soup)):
        c = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if len(c) < 8:
            continue
        if any("Revoked" in x for x in c):  # รายการที่ผู้รายงานเพิกถอน — ไม่ใช่การซื้อขายจริง
            continue
        m = SYMBOL_RE.search(c[0])
        link = tr.find("a", href=True)
        href = link["href"] if link else ""
        ids = re.findall(r"[?&](?:batchNo|transId)=([^&]+)", href)
        out.append({
            "form": "59",
            "symbol": m.group(1) if m else None,
            "name": c[1],
            "relationship": c[2],
            "action": c[7],          # ซื้อ / ขาย / โอน
            "shares": _num(c[5]),
            "price": _num(c[6]),
            "pct_change": None,
            "pct_after": None,
            "txn_date": c[4],
            "recv_date": recv_date,
            "source_url": href or None,
            "filing_id": "59:" + "_".join(ids) if ids else f"59:{c[0]}|{c[1]}|{c[4]}|{c[5]}",
        })
    return out


def _parse_form246(soup, recv_date):
    """แบบ 246-2: หลักทรัพย์|ชื่อ|วิธีการ|ประเภท|%ก่อน|%ได้มา|%หลัง|วันที่|...|เลขที่"""
    out = []
    for tr in _rows(_results_table(soup)):
        c = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if len(c) < 8:
            continue
        report_no = c[13] if len(c) > 13 and c[13] else None
        out.append({
            "form": "246",
            "symbol": c[0] or None,
            "name": c[1],
            "relationship": "ผู้ถือหุ้นใหญ่",
            "action": c[2],          # ได้มา / จำหน่าย / สิ้นสุด...
            "shares": None,
            "price": None,
            "pct_change": _num(c[5]),
            "pct_after": _num(c[6]),
            "txn_date": c[7],
            "recv_date": recv_date,
            "source_url": (tr.find("a", href=True) or {}).get("href"),
            "filing_id": f"246:{report_no}" if report_no else f"246:{c[0]}|{c[1]}|{c[7]}",
        })
    return out


_FORM59_FIELDS = {"ctl00$CPH$ddlCompany": "", "ctl00$CPH$rblDateType": "2",
                  "ctl00$CPH$btSearch": "ค้นหา"}
_FORM246_FIELDS = {"ctl00$CPH$BsCompany": "", "ctl00$CPH$BsCompany_t": "",
                   "ctl00$CPH$BsCompany_v": "", "ctl00$CPH$BsCompany_d": "",
                   "ctl00$CPH$txtSearchPerson": "", "ctl00$CPH$rblDateType": "2",
                   "ctl00$CPH$btSearch": "ค้นหา"}


def _fetch_day(session, path, base_fields, parser, d):
    """ดึง 1 ฟอร์ม 1 วัน (received-date = d). คืน (rows, over_cap: bool)"""
    be = _to_be(d)
    fields = dict(base_fields)
    fields["ctl00$CPH$BSDateFrom"] = be
    fields["ctl00$CPH$BSDateTo"] = be
    soup = _post(session, path, fields)
    rows = parser(soup, d.isoformat())
    count = _found_count(soup)
    # เทียบกับจำนวนแถวใน HTML จริง (ก่อนกรอง revoked) ไม่ใช่ len(rows) ที่กรองแล้ว
    raw_count = len(_rows(_results_table(soup)))
    over_cap = count is not None and count > raw_count  # ทะลุ cap 100 ของ response
    return rows, over_cap


def fetch_filings(symbols, today=None):
    """ดึงแบบ 59 + 246-2 ตาม "วันรับเอกสาร" ที่เมลฉบับนี้ต้องครอบ (ดู report_dates) แล้วกรองเฉพาะ symbols

    คืน (rows, failed):
      rows   = list[Filing dict] กรองด้วย symbols, dedupe ด้วย filing_id, เรียง recv_date ใหม่→เก่า
      failed = list[str] อธิบายวัน/ฟอร์มที่ดึงไม่ได้ หรือวันที่ทะลุ cap 100 (ไว้ทำ failure notice)
    """
    want = {s.upper() for s in symbols}
    if not want:  # ไม่มีหุ้นไทย -> ไม่ต้องยิงเว็บ ก.ล.ต.
        return [], []
    today = today or date.today()
    session = requests.Session()
    session.headers.update(HEADERS)

    by_id, failed = {}, []
    forms = [("r59", _FORM59_FIELDS, _parse_form59), ("r246", _FORM246_FIELDS, _parse_form246)]
    for d in report_dates(today):
        for path, base_fields, parser in forms:
            try:
                rows, over_cap = _fetch_day(session, path, base_fields, parser, d)
            except Exception:
                failed.append(f"{path} {d.isoformat()}")
                continue
            if over_cap:
                failed.append(f"{path} {d.isoformat()} (>100 แถว ดูไม่ครบ)")
            for row in rows:
                if row["symbol"] in want:
                    by_id[row["filing_id"]] = row

    rows = sorted(by_id.values(), key=lambda r: (r["recv_date"], r["symbol"] or ""), reverse=True)
    return rows, failed
