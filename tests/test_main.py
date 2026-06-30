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
