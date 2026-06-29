# 2026-06-29 — SEC insider report window + cap fallback

## Goal
ปรับ section ความเคลื่อนไหวผู้บริหาร/ผู้ถือหุ้นใหญ่ให้แสดงรายการใหม่ตามรอบเมลล่าสุด และแก้ warning จากแบบ 59 วันที่มีผลลัพธ์เกิน cap 100 แถว

## What changed
- `report_dates(today)` ใช้ window ตั้งแต่เมลรอบก่อนถึงเมื่อวาน: อังคารครอบเสาร์-จันทร์, พุธ-เสาร์ครอบเมื่อวานวันเดียว
- เพิ่ม test boundary ของ cron window เพื่อลดการแสดงรายการเก่าซ้ำทุกวัน
- เพิ่ม `FORM59_COMPANY_IDS` สำหรับหุ้นไทยในพอร์ตที่มีใน dropdown แบบ 59 ของ SEC
- ถ้า global แบบ 59 รายวันชน cap 100 แถว จะ fallback ไป query รายบริษัทของหุ้นในพอร์ต และไม่ขึ้น `sec_failed` ถ้า fallback สำเร็จ
- แบบ 59 global ยิงซ้ำและ merge ด้วย `filing_id` เพื่อลดโอกาส SEC live response ตกแถวแบบไม่มี error
- จำกัด failure notice ในเมลให้โชว์ตัวอย่างรายการแรก ๆ แทนการ join ทั้งหมด

## Decisions
- ไม่ใช้ rolling 30 วันในเมลรายวัน เพราะทำให้ scrape เยอะและรายการเดิมซ้ำหลายวัน
- `DIF` ไม่อยู่ใน dropdown แบบ 59 ที่ตรวจจาก SEC live จึงไม่อยู่ใน `FORM59_COMPANY_IDS`; แบบ 246-2 ยังใช้ global query และกรองด้วย symbol

## Open / next steps
- ถ้าเพิ่มหุ้นไทยใหม่ในพอร์ตและต้องการ fallback แบบ 59 ให้เพิ่ม SEC company id ใน `FORM59_COMPANY_IDS`
- ยังไม่ได้ commit

## Notes for next session
- Verification live: 30/06/2026 ครอบ 27-29 มิ.ย. ได้ 0 รายการในพอร์ตและ `failed=[]`; 01/07 และ 04/07 ครอบวันเดียวและ `failed=[]`
- รันเทสต์: `PYTHONPATH=. pytest -q tests/test_sec_filings.py` หรือ `PYTHONPATH=. python3 tests/test_sec_filings.py`
