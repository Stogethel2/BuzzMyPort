"""ดึงข้อมูลจาก yfinance: ราคา/history/dividends ต่อ ticker + เรท USD->THB"""
import logging
import time
import yfinance as yf

# yfinance log HTTP 404 เองตอนหา calendar/XD ของ ETF ไม่เจอ — เราดักด้วย try/except อยู่แล้ว ปิด noise
logging.getLogger("yfinance").setLevel(logging.CRITICAL)


def _retry(fn, attempts=3, base_delay=2):
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:  # yfinance โยน error หลายชนิด rate-limit/network
            last = e
            time.sleep(base_delay * (i + 1))
    raise last


def fetch_ticker(ticker, period="1y"):
    """คืน DataFrame รายวัน (มีคอลัมน์ Open/High/Low/Close/Dividends). โยน error ถ้าว่าง"""
    def _fetch():
        df = yf.Ticker(ticker).history(period=period, auto_adjust=False)
        if df is None or df.empty:  # ใน _retry เพื่อให้ response ว่างถูก retry ด้วย
            raise ValueError(f"no data for {ticker}")
        return df
    return _retry(_fetch)


def fetch_all(tickers, period="1y"):
    """ดึงทุก ticker แบบทนตัวพัง: คืน (ok: dict[ticker]=df, failed: list[ticker])"""
    ok, failed = {}, []
    for t in tickers:
        try:
            ok[t] = fetch_ticker(t, period)
        except Exception:
            failed.append(t)
    return ok, failed


def get_next_xd(ticker):
    """วันขึ้นเครื่องหมาย XD ที่จะถึง (date) หรือ None ถ้าไม่มีปันผลรอคิว

    โยน error ถ้าดึง calendar ไม่ได้ (rate-limit/network) — "ไม่มี XD" กับ "ดึงไม่ได้"
    คนละเรื่องกัน ถ้ากลืนเป็น None ทั้งคู่ badge XD จะหายเงียบโดยไม่มีใครรู้

    yfinance กลืน HTTPError เองแล้วคืน calendar เป็น {} (scrapers/quote.py _fetch_calendar)
    จึงต้องใช้ "dict ว่าง" เป็นสัญญาณว่าดึงไม่สำเร็จ — หุ้นที่ดึงได้จริงจะมีคีย์ Earnings*
    ติดมาเสมอแม้ไม่มีปันผลรอ (เช็คกับพอร์ตจริงแล้ว DIF.BK ไม่มี Ex-Dividend Date แต่ dict ไม่ว่าง)
    ตราสารที่ไม่มีปฏิทินเลยจริง ๆ (ETF/ฟิวเจอร์ส) ให้ตั้ง skip_xd ใน portfolio.json
    yfinance .calendar คืน dict หรือ DataFrame แล้วแต่เวอร์ชัน — กันทั้งสองแบบ
    """
    cal = yf.Ticker(ticker).calendar
    if cal is None or len(cal) == 0:  # len() ไม่ใช่ truthiness — DataFrame โยน ValueError
        raise RuntimeError(f"calendar unavailable for {ticker}")
    if isinstance(cal, dict):
        val = cal.get("Ex-Dividend Date")
    else:  # DataFrame เก่า
        val = cal.loc["Ex-Dividend Date"].iloc[0] if "Ex-Dividend Date" in cal.index else None
    if val is None:
        return None
    return val[0] if isinstance(val, list) else val


def get_usdthb():
    """เรท USD->THB จาก yfinance. คืน None ถ้าดึงไม่ได้ (caller ตัดสินใจ fallback)"""
    try:
        df = fetch_ticker("THB=X", period="5d")
        return float(df["Close"].dropna().iloc[-1])
    except Exception:
        return None
