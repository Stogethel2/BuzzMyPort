# Stock Portfolio Summary Alert

## Purpose
ระบบส่งอีเมลสรุปพอร์ตหุ้นอัตโนมัติทุกเช้า 07:30 Asia/Bangkok ผ่าน GitHub Actions เพื่อดูมูลค่าพอร์ต, P/L, momentum, XD และความเคลื่อนไหวผู้บริหาร/ผู้ถือหุ้นใหญ่ของหุ้นไทยในพอร์ต

## Scope
- รองรับหุ้นไทย (`.BK`) และหุ้นสหรัฐใน `config/portfolio.json`
- แสดงมูลค่ารวมเป็นบาท โดยแปลงหุ้นสหรัฐด้วย USD/THB
- แสดง P/L รายตัวและ P/L รวมจากต้นทุนเฉลี่ย
- แสดง RSI/Stochastic/Crossover ทั้ง 1D และ 1W
- แสดง XD badge ถ้า ex-date อยู่ในช่วงใกล้ถึง
- แสดง High Volume เมื่อ volume วันล่าสุดสูงผิดปกติเทียบกับค่าเฉลี่ย
- ส่งอีเมล HTML ตาม cron อังคาร-เสาร์ เวลา 07:30 Asia/Bangkok
- แสดงความเคลื่อนไหวผู้บริหาร/ผู้ถือหุ้นใหญ่จาก ก.ล.ต. สำหรับหุ้นไทยในพอร์ต

## Out Of Scope
- ข่าว
- เทียบมูลค่ากับเมื่อวานหรือเก็บ history ระยะยาว
- lot/transaction tracking และรายงานภาษีรายล็อต
- dashboard

## Data Flow
1. `main.py` โหลด holdings จาก `config/portfolio.json`
2. `src/data_fetcher.py` ดึงราคา, history, dividend/XD และ USD/THB
3. `src/indicators.py` คำนวณ RSI/Stochastic/Crossover
4. `src/pnl.py` คำนวณ P/L และยอดรวมเป็นบาท
5. `src/indicators.py` ตรวจ High Volume จาก history เดิม
6. `src/sec_filings.py` ดึงแบบ 59 และ 246-2 จากเว็บ ก.ล.ต.
7. `src/report.py` render HTML
8. `src/email_sender.py` ส่งอีเมลผ่าน Resend

## Portfolio Config
`config/portfolio.json`

```json
{
  "holdings": [
    { "ticker": "PTT.BK", "shares": 1000, "avg_cost": 34.50 },
    { "ticker": "AAPL", "shares": 10, "avg_cost": 185.20 }
  ]
}
```

- `ticker`: Yahoo Finance symbol; หุ้นไทยลงท้าย `.BK`, หุ้นสหรัฐใช้ symbol เปล่า
- `shares`: จำนวนหุ้นรวมทุก lot
- `avg_cost`: ทุนเฉลี่ยต่อหุ้นในสกุลของตลาดนั้น

## SEC Insider / Major Shareholder Section
- แหล่งข้อมูล: เว็บ ก.ล.ต. iDisc
- แบบ 59: กรรมการ/ผู้บริหาร ซื้อ/ขาย/โอนหลักทรัพย์ของบริษัทตัวเอง
- แบบ 246-2: ผู้ถือหุ้นใหญ่ข้ามหรือลดเกณฑ์ 5%
- ขอบเขต: เฉพาะหุ้น/กองทุนไทยในพอร์ต (`.BK`); ข้ามหุ้นสหรัฐ
- ช่วงรายงาน: ตั้งแต่เมลรอบก่อนถึงเมื่อวาน ตาม cron อังคาร-เสาร์
  - อังคารครอบเสาร์-อาทิตย์-จันทร์
  - พุธ-เสาร์ครอบเมื่อวานวันเดียว
- ใช้ `rblDateType=2` เพื่อ query ตามวันที่ ก.ล.ต. รับเอกสาร/เผยแพร่ ไม่ใช่วันที่ทำรายการ
- แบบ 59 แสดงชื่อ, ความสัมพันธ์, ซื้อ/ขาย/โอน, จำนวน, ราคา และวันที่ทำรายการ
- แบบ 246-2 ไม่มีราคา/จำนวนหุ้น จึงแสดง % เปลี่ยนและ % หลังรายการ
- ตัด filing ที่วันทำรายการเก่ากว่าวันรับเอกสารเกิน 7 วัน เพื่อลดข้อมูลผิดปีหรือรายการย้อนหลังผิดปกติ
- ถ้าวันไหนแบบ 59 global query ชน cap 100 แถว จะ fallback ไป query รายบริษัทด้วย `FORM59_COMPANY_IDS`
- ถ้าดึงข้อมูล ก.ล.ต. บางส่วนไม่สำเร็จ เมลยังส่งต่อและแสดง warning ใน section นี้

## High Volume Section
- แหล่งข้อมูล: `Volume` จาก yfinance history ที่โหลดอยู่แล้ว
- เกณฑ์ v1: volume วันล่าสุด ≥ 2 เท่าของค่าเฉลี่ย 20 วันก่อนหน้า
- ค่าเฉลี่ย 20 วันไม่รวมวันล่าสุด เพื่อไม่ให้ spike ดึงค่าเฉลี่ยของตัวเองขึ้น
- แสดงเฉพาะหุ้นที่มีข้อมูลอย่างน้อย 21 วันและดึงข้อมูลสำเร็จ
- แสดง ticker, volume/avg20, ราคาเปลี่ยน %, และมูลค่าถือครอง
- ถ้ามีรายการ จะเพิ่ม `High Vol N` ใน subject อีเมล

## SEC Scraper Notes
- iDisc เป็น ASP.NET WebForms ไม่ใช่ JSON API
- Request flow: GET หน้าเพื่อดึง `__VIEWSTATE`, `__VIEWSTATEGENERATOR`, `__EVENTVALIDATION` แล้ว POST ฟอร์มกลับ
- แบบ 59 symbol อยู่ท้ายชื่อบริษัทในวงเล็บ เช่น `บมจ.(SIRI)`
- แบบ 246-2 symbol อยู่ในคอลัมน์แรก
- `DIF` ไม่พบใน dropdown แบบ 59 ตอนตรวจ live จึงไม่มี static company id สำหรับ fallback แบบ 59

## Operations
- Local dry-run: `DRY_RUN=1 PYTHONPATH=. python3 main.py`
- SEC parser tests: `PYTHONPATH=. pytest -q tests/test_sec_filings.py`
- Legacy direct test runner: `PYTHONPATH=. python3 tests/test_sec_filings.py`
- GitHub Actions ใช้ cron `30 0 * * 2-6` ซึ่งเท่ากับ 07:30 Asia/Bangkok อังคาร-เสาร์
- Required secrets: `RESEND_API_KEY`, `REPORT_TO_EMAIL`
- Optional secret: `REPORT_FROM_EMAIL`

## Known Limits
- ราคาเป็น close ล่าสุด ไม่ใช่ real-time
- GitHub cron อาจดีเลย์ 5-15 นาที
- ถ้า USD/THB ดึงไม่ได้ ยอดรวมจะนับเฉพาะหุ้นไทยและขึ้น warning
- ถ้าเว็บ ก.ล.ต. เปลี่ยน markup, ช้า, หรือคืนข้อมูลไม่ครบ section SEC อาจว่างหรือขึ้น warning
