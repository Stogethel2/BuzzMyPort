# Plan: Stock Portfolio Daily Alert (v1)

## Context
ต้องการระบบส่ง **อีเมลสรุปพอร์ตหุ้นอัตโนมัติทุกเช้า** (07:30 น. จ–ศ) โดยรันฟรีบน GitHub Actions
แทนการจ่ายค่า TradingView เหตุผล: ฟรี/ถูก, customize logic เองได้ (โดยเฉพาะ Crossover), ขยายต่อง่าย

เป้าหมาย v1: รู้ **มูลค่าพอร์ตรวมเป็นบาทก้อนเดียว** (แปลง USD→THB) + P/L จากต้นทุน + สัญญาณ Momentum (1D/1W) + เตือน XD ของแต่ละตัว

## Scope
**In (v1):**
- รองรับหุ้นไทย (`.BK`) + หุ้นเมกา ใน port เดียวกัน
- มูลค่ารวมทั้งพอร์ตเป็นบาท (แปลง USD→THB ด้วยเรทจาก yfinance)
- P/L รายตัว + P/L รวมจากต้นทุน
- Momentum 1D และ 1W: RSI + Stochastic + ตรวจ Crossover (golden/dead)
- เตือน XD (ex-dividend) ที่ใกล้ถึง
- ส่งอีเมล HTML ทุก 07:30 ICT จ–ศ

**Out (เลื่อนไป v2):**
- ข่าว (News impact) + Insider trading
- การเทียบมูลค่ากับเมื่อวาน / เก็บ history (ไม่มี state เลยใน v1)
- Lot/transaction tracking, รายงานภาษีรายล็อต
- Streamlit dashboard

## ไฟล์ config

### config/portfolio.json (คน maintain)
```json
{
  "holdings": [
    { "ticker": "PTT.BK", "shares": 1000, "avg_cost": 34.50 },
    { "ticker": "AAPL",   "shares": 10,   "avg_cost": 185.20 }
  ]
}
```
- `ticker`: รูปแบบ Yahoo Finance ตรง ๆ (`.BK` = ไทย, symbol เปล่า = เมกา)
- `shares`: จำนวนหุ้นถือ (รวมทุก lot)
- `avg_cost`: ราคาทุนเฉลี่ย/หุ้น สกุลตามตลาดของหุ้นนั้น (THB สำหรับ .BK, USD สำหรับเมกา)

## โครงไฟล์
```
stock-portfolio-alert/
├── .github/workflows/daily-report.yml
├── config/portfolio.json
├── src/
│   ├── data_fetcher.py   # yfinance: ราคา + history + dividends + เรท USDTHB
│   ├── indicators.py     # pandas_ta: RSI, Stoch, crossover (1D & 1W)
│   ├── pnl.py            # P/L รายตัว + รวมเป็นบาท (แปลง USD)
│   ├── report.py         # render HTML (Jinja2)
│   └── email_sender.py   # Resend
├── main.py               # orchestrate ทั้งหมด
├── requirements.txt      # yfinance pandas pandas_ta resend jinja2
└── README.md
```

## Architecture / flow (main.py)
1. โหลด `config/portfolio.json`
2. `data_fetcher`: batch download ราคา+history ทุก ticker ครั้งเดียว + ดึงเรท `THB=X` + dividends
3. `indicators`: คำนวณ RSI/Stoch บน timeframe 1D และ 1W (resample รายสัปดาห์) + detect crossover
4. `pnl`: คำนวณ P/L รายตัว → แปลงมูลค่าเมกาเป็นบาท → รวมเป็นยอดเดียว + P/L รวม
5. ตรวจ XD จาก dividends (ex-date ที่ใกล้ถึง)
6. `report`: สร้าง HTML (ส่วนหัว = มูลค่ารวมบาท, ตารางรายตัว, สัญญาณ, XD badge)
7. `email_sender`: ส่งผ่าน Resend

## ส่วนหัวรายงาน (ตัวอย่าง)
```
มูลค่าพอร์ตรวม (27 มิ.ย. 2026, 07:30)
รวมทั้งหมด: ฿417,800
 - หุ้นไทย:  ฿353,100
 - หุ้นเมกา: $1,881 -> ฿64,700  (เรท 34.40 ฿/$)
กำไร/ขาดทุนรวม: +฿20,300 (+5.1%) จากต้นทุน
```

## GitHub Actions
```yaml
on:
  schedule:
    - cron: "30 0 * * 1-5"   # 00:30 UTC = 07:30 ICT, จ-ศ
  workflow_dispatch: {}        # ปุ่มรันมือทดสอบ
```
- Secrets: `RESEND_API_KEY`, `REPORT_TO_EMAIL`
- ไม่ต้องมี `permissions: contents: write` (v1 ไม่เขียน state กลับ repo)
- หมายเหตุ: GitHub cron ดีเลย์ได้ 5–15 นาที — รับได้สำหรับรายงานเช้า

## Edge cases ที่ต้องจัดการ
| กรณี | พฤติกรรม |
|---|---|
| ticker ตัวเดียวดึงไม่ได้ | try/except ต่อตัว → รายงานตัวที่ได้ + list ตัวที่ fail ท้ายเมล ไม่ล้มทั้งงาน |
| เรท USD->THB ดึงไม่ได้ | retry 3 ครั้ง backoff → ถ้ายังพัง: แสดงเมกาเป็น $ แยก + แจ้งเตือนในเมล |
| ตลาดปิด / วันหยุด | ใช้ close ล่าสุดที่มี ไม่ error |
| 07:30 ICT ก่อนตลาดเปิด | ราคาเป็น close ล่าสุด (เมกา=คืนก่อน, ไทย=วันก่อน) ถูกต้องสำหรับ snapshot เช้า |
| yfinance rate-limit | batch download ครั้งเดียว + retry backoff |

## Phases การ implement (≈ 4–5 วัน)
1. **Foundation + มูลค่ารวมบาท (1–1.5 วัน)**: อ่าน port.json, batch fetch ราคา+เรท, คำนวณ P/L รายตัว + ยอดรวมบาท, print console
2. **Indicators + Crossover (1–2 วัน)**: RSI/Stoch บน 1D & 1W + detect golden/dead cross
3. **XD alert (0.5–1 วัน)**: หา ex-date ใกล้ถึงจาก dividends แล้วติด badge
4. **Email + Cron (1 วัน)**: HTML report + ส่ง Resend + ตั้ง Actions cron
5. **Polish (0.5 วัน)**: error handling ตามตาราง edge case + README

## Verification
- **Phase 1 local**: `python main.py` แล้วได้ยอดรวมบาทถูกต้อง (เทียบมือ: shares × close, เมกาแปลงด้วยเรท)
- **Indicators**: เทียบ flag crossover กับกราฟจริงของหุ้น 1–2 ตัว
- **Email**: รัน `workflow_dispatch` บน Actions → ได้เมลจริงเข้า `REPORT_TO_EMAIL`
- **Robustness**: ใส่ ticker ปลอม 1 ตัวใน port.json → รายงานยังส่งได้ + แจ้งตัว fail
- **Self-check**: เพิ่ม assert-based check ใน `pnl.py` (เช่น `__main__` ทดสอบ P/L + การแปลง FX ด้วยข้อมูลจำลอง)

## Open item
- ต้องการ **อีเมลปลายทาง** (`REPORT_TO_EMAIL`) และตั้ง `RESEND_API_KEY` ใน GitHub Secrets ก่อน deploy
