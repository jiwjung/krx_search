# DESIGN.md
***새로운 버전의 md를 생성하는 경우, 기존 파일은 backup_md 폴더에 "기존md파일명_{version}.md" 형식으로 이름을 바꾸어 저장하시오.

# 한국 증권시장 종목 검색 CLI 설계

## 1. 목적

Python 기반 CLI 프로그램에서 한국 증권시장 종목을 빠르고 직관적으로 검색할 수 있도록 자동완성 기능을 제공한다.

사용자는 종목명을 일부만 입력해도 관련 종목 후보를 확인할 수 있어야 하며, 가능한 한 단순한 구조로 구현한다.

예시:

```text
KRX> 삼성
  삼성전자      005930  KOSPI
  삼성SDI       006400  KOSPI
  삼성전기      009150  KOSPI
```

또는 종목코드 입력:

```text
KRX> 0059
  삼성전자      005930  KOSPI
```

---

## 2. 설계 원칙

이 프로그램은 CLI에서 사용하므로 다음 원칙을 우선한다.

1. 로직이 단순해야 한다.
2. 코드 흐름이 직관적이어야 한다.
3. 불필요한 클래스와 계층을 만들지 않는다.
4. 검색 중 외부 API를 호출하지 않는다.
5. 상장 종목 목록은 프로그램 시작 시 메모리에 로딩한다.
6. 입력할 때마다 전체 종목을 간단히 필터링한다.
7. 검색 결과는 최대 5~10개만 표시한다.

한국 상장 종목 수는 일반적인 CLI 검색에서 충분히 작은 규모이므로 초기 구현에서는 Trie, Elasticsearch, 검색 서버 등의 복잡한 구조를 사용하지 않는다.

---

## 3. 사용 기술

```text
Python
prompt_toolkit
FinanceDataReader
```

선택 기능:

```text
SQLite
```

SQLite는 최근 검색 기록을 저장할 필요가 있을 때만 사용한다.

### 역할

| 기술 | 역할 |
|---|---|
| Python | 프로그램 전체 구현 |
| prompt_toolkit | CLI 입력 및 자동완성 |
| FinanceDataReader | 한국 상장 종목 목록 조회 |
| SQLite | 최근 검색 기록 저장 (선택) |

---

## 4. 전체 구조

복잡한 계층을 만들지 않고 다음 정도로만 구성한다.

```text
stock-cli/
│
├── main.py
├── stock_data.py
├── search.py
├── completer.py
└── history.py
```

`history.py`는 최근 검색 기능이 필요하지 않으면 제외할 수 있다.

---

## 5. 프로그램 흐름

```text
프로그램 실행
    ↓
한국 상장 종목 목록 조회
    ↓
메모리에 저장
    ↓
CLI 입력 시작
    ↓
사용자가 문자 입력
    ↓
search_stocks()
    ↓
검색 결과 최대 10개 반환
    ↓
CLI 자동완성 목록 표시
    ↓
사용자가 종목 선택
```

검색 중에는 API를 호출하지 않는다.

---

## 6. 종목 데이터

프로그램 시작 시 필요한 값만 보관한다.

```python
stocks = [
    {
        "code": "005930",
        "name": "삼성전자",
        "market": "KOSPI"
    },
    {
        "code": "000660",
        "name": "SK하이닉스",
        "market": "KOSPI"
    }
]
```

복잡한 ORM이나 Model 클래스는 초기 구현에서는 사용하지 않는다.

필요한 값:

```text
code
name
market
```

---

## 7. 종목 데이터 로딩

`FinanceDataReader`를 사용한다.

```python
import FinanceDataReader as fdr


def load_stocks():
    df = fdr.StockListing("KRX")

    stocks = []

    for _, row in df.iterrows():
        stocks.append({
            "code": row["Code"],
            "name": row["Name"],
            "market": row["Market"],
        })

    return stocks
```

프로그램 시작 시 한 번만 실행한다.

```python
stocks = load_stocks()
```

---

## 8. 검색 로직

검색 로직은 하나의 함수로 최대한 단순하게 유지한다.

우선순위는 다음과 같다.

```text
1. 종목명 정확히 일치
2. 종목명 앞부분 일치
3. 종목코드 앞부분 일치
4. 종목명에 검색어 포함
```

예:

```python
def search_stocks(stocks, query, limit=10):
    if not query:
        return []

    query = query.strip().lower()

    exact = []
    prefix = []
    code_prefix = []
    contains = []

    for stock in stocks:
        name = stock["name"].lower()
        code = stock["code"]

        if name == query:
            exact.append(stock)

        elif name.startswith(query):
            prefix.append(stock)

        elif code.startswith(query):
            code_prefix.append(stock)

        elif query in name:
            contains.append(stock)

    results = exact + prefix + code_prefix + contains

    return results[:limit]
```

별도의 복잡한 점수 계산은 사용하지 않는다.

검색 우선순위를 코드의 순서 자체로 표현한다.

---

## 9. 자동완성

`prompt_toolkit`의 `Completer`를 사용한다.

```python
from prompt_toolkit.completion import Completer, Completion


class StockCompleter(Completer):

    def __init__(self, stocks):
        self.stocks = stocks

    def get_completions(self, document, complete_event):
        query = document.text_before_cursor

        results = search_stocks(
            self.stocks,
            query,
            limit=10
        )

        for stock in results:
            yield Completion(
                stock["name"],
                start_position=-len(query),
                display=f'{stock["name"]}  {stock["code"]}  {stock["market"]}'
            )
```

사용자는 입력하는 동안 후보를 바로 확인한다.

---

## 10. CLI 실행

`main.py`

```python
from prompt_toolkit import PromptSession

from stock_data import load_stocks
from completer import StockCompleter


def main():

    stocks = load_stocks()

    completer = StockCompleter(stocks)

    session = PromptSession(
        completer=completer,
        complete_while_typing=True
    )

    while True:

        try:
            query = session.prompt("KRX> ")

            if query in ("exit", "quit"):
                break

            print(query)

        except (KeyboardInterrupt, EOFError):
            break


if __name__ == "__main__":
    main()
```

---

## 11. 사용자 경험

기본 동작:

```text
KRX> 삼
```

자동완성:

```text
삼성전자      005930  KOSPI
삼성SDI       006400  KOSPI
삼성전기      009150  KOSPI
삼성물산      028260  KOSPI
```

종목코드:

```text
KRX> 0059
```

결과:

```text
삼성전자      005930  KOSPI
```

종목명 일부:

```text
KRX> 전자
```

결과:

```text
삼성전자      005930  KOSPI
LG전자        066570  KOSPI
```

---

## 12. 최근 검색 기능

초기 버전에서는 필수가 아니다.

필요해지면 최근 검색 종목만 간단히 우선 노출한다.

예:

```python
recent_codes = [
    "005930",
    "000660"
]
```

검색 결과를 정렬할 때:

```python
results.sort(
    key=lambda stock:
        stock["code"] not in recent_codes
)
```

이 정도만 사용한다.

복잡한 확률 모델이나 머신러닝은 사용하지 않는다.

---

## 13. 별칭 검색

다음과 같은 검색이 필요하다면 작은 딕셔너리만 사용한다.

```python
ALIASES = {
    "삼전": "005930",
    "하닉": "000660",
    "현차": "005380",
}
```

검색 함수 시작 부분에서 확인한다.

```python
if query in ALIASES:
    code = ALIASES[query]

    return [
        stock
        for stock in stocks
        if stock["code"] == code
    ]
```

별칭 역시 별도의 검색 엔진으로 분리하지 않는다.

---

## 14. 초성 검색

초성 검색은 필수 기능이 아니다.

필요할 경우 이후 추가한다.

예:

```text
ㅅㅅㅈㅈ
→ 삼성전자
```

초기 버전에서는 구현하지 않고 아래 기능을 우선 구현한다.

```text
종목명 prefix
종목코드 prefix
종목명 포함 검색
```

실제 사용 중 필요성이 확인되면 추가한다.

---

## 15. 하지 않을 것

초기 버전에서는 다음 기능을 구현하지 않는다.

```text
Trie
검색 서버
Elasticsearch
Vector DB
LLM 검색
머신러닝 기반 추천
복잡한 점수 계산
복잡한 Repository / Service 계층
과도한 클래스 분리
```

이러한 기능은 현재 CLI 종목검색 규모에서는 오히려 코드 복잡도만 증가시킨다.

---

## 16. 성능

검색 대상 종목 수가 수천 개 수준이라면 다음 반복문으로 충분하다.

```python
for stock in stocks:
```

사용자가 키를 입력할 때마다 실행되더라도 일반적인 CLI 환경에서는 충분히 빠르다.

성능 문제가 실제로 발생하기 전까지 별도의 인덱싱 구조를 추가하지 않는다.

---

## 17. 최종 구조

```text
                  FinanceDataReader
                         │
                         │ 프로그램 시작 시 1회
                         ▼
                   list[dict]
                         │
                         ▼
사용자 입력 ──────── search_stocks()
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
           종목명       종목코드      포함검색
           prefix       prefix
              └──────────┼──────────┘
                         ▼
                    최대 10개
                         │
                         ▼
                  prompt_toolkit
                         │
                         ▼
                  CLI 자동완성
```

---

## 18. 구현 우선순위

### 1단계

```text
FinanceDataReader 종목 목록 로딩
```

### 2단계

```text
종목명 검색
종목코드 검색
```

### 3단계

```text
prompt_toolkit 자동완성
```

### 4단계

필요할 경우:

```text
최근 검색
별칭 검색
초성 검색
```

순서로 추가한다.

---

## 19. 결론

이 프로젝트에서는 검색 기능 자체보다 CLI에서 빠르고 편하게 종목을 찾는 것이 중요하다.

따라서 초기 구현은 다음 세 요소만으로 구성한다.

```text
FinanceDataReader
        +
search_stocks()
        +
prompt_toolkit
```

핵심 검색 함수는 가능한 한 하나로 유지한다.

```text
정확히 일치
→ 이름 prefix
→ 코드 prefix
→ 이름 포함
```

추가 기능은 실제 사용 과정에서 필요성이 확인될 때만 추가한다.

**단순한 구현을 유지하는 것이 이 프로젝트의 가장 중요한 설계 원칙이다.**
