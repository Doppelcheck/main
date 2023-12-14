import textwrap

import newspaper
import num2words
from nicegui import ui, Client
import lingua

from src.dataobjects import ViewCallbacks, Source
from src.tools.misc import extract_code_block
from src.tools.prompt_openai import PromptOpenAI
from src.view.content_class import ContentPage


class ProcessingPage(ContentPage):
    def __init__(self, client: Client, callbacks: ViewCallbacks):
        super().__init__(client, callbacks)
        self.source: Source | None = None
        config = callbacks.get_agent_config()
        self.agent_extraction = PromptOpenAI(config)
        self._number_of_statements = 3
        self._target_language: str | None = None

        self._prompt_extraction = (
            f"```text"
            f"{{text}}\n"
            f"```\n"
            f"\n"
            f"Identify and extract the top {num2words.num2words(self._number_of_statements)} statements from the "
            f"above text, focusing exclusively on information presented as factual. Exclude examples, questions, "
            f"descriptions of personal feelings, prose, and similar non-factual content. Clearly reference the line "
            f"numbers corresponding to each extracted statement. Ensure that the statements are brief, clear, and "
            f"directly convey the essential information. Use only up to 10 words for each statement.\n"
            f"\n"
            f"Respond according to the following pattern:\n"
            f"```statements\n"
            f"1. lines 2-5: <statement a>\n"
            f"2. lines 16-23: <statement b>\n"
            f"[...]\n"
            f"```\n"
            f"\n"
            f"Answer in one triple single quote fenced code block with the keyword `statements`."
        )

        if self._target_language is not None:
            self._prompt_extraction += f" Translate the statements into {self._target_language}."

    async def _create_content(self):
        ui.label("Test")
        if self.source is None:
            ui.open("/")

        if self.source.url is None:
            ui.open("/")

        ui.label(f"URL: {self.source.url}")

        with ui.element("div") as loading:
            ui.label("Loading...")
            ui.spinner()
            article = newspaper.Article(self.source.url)
            article.download()
            article.parse()
            detector = lingua.LanguageDetectorBuilder.from_all_languages().build()
            language = detector.detect_language_of(article.text)
            article.config.language = language.iso_code_639_1.name.lower()
            article.nlp()

        loading.delete()

        title = article.title
        ui.label("Title:")
        ui.label(title)

        ui.label("Language:")
        ui.label(article.meta_lang)
        ui.label(article.config.get_language())

        keywords = article.keywords
        ui.label("Keywords:")
        ui.label(", ".join(keywords))

        summary = article.summary
        ui.label("Summary:")
        ui.label(summary)

        text = self.source.text or (article.title + "\n\n" + article.text)

        wrapped = textwrap.wrap(text, width=50)
        numbered = "\n".join(f"{i + 1:02d} {line}" for i, line in enumerate(wrapped))
        content = ui.markdown(numbered)
        content.style(
            "white-space: pre-wrap;"
            "width: 80vw;"
            "align-self: center;"
            "display: flex;"
            "flex-direction: column;"
        )

        # process_button = ui.button("Process")

        with ui.element("div") as loading:
            ui.label("Loading...")
            ui.spinner()
            prompt = self._prompt_extraction.format(text=numbered)
            response = await self.agent_extraction.reply_to_prompt(prompt)

        loading.delete()

        lines = extract_code_block(response, "statements")

        ui.label("Response:")
        for each_statement in lines.splitlines():
            ui.label(each_statement)
