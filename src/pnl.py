"""คำนวณ P/L รายตัว + รวมเป็นบาท (แปลง USD->THB)"""


def currency_of(ticker):
    return "THB" if ticker.endswith(".BK") else "USD"


def position_pnl(holding, price):
    """P/L ของหุ้น 1 ตัว ในสกุลของตลาดมันเอง"""
    shares = holding["shares"]
    cost = holding["avg_cost"] * shares
    value = price * shares
    pl = value - cost
    pl_pct = (pl / cost * 100) if cost else 0.0
    return {
        "ticker": holding["ticker"],
        "name": holding.get("name", holding["ticker"]),
        "currency": currency_of(holding["ticker"]),
        "shares": shares,
        "avg_cost": holding["avg_cost"],
        "price": price,
        "value": value,
        "cost": cost,
        "pl": pl,
        "pl_pct": pl_pct,
    }


def portfolio_totals(positions, usdthb):
    """รวมทุกตัวเป็นบาทก้อนเดียว. ถ้า usdthb is None -> แยกบาท/ดอลลาร์ไม่รวม"""
    thb_value = sum(p["value"] for p in positions if p["currency"] == "THB")
    thb_cost = sum(p["cost"] for p in positions if p["currency"] == "THB")
    usd_value = sum(p["value"] for p in positions if p["currency"] == "USD")
    usd_cost = sum(p["cost"] for p in positions if p["currency"] == "USD")

    out = {
        "thb_value": thb_value,
        "usd_value": usd_value,
        "usdthb": usdthb,
        "fx_ok": usdthb is not None,
    }
    if usdthb is None:
        out["total_value"] = thb_value
        out["total_cost"] = thb_cost
    else:
        total_value = thb_value + usd_value * usdthb
        total_cost = thb_cost + usd_cost * usdthb
        out["total_value"] = total_value
        out["total_cost"] = total_cost
    out["total_pl"] = out["total_value"] - out["total_cost"]
    out["total_pl_pct"] = (out["total_pl"] / out["total_cost"] * 100) if out["total_cost"] else 0.0
    return out


def portfolio_changes(positions, usdthb):
    """% และจำนวนบาทที่มูลค่าพอร์ตเปลี่ยนในแต่ละช่วง จาก changes ของแต่ละตัว

    ย้อนหามูลค่าฐานจาก % ที่คำนวณไว้แล้ว (base = value / (1+pct)) จึงไม่ต้องส่งราคาย้อนหลัง
    เข้ามาอีกชุด ตัวที่ไม่มี % ถูกตัดออกทั้งฝั่ง now และ base เพื่อให้เทียบกันบนชุดเดียวกัน

    ponytail: ใช้เรทวันนี้ทั้งสองฝั่ง ตัวเลขนี้จึงเป็นการเคลื่อนไหวของ "ราคา" ล้วน ไม่รวมผล
    ค่าเงิน ถ้าอยากแยกผลค่าเงินต้องดึง THB=X ย้อนหลังมาเทียบเพิ่ม
    """
    out = {}
    for period in ("d1", "w1", "m1"):
        now = base = 0.0
        for p in positions:
            pct = (p.get("changes") or {}).get(period)
            if pct is None or pct <= -100:  # -100% = ราคาเหลือศูนย์ ย้อนหามูลค่าฐานไม่ได้
                continue
            rate = usdthb if p["currency"] == "USD" else 1
            if rate is None:  # ไม่มีเรท -> ตัดหุ้น USD ออก เหมือนที่ portfolio_totals ทำ
                continue
            value = p["value"] * rate
            now += value
            base += value / (1 + pct / 100)
        out[period] = {"pct": (now / base - 1) * 100 if base else None,
                       "diff": now - base if base else None}
    return out


def _demo():
    pos = [
        position_pnl({"ticker": "PTT.BK", "shares": 1000, "avg_cost": 34.5}, 35.0),
        position_pnl({"ticker": "AAPL", "shares": 10, "avg_cost": 185.2}, 190.0),
    ]
    assert pos[0]["pl"] == 500.0  # (35-34.5)*1000
    assert pos[0]["currency"] == "THB" and pos[1]["currency"] == "USD"
    assert pos[0]["name"] == "PTT.BK"  # default = ticker
    gold = position_pnl({"ticker": "GC=F", "shares": 0.05, "avg_cost": 3974.6, "name": "ทองคำ (oz)"}, 4100.0)
    assert gold["name"] == "ทองคำ (oz)" and gold["currency"] == "USD"
    assert round(gold["value"], 2) == 205.0  # 4100*0.05

    t = portfolio_totals(pos, usdthb=34.0)
    # thb_value=35000, usd_value=1900 -> 35000 + 1900*34 = 99600
    assert round(t["total_value"], 2) == 99600.0
    # cost: 34500 + 1852*34 = 97468 ; pl = 2132
    assert round(t["total_pl"], 2) == 2132.0

    nofx = portfolio_totals(pos, usdthb=None)
    assert nofx["fx_ok"] is False and nofx["total_value"] == 35000.0

    pos[0]["changes"] = {"d1": 10.0, "w1": None, "m1": None}   # ไทย 35,000฿
    pos[1]["changes"] = {"d1": 10.0, "w1": 5.0, "m1": None}    # เมกา $1,900 -> 64,600฿
    ch = portfolio_changes(pos, usdthb=34.0)
    assert round(ch["d1"]["pct"], 6) == 10.0  # ทุกตัว +10% -> พอร์ต +10%
    assert round(ch["w1"]["pct"], 6) == 5.0   # ตัวที่ไม่มีข้อมูลถูกตัดออกทั้งสองฝั่ง
    assert round(ch["w1"]["diff"], 0) == 3076.0  # 64,600 - 64,600/1.05 คิดเป็นบาทแล้ว
    assert ch["m1"]["pct"] is None and ch["m1"]["diff"] is None

    nofx_ch = portfolio_changes(pos, usdthb=None)
    assert round(nofx_ch["d1"]["diff"], 2) == 3181.82  # เหลือแต่หุ้นไทย 35,000 - 35,000/1.1
    assert nofx_ch["w1"]["pct"] is None  # ช่วงนี้มีแต่หุ้น USD ที่ถูกตัดออก
    print("pnl self-check OK")


if __name__ == "__main__":
    _demo()
