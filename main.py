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


def _core_data_errors(holdings, failed, usdthb):
    errors = []
    if failed:
        errors.append(f"price fetch failed: {', '.join(failed)}")
    if usdthb is None and any(pnl.currency_of(h["ticker"]) == "USD" for h in holdings):
        errors.append("USD/THB fetch failed")
    return errors


def build(strict=False):
    holdings = json.loads(CONFIG_PATH.read_text())["holdings"]
    tickers = [h["ticker"] for h in holdings]

    history, failed = data_fetcher.fetch_all(tickers)
    usdthb = data_fetcher.get_usdthb()
    if strict:
        errors = _core_data_errors(holdings, failed, usdthb)
        if errors:
            raise RuntimeError("not sending email: " + "; ".join(errors))

    rows = []
    high_volume_rows = []
    for h in holdings:
        df = history.get(h["ticker"])
        if df is None:
            continue
        price = float(df["Close"].dropna().iloc[-1])
        row = pnl.position_pnl(h, price)
        row["signals"] = indicators.compute_signals(df)
        row["xd_days"] = _xd_days(h["ticker"])
        rows.append(row)
        high_volume = None if h.get("skip_high_volume") else indicators.high_volume_alert(h["ticker"], df, h["shares"])
        if high_volume:
            high_volume["ticker"] = row["name"]
            high_volume["currency"] = row["currency"]
            high_volume_rows.append(high_volume)

    totals = pnl.portfolio_totals(rows, usdthb)

    today = datetime.now(TZ).date()
    thai_symbols = [h["ticker"][:-3] for h in holdings if h["ticker"].endswith(".BK")]
    insider_rows, sec_failed = sec_filings.fetch_filings(thai_symbols, today=today)
    sec_period = _sec_period_label(sec_filings.report_dates(today))

    asof = datetime.now(TZ).strftime("%d/%m/%Y %H:%M")
    html = report.render(asof, totals, rows, failed, insider_rows, sec_failed, sec_period, high_volume_rows)
    alerts = []
    if failed or not totals["fx_ok"]:
        alerts.append("Partial")
    if high_volume_rows:
        alerts.append(f"High Vol {len(high_volume_rows)}")
    alert = f"⚠️ {' / '.join(alerts)} " if alerts else ""
    subject = f"📊 {alert}พอร์ต ฿{totals['total_value']:,.0f} ({totals['total_pl_pct']:+.1f}%) — {asof}"
    return html, subject


def _missing_email_env():
    return [name for name in ("RESEND_API_KEY", "REPORT_TO_EMAIL") if not os.environ.get(name)]


def main():
    dry_run = os.environ.get("DRY_RUN")
    if dry_run:
        html, subject = build()
        print(subject)
        print(html)
        return

    missing = _missing_email_env()
    if missing:
        raise RuntimeError("missing required env: " + ", ".join(missing))

    html, subject = build(strict=True)
    email_sender.send(html, subject)
    print("sent:", subject)


if __name__ == "__main__":
    main()
