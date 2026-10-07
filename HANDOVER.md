# 개발 인수인계 문서

## 프로젝트 개요

Python으로 구현한 한국 증권시장 종목 검색 CLI입니다. 프로그램 시작 시 KRX KIND 종목 목록을 로컬 CSV 캐시에서 가져와 메모리에 보관하고, `prompt_toolkit` 자동완성과 검색 결과 출력 기능을 제공합니다.

기본 설계 및 구현 방향은 [DESIGN.md](DESIGN.md)를 참고하세요. 현재 구현은 종목 목록 로딩, 종목명·코드 검색, CLI 자동완성까지 포함합니다.

## 현재 디렉터리 구성

```text
.
├── main.py             # CLI 진입점 및 입력/출력 처리
├── stock_cache.py      # KIND 데이터 조회 및 24시간 CSV 캐시
├── search.py           # 메모리 내 종목 검색
├── completer.py        # prompt_toolkit 자동완성 연결
├── requirements.txt    # 애플리케이션 의존성
├── tests/
│   └── test_app.py      # 검색, 데이터 로딩, 자동완성, CLI 테스트
├── DESIGN.md            # 설계 문서
└── HANDOVER.md          # 이 문서
```

## 실행 방법

Python 환경에서 프로젝트 루트 기준으로 의존성을 설치하고 실행합니다.

```bash
python -m pip install -r requirements.txt
python main.py
```

입력 예시:

```text
KRX> 삼성
KRX> 0059
```

입력 중 자동완성 후보를 확인할 수 있습니다. 입력 후 Enter를 누르면 검색 결과(최대 10개)가 출력됩니다. `exit`, `quit`, `Ctrl+C`, `Ctrl+D`로 종료합니다. 캐시가 없거나 24시간이 지나면 KIND에서 갱신하므로 이때 네트워크 연결이 필요합니다.

## 주요 동작

### 데이터 로딩

`stock_cache.get_stocks()`가 로컬 캐시를 반환하거나 KIND에서 KOSPI, KOSDAQ, KONEX 목록을 가져와 캐시를 갱신합니다. 반환 항목은 다음 형태입니다.

```python
{"code": "005930", "name": "삼성전자", "market": "KOSPI"}
```

캐시 경로는 `data/stocks.csv`, 유효기간은 24시간입니다. 코드는 문자열로 유지하고 6자리로 보정합니다. KIND 응답은 EUC-KR Excel 호환 HTML 테이블입니다. 강제 갱신은 `get_stocks(refresh=True)`로 수행하며, 갱신 요청 실패 시 기존 CSV를 교체하지 않습니다. 로딩 오류는 `main()`에서 잡아 사용자 메시지로 출력합니다.

### 검색

`search.search_stocks(stocks, query, limit=10)`은 공백을 제거하고 소문자로 정규화한 검색어를 사용합니다. 우선순위는 아래와 같습니다.

1. 종목명 정확 일치
2. 종목명 앞부분 일치
3. 종목코드 앞부분 일치
4. 종목명 포함

각 분류 안에서는 입력 종목 목록의 순서를 유지하며, 전체 결과를 `limit`개로 자릅니다. 빈 검색어, 0 또는 음수 제한은 빈 목록을 반환합니다.

### 자동완성 및 CLI

`completer.StockCompleter`가 입력 커서 앞의 텍스트를 검색 함수에 전달합니다. 자동완성 후보에는 종목명, 코드, 시장이 표시됩니다. `main.py`도 같은 검색 함수를 사용해 Enter 이후 결과를 출력합니다.

## 테스트 및 확인

테스트 실행:

```bash
python -m pytest -q
```

현재 테스트는 검색 우선순위·결과 제한, KIND EUC-KR HTML 응답 파싱·캐시 동작, 자동완성 후보, CLI 출력·종료 동작을 확인합니다. 기본 테스트는 네트워크 없이 실행됩니다. 실제 KIND 조회 통합 테스트는 다음처럼 별도로 실행합니다.

```bash
KRX_KIND_LIVE_TEST=1 python -m pytest -q tests/test_app.py::test_live_kind_fetch_and_cache
```

마지막 확인 결과는 현재 테스트 실행 결과를 기준으로 갱신합니다.

## 알려진 범위와 후속 작업

- 최근 검색 기록, SQLite 저장, 별칭 검색, 초성 검색은 아직 구현하지 않았습니다. 필요성이 확인된 경우에만 추가하는 것이 설계 원칙입니다.
- 검색은 매 입력마다 메모리의 종목 목록을 순회합니다. 현재 예상 데이터 규모에는 별도 인덱스가 필요하지 않습니다.
- 현재 `requirements.txt`는 패키지 버전 범위를 고정하지 않았습니다. 배포 환경에서 재현성이 필요해지면 지원 Python 버전과 함께 버전을 검토·고정하세요.
- `stock_cache.py`는 KIND Excel 호환 HTML의 회사명 및 종목코드 열을 읽습니다. 제공 데이터 스키마가 바뀌면 로딩과 관련 테스트를 함께 수정하세요.
- 저장소에는 현재 별도의 패키지/프로젝트 설정이나 배포 스크립트가 없습니다. 실행 및 테스트는 프로젝트 루트에서 수행합니다.

## 변경 시 주의사항

- 핵심 검색 동작은 `search_stocks()` 한 곳에서 유지하고, 자동완성과 Enter 검색이 같은 함수를 사용하도록 하세요.
- 종목 데이터는 `get_stocks()` 인터페이스를 통해 로드하고 검색 중에는 외부 요청을 하지 않도록 유지하세요.
- 새 기능은 우선 설계 문서의 단순성 원칙과 기존 테스트를 고려하세요.
- `DESIGN.md`의 새 버전을 작성할 때는 기존 문서를 해당 파일에 명시된 규칙에 따라 `backup_md` 폴더에 백업하세요.
