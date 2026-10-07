"""Simple in-memory stock search."""


def search_stocks(stocks, query, limit=10):
    """Search by exact name, name prefix, code prefix, then name substring."""
    query = query.strip().lower()
    if not query or limit <= 0:
        return []

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

    return (exact + prefix + code_prefix + contains)[:limit]
