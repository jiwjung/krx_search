# KRX 종목 검색

한국 증권시장 상장종목을 이름이나 종목코드로 검색하는 Python CLI입니다. 입력 중 자동완성을 지원하며, 종목 목록은 KRX KIND에서 가져옵니다.

## 설치 및 실행

```bash
python -m pip install -r requirements.txt
python start.py
```

종목 목록을 처음 불러오거나 캐시가 만료(24시간 초과)되면 인터넷 연결이 필요합니다.

## 사용법

`KRX>` 프롬프트에서 종목명 또는 코드 일부를 입력하고 Enter를 누르세요. 예: `삼성`, `0059`. `exit` 또는 `quit`을 입력하면 종료합니다.

## 테스트 코드 실행

```bash
python -m pytest -q
```
