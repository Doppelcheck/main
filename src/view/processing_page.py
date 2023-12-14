import textwrap

import newspaper
import num2words
from nicegui import ui, Client

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
        self._target_language: str | None = "German"

        self._prompt_extraction = (
            f"```text"
            f"{{text}}\n"
            f"```\n"
            f"\n"
            f"Identify and extract the top {num2words.num2words(self._number_of_statements)} statements from the "
            f"above text, focusing exclusively on information presented as factual. Exclude examples, questions, "
            f"opinions, descriptions of personal feelings, prose, and similar non-factual content.\n"
            f"\n"
            f"Clearly reference the line numbers corresponding to each extracted statement. Ensure that the statements "
            f"are brief, clear, and directly convey the essential information. Use only up to 20 words for each "
            f"statement.\n"
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
            article = newspaper.Article(self.source.url, fetch_images=False)
            article.download()
            article.parse()
            language = self.callbacks.detect_language(article.text)
            article.config.set_language(language)
            article.nlp()

        loading.delete()

        ui.label("Title:")
        ui.label(article.title)

        ui.label("Authors:")
        ui.label(", ".join(article.authors))

        ui.label("Language:")
        ui.label(article.meta_lang)
        ui.label(article.config.get_language())

        ui.label("Publish date:")
        ui.label(article.publish_date)

        ui.label("Tags:")
        ui.label(", ".join(article.tags))

        ui.label("Keywords:")
        ui.label(", ".join(article.keywords))

        ui.label("Meta keywords:")
        ui.label(", ".join(article.meta_keywords))

        ui.label("Summary:")
        ui.label(article.summary)

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
