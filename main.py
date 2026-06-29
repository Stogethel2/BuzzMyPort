"""Stock Portfolio Daily Alert — orchestrate ทั้งหมด

รัน local แบบ dry-run (พิมพ์ HTML ออกจอ ไม่ส่งเมล):
    DRY_RUN=1 python main.py
รันจริง (ส่งเมล) ต้องตั้ง RESEND_API_KEY + REPORT_TO_EMAIL
"""
import json
import os
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

from src import data_fetcher, indicators, pnl, report, email_sender, sec_filings

CONFIG_PATH = Path(__file__).parent / "config" / "portfolio.json"
TZ = ZoneInfo("Asia/Bangkok")
XD_WINDOW_DAYS = 14


def _sec_period_label(dates):
    """ป้ายช่วง 'วันรับเอกสาร' ในเมล เป็น พ.ศ. — วันเดียวหรือช่วง"""
    if not dates:
        return ""
    fmt = lambda d: f"{d.day:02d}/{d.month:02d}/{d.year + 543}"
    return fmt(dates[0]) if len(dates) == 1 else f"{fmt(dates[0])}–{fmt(dates[-1])}"


def _xd_days(ticker):
    nxt = data_fetcher.get_next_xd(ticker)
    if nxt is None:
        return None
    d = nxt.date() if hasattr(nxt, "date") else nxt
    if not isinstance(d, date):
        return None
    days = (d - datetime.now(TZ).date()).days
    return days if 0 <= days <= XD_WINDOW_DAYS else None


def build():
    holdings = json.loads(CONFIG_PATH.read_text())["holdings"]
    tickers = [h["ticker"] for h in holdings]

    history, failed = data_fetcher.fetch_all(tickers)
    usdthb = data_fetcher.get_usdthb()

    rows = []
    for h in holdings:
        df = history.get(h["ticker"])
        if df is None:
            continue
        price = float(df["Close"].dropna().iloc[-1])
        row = pnl.position_pnl(h, price)
        row["signals"] = indicators.compute_signals(df)
        row["xd_days"] = _xd_days(h["ticker"])
        rows.append(row)

    totals = pnl.portfolio_totals(rows, usdthb)

    today = datetime.now(TZ).date()
    thai_symbols = [h["ticker"][:-3] for h in holdings if h["ticker"].endswith(".BK")]
    insider_rows, sec_failed = sec_filings.fetch_filings(thai_symbols, today=today)
    sec_period = _sec_period_label(sec_filings.report_dates(today))

    asof = datetime.now(TZ).strftime("%d/%m/%Y %H:%M")
    html = report.render(asof, totals, rows, failed, insider_rows, sec_failed, sec_period)
    partial = "⚠️ " if (failed or not totals["fx_ok"]) else ""
    subject = f"📊 {partial}พอร์ต ฿{totals['total_value']:,.0f} ({totals['total_pl_pct']:+.1f}%) — {asof}"
    return html, subject


def main():
    html, subject = build()
    has_creds = os.environ.get("RESEND_API_KEY") and os.environ.get("REPORT_TO_EMAIL")
    if os.environ.get("DRY_RUN") or not has_creds:
        print(subject)
        print(html)
        return
    email_sender.send(html, subject)
    print("sent:", subject)


if __name__ == "__main__":
    main()
