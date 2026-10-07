"""Interactive KRX stock search CLI."""

from prompt_toolkit import PromptSession

from completer import StockCompleter
from search import search_stocks
from stock_cache import get_stocks


def main():
    try:
        stocks = get_stocks()
    except Exception as error:
        print(f"종목 목록을 불러오지 못했습니다: {error}")
        return

    print(f"한국 상장 종목 {len(stocks)}개를 불러왔습니다. (종료: exit 또는 quit)")
    session = PromptSession(
        completer=StockCompleter(stocks),
        complete_while_typing=True,
    )

    while True:
        try:
            query = session.prompt("KRX> ").strip()
            if query.lower() in ("exit", "quit"):
                break

            results = search_stocks(stocks, query)
            if not results:
                print("검색 결과가 없습니다.")
                continue

            for stock in results:
                print(f'{stock["name"]:<16} {stock["code"]}  {stock["market"]}')
        except (KeyboardInterrupt, EOFError):
            break


if __name__ == "__main__":
    main()
