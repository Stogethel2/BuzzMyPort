import json
import sys
import types

import pytest

sys.modules.setdefault("yfinance", types.SimpleNamespace(Ticker=lambda ticker: None))
sys.modules.setdefault(
    "resend",
    types.SimpleNamespace(api_key=None, Emails=types.SimpleNamespace(send=lambda payload: payload)),
)

import main


def _portfolio(tmp_path, holdings):
    path = tmp_path / "portfolio.json"
    path.write_text(json.dumps({"holdings": holdings}))
    return path


def test_build_strict_rejects_failed_price_fetch(monkeypatch, tmp_path):
    monkeypatch.setattr(
        main,
        "CONFIG_PATH",
        _portfolio(tmp_path, [{"ticker": "PTT.BK", "shares": 1, "avg_cost": 1}]),
    )
    monkeypatch.setattr(main.data_fetcher, "fetch_all", lambda tickers: ({}, ["PTT.BK"]))
    monkeypatch.setattr(main.data_fetcher, "get_usdthb", lambda: 33.0)

    with pytest.raises(RuntimeError, match="price fetch failed: PTT.BK"):
        main.build(strict=True)


def test_build_strict_rejects_missing_fx_for_usd_holding(monkeypatch, tmp_path):
    monkeypatch.setattr(
        main,
        "CONFIG_PATH",
        _portfolio(tmp_path, [{"ticker": "QQQM", "shares": 1, "avg_cost": 1}]),
    )
    monkeypatch.setattr(main.data_fetcher, "fetch_all", lambda tickers: ({}, []))
    monkeypatch.setattr(main.data_fetcher, "get_usdthb", lambda: None)

    with pytest.raises(RuntimeError, match="USD/THB fetch failed"):
        main.build(strict=True)


def test_main_rejects_real_run_without_required_email_env(monkeypatch):
    monkeypatch.delenv("DRY_RUN", raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("REPORT_TO_EMAIL", raising=False)
    monkeypatch.setattr(main, "build", lambda strict=False: ("html", "subject"))

    with pytest.raises(RuntimeError, match="missing required env: RESEND_API_KEY, REPORT_TO_EMAIL"):
        main.main()


def test_main_dry_run_allows_missing_email_env(monkeypatch, capsys):
    monkeypatch.setenv("DRY_RUN", "1")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("REPORT_TO_EMAIL", raising=False)
    monkeypatch.setattr(main, "build", lambda strict=False: ("html", "subject"))

    main.main()

    assert "subject" in capsys.readouterr().out


def _xd_unavailable(ticker):
    raise RuntimeError("rate limited")


def test_build_reports_xd_fetch_failure_without_blocking_the_email(monkeypatch, tmp_path):
    """XD ดึงไม่ได้ = ข้อมูลเสริมหาย ต้องเตือนในเมล แต่ห้ามล้มทั้งฉบับเหมือนราคาหาย"""
    import pandas as pd

    monkeypatch.setattr(
        main,
        "CONFIG_PATH",
        _portfolio(tmp_path, [{"ticker": "PTT.BK", "shares": 1, "avg_cost": 1}]),
    )
    df = pd.DataFrame(
        {"Open": [10] * 5, "High": [11] * 5, "Low": [9] * 5, "Close": [10] * 5, "Volume": [1] * 5},
        index=pd.date_range("2026-01-01", periods=5, freq="D"),
    )
    monkeypatch.setattr(main.data_fetcher, "fetch_all", lambda tickers: ({"PTT.BK": df}, []))
    monkeypatch.setattr(main.data_fetcher, "get_usdthb", lambda: 33.0)
    monkeypatch.setattr(main.data_fetcher, "get_next_xd", _xd_unavailable)
    monkeypatch.setattr(main.sec_filings, "fetch_filings", lambda symbols, today=None: ([], []))
    monkeypatch.setattr(main.sec_filings, "report_dates", lambda today: [])

    html, subject = main.build(strict=True)

    assert "เช็ควัน XD ไม่ได้ 1 ตัว (PTT.BK)" in html
    assert "พอร์ต" in subject


def test_build_skips_xd_for_instruments_without_a_dividend_calendar(monkeypatch, tmp_path):
    """ETF/ฟิวเจอร์สไม่มีปฏิทินปันผลเลย ต้องไม่ถูกนับเป็น 'ดึงไม่ได้' ทุกวัน"""
    import pandas as pd

    monkeypatch.setattr(
        main,
        "CONFIG_PATH",
        _portfolio(tmp_path, [{"ticker": "GC=F", "shares": 1, "avg_cost": 1, "skip_xd": True}]),
    )
    df = pd.DataFrame(
        {"Open": [10] * 5, "High": [11] * 5, "Low": [9] * 5, "Close": [10] * 5, "Volume": [1] * 5},
        index=pd.date_range("2026-01-01", periods=5, freq="D"),
    )
    monkeypatch.setattr(main.data_fetcher, "fetch_all", lambda tickers: ({"GC=F": df}, []))
    monkeypatch.setattr(main.data_fetcher, "get_usdthb", lambda: 33.0)
    monkeypatch.setattr(main.data_fetcher, "get_next_xd", _xd_unavailable)
    monkeypatch.setattr(main.sec_filings, "fetch_filings", lambda symbols, today=None: ([], []))
    monkeypatch.setattr(main.sec_filings, "report_dates", lambda today: [])

    html, _ = main.build(strict=True)

    assert "เช็ควัน XD ไม่ได้" not in html


def _yf_calendar(cal):
    return types.SimpleNamespace(Ticker=lambda ticker: types.SimpleNamespace(calendar=cal))


def test_get_next_xd_treats_empty_calendar_as_fetch_failure(monkeypatch):
    """yfinance กลืน HTTP error เองแล้วคืน {} — ห้ามตีความว่า 'ไม่มีปันผล'"""
    monkeypatch.setattr(main.data_fetcher, "yf", _yf_calendar({}))

    with pytest.raises(RuntimeError, match="calendar unavailable"):
        main.data_fetcher.get_next_xd("PTT.BK")


def test_get_next_xd_returns_none_when_calendar_has_no_ex_dividend_date(monkeypatch):
    """เคส DIF.BK ของจริง: ดึงสำเร็จ มีคีย์ Earnings แต่ไม่มี Ex-Dividend Date = ไม่มี XD รอ"""
    monkeypatch.setattr(main.data_fetcher, "yf", _yf_calendar({"Earnings Date": [], "Earnings High": None}))

    assert main.data_fetcher.get_next_xd("DIF.BK") is None


def test_get_next_xd_still_reads_legacy_dataframe_calendar(monkeypatch):
    """yfinance รุ่นเก่าคืน calendar เป็น DataFrame — เช็คว่างต้องไม่ไปโยน ValueError ทับ"""
    import pandas as pd

    cal = pd.DataFrame({0: [pd.Timestamp("2026-09-15")]}, index=["Ex-Dividend Date"])
    monkeypatch.setattr(main.data_fetcher, "yf", _yf_calendar(cal))

    assert main.data_fetcher.get_next_xd("PTT.BK") == pd.Timestamp("2026-09-15")
