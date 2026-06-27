# Stock Portfolio Daily Alert

อีเมลสรุปพอร์ตหุ้นอัตโนมัติทุกเช้า 07:30 (จ–ศ) ผ่าน GitHub Actions
แสดง **มูลค่าพอร์ตรวมเป็นบาท** (แปลง USD→THB) + P/L จากต้นทุน + Momentum (RSI/Stochastic/Crossover 1D & 1W) + เตือน XD

## พอร์ตของคุณ — `config/portfolio.json`
```json
{
  "holdings": [
    { "ticker": "PTT.BK", "shares": 1000, "avg_cost": 34.50 },
    { "ticker": "AAPL",   "shares": 10,   "avg_cost": 185.20 }
  ]
}
```
- `ticker` — รูปแบบ Yahoo Finance: หุ้นไทยลงท้าย `.BK`, หุ้นเมกาใส่ symbol เปล่า
- `shares` — จำนวนหุ้นถือ (รวมทุก lot)
- `avg_cost` — ราคาทุนเฉลี่ย/หุ้น สกุลตามตลาด (฿ สำหรับ `.BK`, $ สำหรับเมกา)

## รัน local (ไม่ส่งเมล)
```bash
pip install -r requirements.txt
DRY_RUN=1 python main.py      # พิมพ์ HTML ออกจอ
python -m src.pnl             # self-check การคำนวณ P/L + FX
```

## Deploy
1. push ขึ้น GitHub repo
2. ตั้ง **Secrets** (Settings → Secrets and variables → Actions):
   - `RESEND_API_KEY` — จาก resend.com (free 3,000/เดือน)
   - `REPORT_TO_EMAIL` — อีเมลปลายทาง
   - `REPORT_FROM_EMAIL` — *(ไม่บังคับ)* ดีฟอลต์ `onboarding@resend.dev` ตอนทดสอบ
3. แท็บ Actions → *Daily Stock Report* → **Run workflow** เพื่อทดสอบ

## หมายเหตุ / ข้อจำกัด v1
- ราคา ณ 07:30 เป็น **close ล่าสุด** (ไทย=วันก่อน, เมกา=คืนก่อน) — เป็น snapshot เช้า ไม่ใช่ราคา real-time
- GitHub cron ดีเลย์ได้ 5–15 นาที
- เรท USD→THB ดึงไม่ได้ → ยอดรวมนับเฉพาะหุ้นไทย + เตือนในเมล
- ยังไม่มี: ข่าว/insider, เทียบมูลค่าเมื่อวาน, lot tracking (เลื่อนไป v2)
