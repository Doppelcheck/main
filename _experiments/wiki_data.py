import wikipedia


def main() -> None:
    languages = wikipedia.languages()

    wikipedia.set_lang("en")

    query = "gaza israel hamas"

    summary = wikipedia.summary(query, auto_suggest=True)

    results, suggestion = wikipedia.search(query, results=5, suggestion=True)
    print(summary)


if __name__ == "__main__":
    main()
