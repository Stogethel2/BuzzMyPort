import pytest
import pandas as pd

from src import indicators


def _history(volumes, closes=None):
    closes = closes or [10] * len(volumes)
    return pd.DataFrame(
        {
            "Open": closes,
            "High": closes,
            "Low": closes,
            "Close": closes,
            "Volume": volumes,
        },
        index=pd.date_range("2026-01-01", periods=len(volumes), freq="D"),
    )


def test_compute_signals_uses_adjusted_ohlc_when_available():
    closes = list(range(100, 125))
    df = pd.DataFrame(
        {
            "Open": closes,
            "High": [x + 5 for x in closes],
            "Low": [x - 5 for x in closes],
            "Close": closes,
            "Volume": [100] * len(closes),
        },
        index=pd.date_range("2026-01-01", periods=len(closes), freq="D"),
    )
    df["Adj Close"] = [x * 0.5 if i < 20 else x for i, x in enumerate(closes)]

    ratio = df["Adj Close"] / df["Close"]
    expected_df = df.copy()
    for col in ("Open", "High", "Low", "Close"):
        expected_df[col] = expected_df[col] * ratio

    assert indicators.compute_signals(df)["d1"] == indicators._timeframe_signals(expected_df)


def test_timeframe_signals_include_stoch_d_and_cross():
    closes = [50] * 13 + [10, 10, 10, 10, 10, 20]
    df = pd.DataFrame(
        {
            "Open": closes,
            "High": [100] * len(closes),
            "Low": [0] * len(closes),
            "Close": closes,
            "Volume": [100] * len(closes),
        },
        index=pd.date_range("2026-01-01", periods=len(closes), freq="D"),
    )

    signals = indicators._timeframe_signals(df)

    # raw %K จบที่ [10,10,10,10,10,20] -> slow %K = SMA3 = 13.3, %D = SMA3(%K) = 11.1
    assert signals["stoch_k"] == 13.3
    assert signals["stoch_d"] == 11.1
    assert signals["stoch_cross"] == "up"


def test_high_volume_alert_triggers_at_2x_avg20():
    alert = indicators.high_volume_alert("PTT.BK", _history([100] * 20 + [200], [10] * 20 + [11]), 1000)

    assert alert["ticker"] == "PTT.BK"
    assert alert["latest_volume"] == 200
    assert alert["avg_volume_20"] == 100
    assert alert["volume_ratio"] == 2.0
    assert alert["price_change_pct"] == pytest.approx(10.0)
    assert alert["position_value"] == 11000


def test_high_volume_alert_ignores_low_volume():
    assert indicators.high_volume_alert("PTT.BK", _history([100] * 20 + [199]), 1000) is None


def test_high_volume_alert_requires_21_days():
    assert indicators.high_volume_alert("PTT.BK", _history([100] * 20), 1000) is None


def test_high_volume_alert_requires_latest_volume():
    assert indicators.high_volume_alert("PTT.BK", _history([100] * 20 + [200, None]), 1000) is None


def test_stoch_bias_available_on_first_valid_bar_without_cross():
    """หุ้นเข้าใหม่: (14,3,3) ให้ %D จุดแรกที่แท่งที่ 18 — ต้องรู้ Bull/Bear แม้ยังเทียบ cross ไม่ได้"""
    closes = list(range(10, 28))
    df = pd.DataFrame(
        {
            "Open": closes,
            "High": [100] * len(closes),
            "Low": [0] * len(closes),
            "Close": closes,
            "Volume": [100] * len(closes),
        },
        index=pd.date_range("2026-01-01", periods=len(closes), freq="D"),
    )

    signals = indicators._timeframe_signals(df)

    assert signals["stoch_k"] == 26.0 and signals["stoch_d"] == 25.0
    assert signals["stoch_bias"] == "bull"
    assert signals["stoch_cross"] is None


def test_stoch_k_and_d_always_come_from_the_same_bar():
    """Close ขาดไปแท่งนึงทำให้ %K กับ %D หมดอายุคนละแท่ง — ห้ามรายงานเลขข้ามแท่งกัน"""
    closes = [10 + (i * 7) % 23 for i in range(40)]
    df = pd.DataFrame(
        {
            "Open": closes,
            "High": [x + 3 for x in closes],
            "Low": [x - 3 for x in closes],
            "Close": closes,
            "Volume": [100] * len(closes),
        },
        index=pd.date_range("2026-01-01", periods=len(closes), freq="D"),
    )
    df.loc[df.index[-4], "Close"] = float("nan")  # ตำแหน่งนี้ทำให้ %K กับ %D หมดอายุห่างกัน 4 แท่ง

    signals = indicators._timeframe_signals(df)
    k, d = indicators.stochastic(df)
    same_bar = ((k.round(1) == signals["stoch_k"]) & (d.round(1) == signals["stoch_d"])).any()

    assert signals["stoch_k"] is not None
    assert same_bar, "K/D ที่รายงานไม่ได้เกิดขึ้นพร้อมกันในแท่งเดียว"


def test_rsi_matches_wilder_definition_on_short_series():
    """1W มีแค่ ~52 แท่ง — ถ้า seed ผิด (ewm เปล่า ๆ) ค่าจะเพี้ยนจากนิยาม Wilder"""
    closes = pd.Series([100 + (i * 13) % 17 - (i % 5) for i in range(52)], dtype=float)

    n = 14
    deltas = closes.diff().dropna()
    avg_gain = deltas[:n].clip(lower=0).mean()
    avg_loss = (-deltas[:n].clip(upper=0)).mean()
    for x in deltas[n:]:
        avg_gain = (avg_gain * (n - 1) + max(x, 0)) / n
        avg_loss = (avg_loss * (n - 1) + max(-x, 0)) / n
    expected = 100 - 100 / (1 + avg_gain / avg_loss)

    assert indicators.rsi(closes).iloc[-1] == pytest.approx(expected)


def _closes(pairs):
    """pairs = [(วันที่, ราคา), ...] — index เว้นวันได้ เพื่อจำลองวันหยุด/วันไม่มีเทรด"""
    dates = pd.to_datetime([d for d, _ in pairs])
    prices = [p for _, p in pairs]
    return pd.DataFrame({"Open": prices, "High": prices, "Low": prices,
                         "Close": prices, "Adj Close": prices,
                         "Volume": [100] * len(prices)}, index=dates)


def test_price_changes_1d_uses_previous_bar():
    df = _closes([("2026-01-01", 100), ("2026-01-02", 110)])

    assert indicators.price_changes(df)["d1"] == pytest.approx(10.0)


def test_price_changes_1w_skips_non_trading_days():
    """anchor-7วัน ตรงกับวันหยุด — ต้องถอยไปแท่งล่าสุดที่มีจริง ไม่ใช่นับถอย 5 แท่ง"""
    days = [("2026-01-%02d" % d, 100.0) for d in range(1, 21)]
    days[-1] = ("2026-01-20", 50.0)  # แท่งสุดท้ายก่อนช่วงหยุดยาว 21-23
    df = _closes(days + [("2026-01-24", 60.0), ("2026-01-30", 100.0)])

    # anchor 30/01 - 7 วัน = 23/01 ไม่มีแท่ง -> ต้องใช้ 20/01 ที่ราคา 50
    assert indicators.price_changes(df)["w1"] == pytest.approx(100.0)


def test_price_changes_1m_uses_calendar_month():
    df = _closes([("2026-01-15", 100.0), ("2026-02-01", 200.0), ("2026-03-01", 220.0)])

    assert indicators.price_changes(df)["m1"] == pytest.approx(10.0)


def test_price_changes_none_when_history_too_short():
    df = _closes([("2026-03-01", 100.0), ("2026-03-02", 101.0)])

    changes = indicators.price_changes(df)

    assert changes["d1"] == pytest.approx(1.0)
    assert changes["w1"] is None and changes["m1"] is None


def test_price_changes_all_none_on_single_bar():
    assert indicators.price_changes(_closes([("2026-03-02", 100.0)])) == {"d1": None, "w1": None, "m1": None}


def test_price_changes_uses_adjusted_close_so_xd_is_not_a_fake_drop():
    df = _closes([("2026-03-01", 100.0), ("2026-03-02", 100.0)])
    df["Close"] = [100.0, 98.0]  # วันขึ้น XD ปันผล 2 บาท — ราคาดิบตก แต่ Adj Close เท่าเดิม

    assert indicators.price_changes(df)["d1"] == 0.0


def test_price_changes_keeps_full_precision_for_portfolio_math():
    """pnl.portfolio_changes ย้อนหามูลค่าฐานจาก % นี้ — ปัดเศษที่นี่ทำให้ยอดรวมคลาดหลักร้อยบาท"""
    df = _closes([("2026-03-01", 100.0), ("2026-03-02", 99.96)])

    assert indicators.price_changes(df)["d1"] == pytest.approx(-0.04)


def test_price_changes_handles_timezone_aware_index():
    """ของจริงจาก yfinance เป็น tz-aware และตลาดเมกาข้ามเส้น DST ระหว่างทาง"""
    df = _closes([("2026-10-15", 100.0), ("2026-11-14", 100.0), ("2026-11-15", 110.0)])
    df.index = df.index.tz_localize("America/New_York")

    assert indicators.price_changes(df)["m1"] == pytest.approx(10.0)


def test_price_changes_1w_is_seven_calendar_days_across_spring_dst():
    """ตลาดเมกาสัปดาห์ปรับเวลา: ลบ 168 ชม. จะได้ 03-02 23:00 EST แล้ว asof หลุดไปแท่ง 03-02"""
    df = _closes([("2026-03-02", 50.0), ("2026-03-03", 100.0), ("2026-03-10", 110.0)])
    df.index = df.index.tz_localize("America/New_York")

    assert indicators.price_changes(df)["w1"] == pytest.approx(10.0)  # เทียบ 03-03 ไม่ใช่ 03-02
