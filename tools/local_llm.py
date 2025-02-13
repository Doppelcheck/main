import datetime
from typing import Generator

import ollama


def summarize_ollama(text: str, language: str | None = None) -> Generator[str, None, None]:
    model= "tulu3"

    language = "the text's language" or language

    date_string = datetime.datetime.now().strftime("%B %d, %Y")
    ollama.pull(model)
    prompt = (
        "```text\n"
        "{chunk}\n"
        "```\n"
        "\n"
        "Summarize the the text above in one concise sentence and in {language}. Respond with the summary only: no "
        "disclaimer, introduction, or conclusion.\n"
        "\n"
    )
    stream = ollama.chat(
        model=model,
        messages=[
            {'role': 'system', 'content': "You are an expert at summarizing texts, focusing on key information and facts."},
            {'role': 'user', 'content': prompt.format(chunk=text, today=date_string, language=language)},
            # {"role": "assistant", "content": "This is a short summary of the text:"},
        ],
        stream=True
    )
    yield from (response['message']['content'] for response in stream)


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
