import importlib
import os
import sys
import types
from dataclasses import dataclass
from unittest.mock import Mock

import pandas as pd
import pytest
import requests as real_requests


@dataclass
class FakeCompletion:
    text: str
    start_position: int
    display: str


class FakeCompleter:
    pass


@pytest.fixture
def app_modules(monkeypatch):
    """Load app modules with external dependencies replaced by local fakes."""
    prompt_toolkit = types.ModuleType("prompt_toolkit")
    prompt_toolkit.PromptSession = Mock()
    completion_module = types.ModuleType("prompt_toolkit.completion")
    completion_module.Completer = FakeCompleter
    completion_module.Completion = FakeCompletion
    monkeypatch.setitem(sys.modules, "prompt_toolkit", prompt_toolkit)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.completion", completion_module)

    requests_module = types.ModuleType("requests")
    requests_module.get = Mock()
    monkeypatch.setitem(sys.modules, "requests", requests_module)

    for name in ("search", "stock_cache", "completer", "main"):
        sys.modules.pop(name, None)
    modules = {
        name: importlib.import_module(name)
        for name in ("search", "stock_cache", "completer", "main")
    }
    yield modules
    for name in modules:
        sys.modules.pop(name, None)


@pytest.fixture
def stocks():
    return [
        {"name": "삼성전자", "code": "005930", "market": "KOSPI"},
        {"name": "삼성SDI", "code": "006400", "market": "KOSPI"},
        {"name": "LG전자", "code": "066570", "market": "KOSPI"},
        {"name": "하나금융지주", "code": "086790", "market": "KOSPI"},
    ]


def test_search_matches_exact_name_first(app_modules, stocks):
    search_stocks = app_modules["search"].search_stocks
    extra = {"name": "삼성전자우", "code": "005935", "market": "KOSPI"}
    assert search_stocks(stocks + [extra], "삼성전자") == [stocks[0], extra]


@pytest.mark.parametrize(
    ("query", "expected_names"),
    [
        ("삼", ["삼성전자", "삼성SDI"]),
        ("0059", ["삼성전자"]),
        ("전자", ["삼성전자", "LG전자"]),
        ("  삼성  ", ["삼성전자", "삼성SDI"]),
        ("없는종목", []),
        ("", []),
        ("   ", []),
    ],
)
def test_search_query_cases(app_modules, stocks, query, expected_names):
    result = app_modules["search"].search_stocks(stocks, query)
    assert [stock["name"] for stock in result] == expected_names


def test_search_orders_match_categories_and_applies_limit(app_modules):
    stocks = [
        {"name": "삼성바이오로직스", "code": "111111", "market": "KOSPI"},
        {"name": "전자삼성", "code": "005900", "market": "KOSPI"},
        {"name": "삼성", "code": "222222", "market": "KOSPI"},
        {"name": "삼성전자", "code": "333333", "market": "KOSPI"},
    ]
    result = app_modules["search"].search_stocks(stocks, "삼성", limit=3)
    assert [stock["name"] for stock in result] == ["삼성", "삼성바이오로직스", "삼성전자"]


@pytest.mark.parametrize("limit", [0, -1])
def test_search_nonpositive_limit_returns_empty(app_modules, stocks, limit):
    assert app_modules["search"].search_stocks(stocks, "삼", limit) == []


def test_search_caps_results_at_ten(app_modules):
    stocks = [
        {"name": f"종목{i}", "code": f"{i:06}", "market": "KOSPI"}
        for i in range(15)
    ]
    assert len(app_modules["search"].search_stocks(stocks, "종목")) == 10


def test_get_stocks_fetches_all_markets_and_normalizes(app_modules, monkeypatch, tmp_path):
    cache = app_modules["stock_cache"]
    monkeypatch.setattr(cache, "_CACHE_PATH", tmp_path / "stocks.csv")
    responses = [Mock(content=b"xls") for _ in range(3)]
    for response in responses:
        response.raise_for_status = Mock()
    monkeypatch.setattr(sys.modules["requests"], "get", Mock(side_effect=responses))
    listings = iter([
        pd.DataFrame([{"회사명": " 삼성전자 ", "종목코드": "5930"}]),
        pd.DataFrame([{"회사명": "카카오", "종목코드": "035720"}]),
        pd.DataFrame([{"회사명": "코넥스", "종목코드": "1234"}]),
    ])
    monkeypatch.setattr(cache.pd, "read_html", lambda *args, **kwargs: [next(listings)])

    stocks = cache.get_stocks()

    assert stocks == [
        {"code": "005930", "name": "삼성전자", "market": "KOSPI"},
        {"code": "035720", "name": "카카오", "market": "KOSDAQ"},
        {"code": "001234", "name": "코넥스", "market": "KONEX"},
    ]
    assert len(responses) == 3
    assert cache.get_stocks()[0]["code"] == "005930"


def test_fetch_market_parses_kind_euc_kr_html(app_modules, monkeypatch):
    cache = app_modules["stock_cache"]
    response = Mock(
        content=(
            "<table><tr><th>회사명</th><th>시장구분</th><th>종목코드</th></tr>"
            "<tr><td>테스트회사</td><td>유가</td><td>0220W0</td></tr></table>"
        ).encode("euc-kr")
    )
    response.raise_for_status = Mock()
    request = Mock(return_value=response)
    monkeypatch.setattr(sys.modules["requests"], "get", request)

    result = cache._fetch_market("stockMkt", "KOSPI")

    assert result.to_dict("records") == [
        {"회사명": "테스트회사", "시장구분": "KOSPI", "종목코드": "0220W0"}
    ]
    request.assert_called_once_with(
        cache._KIND_URL,
        params={"method": "download", "marketType": "stockMkt"},
        timeout=30,
    )
    response.raise_for_status.assert_called_once_with()


@pytest.mark.skipif(
    os.environ.get("KRX_KIND_LIVE_TEST") != "1",
    reason="Set KRX_KIND_LIVE_TEST=1 to run the live KIND integration test",
)
def test_live_kind_fetch_and_cache(app_modules, monkeypatch, tmp_path):
    cache = app_modules["stock_cache"]
    cache_path = tmp_path / "stocks.csv"
    monkeypatch.setattr(cache, "_CACHE_PATH", cache_path)
    live_get = Mock(wraps=real_requests.get)
    monkeypatch.setattr(cache, "requests", types.SimpleNamespace(get=live_get))

    stocks = cache.get_stocks(refresh=True)

    assert stocks
    assert {stock["market"] for stock in stocks} == {"KOSPI", "KOSDAQ", "KONEX"}
    assert all(len(stock["code"]) == 6 for stock in stocks)
    assert cache_path.is_file()
    assert list(pd.read_csv(cache_path, dtype={"종목코드": str}).columns) == [
        "회사명", "시장구분", "종목코드"
    ]

    assert cache.get_stocks() == stocks
    assert live_get.call_count == 3


def test_refresh_failure_does_not_replace_cache(app_modules, monkeypatch, tmp_path):
    cache = app_modules["stock_cache"]
    cache_path = tmp_path / "stocks.csv"
    cache_path.write_text("회사명,시장구분,종목코드\n기존,KOSPI,000001\n", encoding="utf-8")
    monkeypatch.setattr(cache, "_CACHE_PATH", cache_path)
    monkeypatch.setattr(sys.modules["requests"], "get", Mock(side_effect=RuntimeError("offline")))

    with pytest.raises(RuntimeError, match="offline"):
        cache.get_stocks(refresh=True)
    assert "기존" in cache_path.read_text(encoding="utf-8")


def test_completer_candidates_include_stock_details(app_modules, stocks):
    completer = app_modules["completer"].StockCompleter(stocks)
    candidates = list(completer.get_completions(types.SimpleNamespace(text_before_cursor="삼"), None))
    assert [item.text for item in candidates] == ["삼성전자", "삼성SDI"]
    assert candidates[0].start_position == -1
    assert candidates[0].display == "삼성전자  005930  KOSPI"


def test_completer_returns_no_candidates_for_no_match(app_modules, stocks):
    completer = app_modules["completer"].StockCompleter(stocks)
    assert list(completer.get_completions(types.SimpleNamespace(text_before_cursor="xyz"), None)) == []


@pytest.mark.parametrize("command", ["exit", "quit", "QUIT"])
def test_main_stops_on_exit_commands(app_modules, monkeypatch, capsys, command):
    main_module = app_modules["main"]
    monkeypatch.setattr(main_module, "get_stocks", lambda: [])
    session = Mock()
    session.prompt.return_value = command
    monkeypatch.setattr(main_module, "PromptSession", Mock(return_value=session))

    main_module.main()

    assert session.prompt.call_count == 1
    assert "종목 0개" in capsys.readouterr().out


def test_main_prints_search_results_and_no_match(app_modules, monkeypatch, capsys):
    main_module = app_modules["main"]
    stock_list = [{"name": "삼성전자", "code": "005930", "market": "KOSPI"}]
    monkeypatch.setattr(main_module, "get_stocks", lambda: stock_list)
    session = Mock()
    session.prompt.side_effect = ["삼성", "없는종목", "exit"]
    monkeypatch.setattr(main_module, "PromptSession", Mock(return_value=session))

    main_module.main()

    output = capsys.readouterr().out
    assert "삼성전자" in output and "005930" in output and "KOSPI" in output
    assert "검색 결과가 없습니다." in output


@pytest.mark.parametrize("exception", [KeyboardInterrupt, EOFError])
def test_main_exits_on_terminal_interrupt(app_modules, monkeypatch, capsys, exception):
    main_module = app_modules["main"]
    monkeypatch.setattr(main_module, "get_stocks", lambda: [])
    session = Mock()
    session.prompt.side_effect = exception
    monkeypatch.setattr(main_module, "PromptSession", Mock(return_value=session))

    main_module.main()

    assert "종목 0개" in capsys.readouterr().out


def test_main_reports_stock_loading_error(app_modules, monkeypatch, capsys):
    main_module = app_modules["main"]
    monkeypatch.setattr(
        main_module, "get_stocks", Mock(side_effect=RuntimeError("offline"))
    )
    session_factory = Mock()
    monkeypatch.setattr(main_module, "PromptSession", session_factory)

    main_module.main()

    assert "종목 목록을 불러오지 못했습니다: offline" in capsys.readouterr().out
    session_factory.assert_not_called()
