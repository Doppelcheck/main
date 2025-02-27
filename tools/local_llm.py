import datetime
from typing import Generator, AsyncGenerator, Mapping, AsyncIterator

import ollama


async def search_query_wikipedia_ollama(claim: str, language: str | None = None) -> AsyncGenerator[str, None]:
    model = "tulu3"

    language = "the claim's language" or language

    ollama.pull(model)
    prompt = (
        f"```claim\n"
        f"{claim}\n"
        f"```\n"
        f"\n"
        f"Generate a very simple Wikipedia query (two words max.) in {language} for articles that might cover the claim above. Respond "
        f"with the query only: no disclaimer, introduction, or conclusion.\n"
    )

    host = None
    client = ollama.AsyncClient(host=host)

    stream: AsyncIterator[Mapping[str, any]] = await client.chat(
        model=model,
        messages=[
            {'role': 'system', 'content': "You are an expert at generating search queries to find relevant information."},
            {'role': 'user', 'content': prompt},
            # {"role": "assistant", "content": "This is a search query for the text:"},
        ],
        stream=True
    )

    async for response in stream:
        message = response["message"]
        content = message["content"]
        yield content


async def search_query_google_ollama(text: str, language: str | None = None) -> AsyncGenerator[str, None]:
    model = "tulu3"

    language = "the text's language" or language

    date_string = datetime.datetime.now().strftime("%B %d, %Y")
    ollama.pull(model)
    prompt = (
        f"```text\n"
        f"{text}\n"
        f"```\n"
        f"\n"
        f"For the provided text, generate a search query that would return the most relevant information on the topic. "
        f"The query should be concise and in {language}. Respond with the query only: no disclaimer, introduction, or "
        f"conclusion.\n"
        f"\n"
    )

    host = None
    client = ollama.AsyncClient(host=host)

    stream: AsyncIterator[Mapping[str, any]] = await client.chat(
        model=model,
        messages=[
            {'role': 'system', 'content': "You are an expert at generating search queries to find relevant information."},
            {'role': 'user', 'content': prompt},
            # {"role": "assistant", "content": "This is a search query for the text:"},
        ],
        stream=True
    )

    async for response in stream:
        message = response["message"]
        content = message["content"]
        yield content


async def summarize_ollama(text: str, context: str | None = None, language: str | None = None) -> AsyncGenerator[str, None]:
    model= "tulu3"

    language = "the text's language" or language
    context_snippet = (
        f"```\n"
        f"{context}\n"
        f"```\n"
        f"\n"
    ) if context else ""

    context_instruction = (
        "Consider the provided context in your summary but summarize only the extracted text."
    ) if context else ""

    ollama.pull(model)
    prompt = (
        f"{context_snippet}"
        f"```text\n"
        f"{text}\n"
        f"```\n"
        f"\n"
        f"Extract the main claim from the text above. If time, location, and people are available, make sure to "
        f"mention them by converting any and all relative references to their absolute, explicitly, and specific "
        f"counterparts.{context_instruction} Respond in {language} with one single sentence only: no disclaimer, "
        f"introduction, or conclusion.\n"
        "\n"
    )

    host=None
    client = ollama.AsyncClient(host=host)

    stream: AsyncIterator[Mapping[str, any]] = await client.chat(
        model=model,
        messages=[
            {'role': 'system', 'content': "You are an expert at summarizing texts, focusing on key information and facts."},
            {'role': 'user', 'content': prompt},
            # {"role": "assistant", "content": "This is a short summary of the text:"},
        ],
        stream=True
    )
    async for response in stream:
        message = response["message"]
        content = message["content"]
        yield content


def _summarize_ollama(text: str, language: str | None = None) -> Generator[str, None, None]:
    model = "gemma2"
    model = "phi3.5"
    model = "nuextract"
    model = "llama3.2"
    model = "smollm"
    model = "vanilj/Phi-4"
    model = "falcon3"
    model= "dolphin3"
    model= "smallthinker"
    model = "qwen2.5"

    model = "deepseek-r1:8b"
    model = "llama3.2:3b-instruct-q8_0"
    model= "tulu3"

    language = "the text's language" or language

    date_string = datetime.datetime.now().strftime("%B %d, %Y")
    ollama.pull(model)
    prompt = (
        "```text\n"
        "{chunk}\n"
        "```\n"
        "\n"
        "From the provided text, extract only the most important empiric fact in self-contained telegraphic style. "
        "Follow these rules strictly:\n"
        "1. Start the fact directly with the subject/topic\n"
        "2. Write in telegraphic style but ensure the statement is self-contained:\n"
        "   - Remove all connector words\n"
        "   - Remove introductory phrases\n"
        "   - Remove modal particles\n"
        "   - Remove auxiliary constructions\n"
        "   - Keep core subject-verb-object structure\n"
        "   - Include essential context within the statement (who said it, who was involved, when, and on what "
        "occasion)\n"
        "3. Ignore:\n"
        "   - Opinions\n"
        "   - Feelings\n"
        "   - Judgments\n"
        "   - Predictions\n"
        "   - Exclamations\n"
        "   - General statements\n"
        "4. Replace deictic expressions / deixis (pronouns, \"here\", \"now\", etc.) with their proper names\n"
        "5. Always use full names, locations, dates, times, and object references independent from the perspective of "
        "the text or its author (today is {today})\n"
        "6. Answer in {language} only.\n"
        "\n"
    #)
    #(
        "Example:\n"
        "```text\n"
        "Die gestrige Pressekonferenz von Quantum Dynamics AG im Konferenzraum Ost des Münchner Hauptsitzes brachte "
        "mehrere bedeutende Neuigkeiten: CEO Dr. Sarah Weber, die vorletzte Woche vom Handelsblatt zur \"Managerin" 
        "des Jahres\" gewählt wurde, präsentierte um 10:30 Uhr eine strategische Partnerschaft mit dem japanischen "
        "Technologiekonzern Tokyo Electronics. Während die Aktie hier an der Frankfurter Börse daraufhin um 12% stieg, "
        "verkündete der anwesende Forschungsleiter Prof. Zhang, der sein 30-köpfiges Team seit März vom MIT-Campus aus "
        "leitet, den erfolgreichen Abschluss der ersten Testphase des Quantenprozessors QX-1000. Das mit 25 Millionen "
        "Euro vom Bundesforschungsministerium geförderte Projekt wird meiner Einschätzung nach die Computerindustrie "
        "revolutionieren und soll nächsten Monat auf der CeBIT vorgestellt werden.\n"
        "```\n"
        "\n"
        "```output\n"
        "Quantum Dynamics AG Vorstandsvorsitzende Dr. Sarah Weber verkündete strategische Partnerschaft mit Tokyo "
        "Electronics bei Münchner Hauptsitz-Pressekonferenz am 7. Januar 2025 10:30 Uhr.\n"
        "```\n"
        "\n"
        "IMPORTANT! Use the example text and output only as a reference. Do not copy, paraphrase, or summarize anything "
        "from the example!\n"
        "\n"
    )
    stream = ollama.chat(
        model=model,
        messages=[
            {'role': 'system', 'content': "Concisely summarize the main points of the input text, focusing on key information and facts."},
            {'role': 'user', 'content': prompt.format(chunk=text, today=date_string, language=language)},
            # {"role": "assistant", "content": "This is a short summary of the text:"},
        ],
        stream=True
    )
    yield from (response['message']['content'] for response in stream)
