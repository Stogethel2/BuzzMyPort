"""RSI + Stochastic + Crossover บน timeframe 1D และ 1W (pure pandas)

ponytail: ไม่ใช้ pandas_ta — RSI/Stoch ตัวละ ~10 บรรทัด และ pandas_ta พังกับ numpy ใหม่บ่อย
"""
import pandas as pd


def rsi(close, length=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def stochastic(df, k=14, d=3):
    low_min = df["Low"].rolling(k).min()
    high_max = df["High"].rolling(k).max()
    percent_k = 100 * (df["Close"] - low_min) / (high_max - low_min)
    percent_d = percent_k.rolling(d).mean()
    return percent_k, percent_d


def _timeframe_signals(df):
    r = rsi(df["Close"])
    k, _ = stochastic(df)
    return {
        "rsi": round(float(r.dropna().iloc[-1]), 1) if r.notna().any() else None,
        "stoch_k": round(float(k.dropna().iloc[-1]), 1) if k.notna().any() else None,
    }


def _to_weekly(df):
    weekly = df.resample("W").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    ).dropna(how="any")
    # ponytail: ตัดสัปดาห์ปัจจุบันที่ยังไม่ปิด (จ-พฤ) กันสัญญาณ repaint กลางสัปดาห์
    # heuristic ตามวันในสัปดาห์ ไม่เป๊ะกรณีวันหยุดศุกร์ — พอสำหรับรายงานเช้า
    if not df.empty and df.index[-1].weekday() < 4 and len(weekly) > 1:
        weekly = weekly.iloc[:-1]
    return weekly


def compute_signals(df):
    """คืน {'d1': {...}, 'w1': {...}} สำหรับหุ้น 1 ตัว"""
    return {"d1": _timeframe_signals(df), "w1": _timeframe_signals(_to_weekly(df))}
