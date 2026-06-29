# แผน: ปรับ cron (อ–ส) + เพิ่มข้อมูลการซื้อขายของกรรมการ/ผู้ถือหุ้นใหญ่ (แบบ 59 + 246-2 จาก ก.ล.ต.)

## Context (ทำไปทำไม)
รายงานพอร์ตรายวันส่งเมลผ่าน GitHub Actions ทุกวันจันทร์–ศุกร์ เวลา 07:30 (Bangkok)
ตอนนี้ตลาดไทยเทรดจันทร์–ศุกร์ ดังนั้นรายงานควรออก **วันถัดไป** ของแต่ละวันเทรด → ต้องเลื่อนเป็น **อังคาร–เสาร์**
และต้องการข้อมูลเพิ่ม: กรรมการ/ผู้บริหาร/ผู้ถือหุ้นใหญ่ของแต่ละบริษัท/กองทุนมีการซื้อขายหุ้นตัวเองไหม ที่ราคา/จำนวนเท่าไหร่ — หุ้นไทยไม่มี API ต้อง scrape จากเว็บ ก.ล.ต.

**ผลลัพธ์ที่ต้องการ:** เมลออกเฉพาะ อ–ส เวลาเดิม และมีหัวข้อใหม่ในเมลแสดงรายการ insider/major-shareholder ที่ ก.ล.ต. เพิ่งรับเอกสารล่าสุด (ราคา, จำนวน, ซื้อ/ขาย, ชื่อ, ตำแหน่ง/ความสัมพันธ์)

## การตัดสินใจ (ยืนยันกับ PO แล้ว)
- ข้อมูล: **แบบ 59** (กรรมการ/ผู้บริหาร) **+ แบบ 246-2** (ผู้ถือหุ้นใหญ่ ข้าม/ลดเกณฑ์ 5%)
- ช่วงเวลา: **"ตั้งแต่เมลฉบับก่อนถึงเมื่อวาน"** (อิงตาราง cron อ-ส) — `report_dates()`: อังคารครอบ เสาร์+อาทิตย์+จันทร์ (กันตกหล่นช่วงสุดสัปดาห์), พุธ-เสาร์ = เมื่อวานวันเดียว ; label ในเมลโชว์ช่วงวันที่จริง (พ.ศ.) ไม่ขาดไม่ซ้ำ (PO เลือกเอง 2026-06-29)
- ขอบเขต: **หุ้น/กองทุนไทย (.BK) เท่านั้น** — ข้าม QQQM (US)
- **ถ้า scrape ไม่สำเร็จ → แนบ notice ในเมลรายวัน** (บอกว่าฟอร์ม/หุ้นไหนดึงไม่ได้) ไม่ใช่เงียบหาย

---

## ส่วน A — ปรับ cron schedule (one-line)
**ไฟล์:** `.github/workflows/daily-report.yml`

```yaml
# เดิม
- cron: "30 0 * * 1-5"   # จ–ศ
# ใหม่
- cron: "30 0 * * 2-6"   # อ–ส (Tue–Sat) เวลาเดิม 07:30 Asia/Bangkok
```
เวลา (00:30 UTC) คงเดิม เปลี่ยนเฉพาะ day-of-week. GitHub Actions: 0/7=อาทิตย์ → อ–ส = `2-6`.
หมายเหตุ: GitHub cron อาจดีเลย์ได้ไม่กี่นาที (พฤติกรรมเดิม ไม่ต้องแก้)

---

## ส่วน B — Scraper แบบ 59 + 246-2 จาก ก.ล.ต.

### ✅ B1 พิสูจน์แล้ว (spike จริงด้วย requests+bs4 — gate ผ่าน)
**ไม่ใช่ JSON API / ไม่ใช่ Angular — เป็น ASP.NET WebForms (postback HTML + ViewState)**
- Flow ต่อฟอร์ม: GET หน้า → ดึง hidden `__VIEWSTATE`(~151KB)/`__VIEWSTATEGENERATOR`/`__EVENTVALIDATION` → POST กลับ URL เดิม → ได้ HTML ตาราง → parse ด้วย bs4
- **global query ได้** (ปล่อย company ว่าง) → **ไม่ต้อง map symbol→company-id เลย** (สำคัญมาก แก้ข้อกังวล Codex)
- **page cap 100 แถว/response** (เช่น 29 วัน = 686 จริง แต่ส่งมา 100) → **เลี่ยงด้วยการ query ราย "วันรับเอกสาร" ทีละวัน** (received-date ≈ 14–41 แถว/วัน << 100) → ไม่ต้องทำ pagination
- ใช้ received/published = **`rblDateType=2`** (r59 = "วันที่ สนง.รับเอกสาร", r246 = "วันที่เผยแพร่") — ⚠️ ค่า `1` คือ transaction date อย่าใช้
- safety: ถ้า count(พบ X) > แถวที่ parse ได้ → วันนั้นทะลุ cap 100 → **ใส่ใน `sec_failed`/failure-notice** (per-day คือ granularity ละเอียดสุดของ UI ซอยต่อไม่ได้ — เป็น edge case ที่แค่เตือน)

**แบบ 59** `https://market.sec.or.th/public/idisc/th/r59`
- fields: `ctl00$CPH$ddlCompany`(ว่าง), `ctl00$CPH$rblDateType`(=2), `ctl00$CPH$BSDateFrom/To`(พ.ศ. dd/mm/yyyy), `ctl00$CPH$btSearch`(=ค้นหา)
- คอลัมน์: ชื่อบริษัท | ชื่อผู้บริหาร | ความสัมพันธ์ | ประเภทหลักทรัพย์ | วันที่ได้มา/จำหน่าย | **จำนวน** | **ราคา** | **วิธีการ(ซื้อ/ขาย/โอน)** | หมายเหตุ
- **symbol อยู่ท้ายชื่อบริษัทในวงเล็บ** เช่น `...บมจ.(CCET)` → regex `\(([A-Z0-9]+)\)\s*$`
- ราคา = `-` เมื่อเป็น "โอน"; จำนวน มี comma; detail link `/r59/th/report?batchNo&transId&reporter&executor` → ใช้เป็น filing_id

**แบบ 246-2** `https://market.sec.or.th/public/idisc/th/r246`
- fields ต่างจาก 59: `ctl00$CPH$BsCompany`(+ _t/_v/_d ว่างทั้งหมด), `ctl00$CPH$txtSearchPerson`(ว่าง), `rblDateType`(=1), `BSDateFrom/To`, `btSearch`
- คอลัมน์: **หลักทรัพย์(symbol ตรงๆ คอลัมน์แรก)** | ชื่อผู้ได้มา/จำหน่าย | **วิธีการ(ได้มา/จำหน่าย/สิ้นสุด)** | ประเภท | **%ก่อน | %ได้มา/จำหน่าย | %หลัง** | วันที่ | (group %s, หมายเหตุ)
- ⚠️ **246-2 ไม่มี ราคา/จำนวนหุ้น** — รายงานเป็น **%การถือครอง** (ข้าม/ลดเกณฑ์ 5%) เท่านั้น → คนละ schema กับ 59 → report แสดงคอลัมน์ต่างกันต่อฟอร์ม
- volume ต่ำมาก (4 วัน = 3 รายการ) ไม่มีปัญหา pagination

### ขั้นตอนทำ (B1 เสร็จแล้ว — ที่เหลือคือ implement)
1. **โมดูลใหม่** `src/sec_filings.py` (requests + bs4, ตามแพทเทิร์น `src/data_fetcher.py`)
   - helper `_post(url, fields)`: GET → ดึง 3 hidden fields → POST → คืน soup (retry 3 ครั้งแบบ `_retry`)
   - `fetch_form59(date_th) -> list[Filing]`: POST r59 (company ว่าง, rblDateType=1, from=to=date) → parse ตาราง (หา table ที่มี "ความสัมพันธ์")
   - `fetch_form246(date_th) -> list[Filing]`: POST r246 (BsCompany ว่าง, rblDateType=1) → parse
   - วนเรียกตาม `report_dates(today)` = ตั้งแต่วันรัน cron ก่อนหน้า ถึงเมื่อวาน (อังคาร=เสาร์-จันทร์, วันอื่น=เมื่อวาน)
   - `Filing` (รวม 2 schema): `form, symbol, name, relationship, action, shares, price, pct_change, pct_after, txn_date, recv_date, source_url, filing_id`
     - 59 เติม shares/price; 246 เติม pct_change/pct_after (อีกฝั่งเว้น None)
   - symbol: 59 = regex `\(([A-Z0-9]+)\)\s*$` จากชื่อบริษัท; 246 = คอลัมน์แรกตรงๆ
   - filing_id: 59 = batchNo+transId+reporter (จาก detail href); 246 = symbol+name+recv_date (ไม่มี id ชัด)
   - แปลง **พ.ศ.→ค.ศ. (ปี−543)**, parse จำนวน (ตัด comma), ราคา `-`→None
   - safety: ถ้า "พบ X" > จำนวนแถว → บันทึก warning (วันนั้นทะลุ cap 100)
   - graceful: error ต่อวัน/ต่อฟอร์ม ไม่ทำทั้งงานล้ม → เก็บใน failed

2. **กรอง + รวม** — เก็บเฉพาะ symbol ที่อยู่ใน watchlist (`config/portfolio.json`, ตัด `.BK`, ข้าม QQQM), dedupe ด้วย filing_id, เรียง recv_date ใหม่→เก่า
   - `// ponytail: query ราย "วันรับเอกสาร" ตามตาราง เลี่ยง pagination+ไม่ต้อง map company-id — ถ้าวันไหนทะลุ 100 แค่เตือนใน notice`

3. **deps** — เพิ่ม `requests` + `beautifulsoup4` ใน `requirements.txt`

4. **wire เข้า** `main.py:build()` — หลัง fetch ราคา: เรียก scraper, ส่ง `insider_rows` + `sec_failed` เข้า template

5. **report** `src/report.py` + Jinja2 template
   - section ใหม่ "ความเคลื่อนไหวผู้บริหาร/ผู้ถือหุ้นใหญ่ (แบบ 59 / 246-2) — รับเอกสาร <ช่วงวันที่จริง>"
   - **คอลัมน์ต่างกันต่อฟอร์ม:** 59 → หุ้น|ชื่อ|ความสัมพันธ์|ซื้อ/ขาย/โอน|จำนวน|ราคา|วันที่|ลิงก์ ; 246 → หุ้น|ชื่อ|ได้มา/จำหน่าย|%เปลี่ยน|%หลัง|วันที่
   - สี: ซื้อ/ได้มา=เขียว ขาย/จำหน่าย=แดง; ไม่มีรายการ → "ไม่มีรายงานใหม่"
   - **failure notice (PO ขอ):** ถ้า `sec_failed` ไม่ว่าง → แถบ "⚠️ ดึงข้อมูล ก.ล.ต. ไม่สำเร็จ: <ฟอร์ม/วัน>" เมลยังส่งปกติ

### ไฟล์ที่แตะ
- `.github/workflows/daily-report.yml` (cron)
- `src/sec_filings.py` (ใหม่)
- `main.py` (เรียกใช้)
- `src/report.py` + template (section ใหม่ + failure notice)
- `requirements.txt` (deps)

---

## Verification
1. **Parser:** เก็บ fixture จริง 1 ไฟล์จาก B1 → เทสต์ `src/sec_filings.py` parse ถูก (assert ราคา/จำนวน/action + พ.ศ.→ค.ศ. + ชื่อไทย UTF-8) — เทสต์เล็ก 1 ตัวพอ
2. **End-to-end (local):** รัน `python main.py` ด้วย env จริง → เมลมี section ใหม่เรนเดอร์ถูก / ไม่มีรายการ = empty state
3. **Failure notice (PO ขอ):** จำลอง SEC ล่ม (URL ผิด) → เมลรายวันยังส่งได้ + มีแถบ "⚠️ ดึงข้อมูล ก.ล.ต. ไม่สำเร็จ" ไม่ crash
4. **Cron:** ตรวจ `2-6` ใน workflow + ทดสอบ `workflow_dispatch` ว่ารันผ่าน
