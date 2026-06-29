# 2026-06-29 — Cron อ–ส + SEC insider filings (แบบ 59/246-2)

## Goal
เลื่อน cron ส่งเมลเป็น อ–ส (รายงานวันถัดไปของวันเทรด) และเพิ่มข้อมูลซื้อขายของกรรมการ/ผู้ถือหุ้นใหญ่จากเว็บ ก.ล.ต.

## What changed
- `.github/workflows/daily-report.yml`: cron `30 0 * * 1-5` → `30 0 * * 2-6` (อ–ส, เวลาเดิม)
- `src/sec_filings.py` (ใหม่): scraper แบบ 59 + 246-2 จาก market.sec.or.th iDisc
- `src/report.py`: section ใหม่ "ความเคลื่อนไหวผู้บริหาร/ผู้ถือหุ้นใหญ่" (คอลัมน์ต่างกันต่อฟอร์ม) + failure notice
- `main.py`: ดึง thai_symbols (.BK) → `fetch_filings(days=7)` → ส่งเข้า report
- `requirements.txt`: + requests, beautifulsoup4
- `tests/test_sec_filings.py` + fixtures HTML จริง (5 เทสต์ผ่าน)

## Decisions (ที่พิสูจน์จาก spike จริง)
- iDisc = **ASP.NET WebForms** (postback HTML + ViewState ~151KB) ไม่ใช่ JSON/Angular → requests+bs4
- **global query** (company ว่าง) ราย "วันรับเอกสาร" (`rblDateType=2`) ทีละวัน 7 วัน → เลี่ยง page cap 100 แถว + **ไม่ต้อง map symbol→company-id** (symbol อยู่ในผลลัพธ์: 59 = `บมจ.(SYM)`, 246 = คอลัมน์แรก)
- 246-2 ไม่มีราคา/จำนวน → แสดง **% การถือครอง** แทน (คนละ schema กับ 59)
- stateless: window 7 วัน + dedupe ด้วย filing_id (59=batchNo/transId, 246=เลขที่รายงาน), label "ล่าสุด 7 วัน"
- graceful: error/วันทะลุ cap → เข้า `sec_failed` → failure notice ในเมล เมลยังส่งปกติ

## Verified
- 5 parser tests ผ่าน (fixture HTML จริง) · live fetch เจอจริง (KBANK ซื้อ 41.2M @142.56) · full dry-run e2e · empty-state · failure-notice
- Codex review: ไม่มี Must-fix; แก้ P2 (guard ถ้าไม่มีหุ้นไทยไม่ยิงเว็บ) แล้ว

## Open / next steps
- ยังไม่ commit (รอ PO)
- edge case: ถ้าวันเดียวมี >100 รายการ จะดูไม่ครบ — ปัจจุบันแค่เตือนใน failure notice (per-day คือ granularity ละเอียดสุดของ UI)
- ถ้าต้อง "ใหม่ตั้งแต่ครั้งก่อน" จริง (ไม่ซ้ำข้ามเมล) ต้องเพิ่ม state (cache/artifact)
- ตรวจ secret/cron บน GitHub Actions ว่ารันจริงวันถัดไป (workflow_dispatch ทดสอบได้)

## Notes for next session
- plan/feature docs ของโปรเจกต์นี้อยู่ใน `.notes/` (ย้ายมาจาก ~/.claude/plans แล้ว)
- รันเทสต์: `PYTHONPATH=. python3 tests/test_sec_filings.py` · dry-run: `DRY_RUN=1 PYTHONPATH=. python3 main.py`
