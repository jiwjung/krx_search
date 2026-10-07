# 한국 증권시장 종목 검색 CLI 설계

## 목적과 구조

Python CLI에서 국내 상장 종목을 검색하고 자동완성한다. 프로그램 시작 시 종목 데이터를 메모리에 로드한 뒤, 입력별 검색은 메모리에서만 수행한다.

```text
main.py → stock_cache.get_stocks() → DataFrame records → 검색/자동완성
```

주요 모듈은 `main.py`(CLI), `stock_cache.py`(KIND 조회 및 CSV 캐시), `search.py`(검색), `completer.py`(자동완성)이다. 검색 중 외부 요청은 하지 않는다.

## 종목 데이터 로딩과 캐시

외부 공개 인터페이스는 `stock_cache.py`의 `get_stocks(refresh=False)` 하나다. 반환값은 다음 필드를 가진 딕셔너리 목록이다.

```python
{"code": "005930", "name": "삼성전자", "market": "KOSPI"}
```

`get_stocks()`는 `data/stocks.csv`를 사용하며 캐시가 없거나 마지막 수정 후 24시간 이상 지났으면 KIND에서 KOSPI(`stockMkt`), KOSDAQ(`kosdaqMkt`), KONEX(`konexMkt`) 목록을 다시 가져온다. `refresh=True`는 캐시 유효기간과 관계없이 강제 갱신한다.

캐시 CSV 컬럼은 `회사명,시장구분,종목코드`이며 종목코드는 문자열로 보존하고 6자리로 정규화한다. 시장 구분은 KIND 응답의 시장 필드 대신 요청한 시장으로 지정한다. 이름 공백을 제거하고 종목코드 기준 중복 제거 후 회사명으로 정렬한다.

갱신은 전체 시장 데이터를 성공적으로 정규화한 뒤 같은 디렉터리의 임시 CSV에 기록하고 원자적으로 교체한다. 요청 또는 저장 실패 시 기존 캐시는 보존한다. KIND는 Excel 호환 HTML 테이블을 EUC-KR로 응답하므로 pandas와 lxml로 읽으며, requests로 조회한다.

## 검색 및 CLI

`search_stocks(stocks, query, limit=10)`은 검색어를 trim/lower 처리하고 다음 순서로 결과를 구성한다.

1. 종목명 정확 일치
2. 종목명 앞부분 일치
3. 종목코드 앞부분 일치
4. 종목명 포함

결과는 `limit`개까지 반환한다. `StockCompleter`와 Enter 이후 출력은 같은 검색 함수를 사용한다. CLI 종료 입력은 `exit`, `quit`이며 Ctrl+C와 Ctrl+D도 종료한다.

## 실행 및 확인

```bash
python -m pip install -r requirements.txt
python main.py
python -m pytest -q
```

최근 검색, 별칭, 초성 검색은 필요성이 확인될 때 추가한다. 검색 규모가 현재와 같은 수천 종목 수준인 동안 별도 인덱스나 검색 서비스를 도입하지 않는다.
