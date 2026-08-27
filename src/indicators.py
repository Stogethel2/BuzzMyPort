"""RSI + Stochastic + Crossover บน timeframe 1D และ 1W (pure pandas)

ponytail: ไม่ใช้ pandas_ta — RSI/Stoch ตัวละ ~10 บรรทัด และ pandas_ta พังกับ numpy ใหม่บ่อย
"""
import pandas as pd


def high_volume_alert(ticker, df, shares, threshold=2.0, window=20):
    if "Volume" not in df or len(df) <= window:
        return None
    latest_volume = df["Volume"].iloc[-1]
    prior_volumes = df["Volume"].iloc[-window - 1:-1].dropna()
    if pd.isna(latest_volume) or len(prior_volumes) < window:
        return None

    latest_volume = float(latest_volume)
    avg_volume = float(prior_volumes.mean())
    if avg_volume <= 0 or latest_volume / avg_volume < threshold:
        return None

    closes = df["Close"].dropna()
    price = float(closes.iloc[-1])
    prev_price = float(closes.iloc[-2]) if len(closes) > 1 else None
    price_change_pct = ((price - prev_price) / prev_price * 100) if prev_price else None
    return {
        "ticker": ticker,
        "latest_volume": latest_volume,
        "avg_volume_20": avg_volume,
        "volume_ratio": round(latest_volume / avg_volume, 2),
        "price_change_pct": round(price_change_pct, 1) if price_change_pct is not None else None,
        "position_value": price * shares,
    }


def _wilder_avg(series, length):
    """ค่าเฉลี่ยแบบ Wilder — seed ด้วย SMA ของ length ค่าแรก แล้วค่อย smooth ต่อ

    ewm เปล่า ๆ จะ seed จากค่าแรกค่าเดียว บน 1W ที่มีแค่ ~52 แท่ง อคติจาก seed
    ยังเหลือพอทำให้ RSI เพี้ยนได้ถึง ~3.5 จุด (พอพลิกสีที่เส้น 70/30) ส่วน 1D ที่มี
    ~250 แท่งไม่ต่างเลย
    """
    s = series.dropna()  # delta ตัวแรกเป็น NaN เสมอ — seed ต้องนับจาก delta จริง 14 ตัวแรก
    if len(s) < length:
        return pd.Series(float("nan"), index=series.index)
    seeded = s.astype(float).copy()
    seeded.iloc[:length] = float("nan")
    seeded.iloc[length - 1] = s.iloc[:length].mean()
    return seeded.ewm(alpha=1 / length, adjust=False, ignore_na=True).mean().reindex(series.index)


def rsi(close, length=14):
    delta = close.diff()
    avg_gain = _wilder_avg(delta.clip(lower=0), length)
    avg_loss = _wilder_avg(-delta.clip(upper=0), length)
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def stochastic(df, k=14, smooth_k=3, d=3):
    """Slow Stochastic (14,3,3) — %K = SMA3 ของ raw %K, %D = SMA3 ของ %K

    smooth_k=3 ทำให้ตรงกับ default ของ TradingView/StockCharts (สูตรเดิมของ Lane)
    ถ้าไม่ smooth จะได้ Fast Stochastic ซึ่งตัวเลขไม่ตรงกับกราฟที่คนดูกัน
    """
    low_min = df["Low"].rolling(k).min()
    high_max = df["High"].rolling(k).max()
    raw_k = 100 * (df["Close"] - low_min) / (high_max - low_min)
    percent_k = raw_k.rolling(smooth_k).mean()
    percent_d = percent_k.rolling(d).mean()
    return percent_k, percent_d


def _adjusted_ohlc(df):
    if "Adj Close" not in df or "Close" not in df:
        return df
    out = df.copy()
    ratio = out["Adj Close"] / out["Close"]
    out[["Open", "High", "Low", "Close"]] = out[["Open", "High", "Low", "Close"]].mul(ratio, axis=0)
    return out


def _stoch_state(kd):
    """คืน (bias, cross) จากสองแถวล่าสุดของตาราง K/D ที่จับคู่กันแล้ว

    bias คำนวณที่นี่ด้วยค่าไม่ปัดเศษ ไม่ใช่ที่ template — K/D ที่ปัดทศนิยม 1 ตำแหน่ง
    แล้วเท่ากันจะกลายเป็น Flat ทั้งที่จริงตัดกันอยู่ (Slow Stoch ทำให้ K/D ชิดกันบ่อย)
    """
    latest_k, latest_d = kd.iloc[-1]
    bias = "bull" if latest_k > latest_d else "bear" if latest_k < latest_d else "flat"
    if len(kd) < 2:  # bias ใช้แถวเดียวพอ, cross ต้องมีแถวก่อนหน้าเทียบ
        return bias, None
    prev_k, prev_d = kd.iloc[-2]
    if prev_k <= prev_d and latest_k > latest_d:
        return bias, "up"
    if prev_k >= prev_d and latest_k < latest_d:
        return bias, "down"
    return bias, None


def _timeframe_signals(df):
    r = rsi(df["Close"]).dropna()
    # จับคู่ K/D ก่อน dropna เพื่อให้เลข K, เลข D และทิศ Bull/Bear มาจากแท่งเดียวกันเสมอ
    kd = pd.concat(stochastic(df), axis=1).dropna()
    bias, cross = _stoch_state(kd) if not kd.empty else (None, None)
    return {
        "rsi": round(float(r.iloc[-1]), 1) if not r.empty else None,
        "stoch_k": round(float(kd.iloc[-1, 0]), 1) if not kd.empty else None,
        "stoch_d": round(float(kd.iloc[-1, 1]), 1) if not kd.empty else None,
        "stoch_bias": bias,
        "stoch_cross": cross,
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
    df = _adjusted_ohlc(df)
    return {"d1": _timeframe_signals(df), "w1": _timeframe_signals(_to_weekly(df))}
