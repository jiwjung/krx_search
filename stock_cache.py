"""Fetch and cache listed stocks from KRX KIND."""

from io import StringIO
from pathlib import Path
import tempfile
import time

import pandas as pd
import requests


_CACHE_PATH = Path(__file__).resolve().parent / "data" / "stocks.csv"
_CACHE_TTL_SECONDS = 24 * 60 * 60
_KIND_URL = "https://kind.krx.co.kr/corpgeneral/corpList.do"
_MARKETS = (("stockMkt", "KOSPI"), ("kosdaqMkt", "KOSDAQ"), ("konexMkt", "KONEX"))
_COLUMNS = ["회사명", "시장구분", "종목코드"]


def get_stocks(refresh=False):
    """Return listed stocks, using a 24-hour CSV cache when available."""
    if not refresh and _CACHE_PATH.exists() and not _is_cache_expired():
        return _load_cache()
    return _refresh_cache()


def _fetch_market(market_type, market_name):
    response = requests.get(
        _KIND_URL,
        params={"method": "download", "marketType": market_type},
        timeout=30,
    )
    response.raise_for_status()
    listing = pd.read_html(StringIO(response.content.decode("euc-kr")))[0]
    name_column = "회사명"
    code_column = "종목코드"
    normalized = pd.DataFrame(
        {
            "회사명": listing[name_column].fillna("").astype(str).str.strip(),
            "시장구분": market_name,
            "종목코드": listing[code_column].fillna("").astype(str).str.strip().str.zfill(6),
        }
    )
    return normalized[(normalized["회사명"] != "") & (normalized["종목코드"] != "")]


def _normalize(stocks):
    if not stocks:
        return pd.DataFrame(columns=_COLUMNS)
    result = pd.concat(stocks, ignore_index=True)
    return (
        result[_COLUMNS]
        .drop_duplicates(subset=["종목코드"], keep="first")
        .sort_values("회사명", kind="stable")
        .reset_index(drop=True)
    )


def _refresh_cache():
    stocks = _normalize([_fetch_market(code, name) for code, name in _MARKETS])
    _save_cache(stocks)
    return _to_stock_records(stocks)


def _load_cache():
    cached = pd.read_csv(_CACHE_PATH, dtype={"종목코드": str})
    return _to_stock_records(cached[_COLUMNS])


def _to_stock_records(stocks):
    return [
        {"code": row["종목코드"], "name": row["회사명"], "market": row["시장구분"]}
        for row in stocks.to_dict("records")
    ]


def _save_cache(stocks):
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8-sig", newline="", suffix=".tmp.csv",
            dir=_CACHE_PATH.parent, delete=False
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            stocks.to_csv(temporary_file, index=False)
        temporary_path.replace(_CACHE_PATH)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _is_cache_expired():
    return time.time() - _CACHE_PATH.stat().st_mtime >= _CACHE_TTL_SECONDS
