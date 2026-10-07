"""prompt_toolkit completion for stock names and codes."""

from prompt_toolkit.completion import Completer, Completion

from search import search_stocks


class StockCompleter(Completer):
    def __init__(self, stocks):
        self.stocks = stocks

    def get_completions(self, document, complete_event):
        query = document.text_before_cursor
        for stock in search_stocks(self.stocks, query, limit=10):
            yield Completion(
                stock["name"],
                start_position=-len(query),
                display=f'{stock["name"]}  {stock["code"]}  {stock["market"]}',
            )
