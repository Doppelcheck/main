import re
import textwrap

import lingua
import newspaper
import nltk
import num2words
from loguru import logger

from experiments.navi_str import XpathSlice, index_html_new
from src.tools.misc import extract_code_block
from src.tools.prompt_openai import PromptOpenAI


class LLMFormatException(Exception):
    pass


class AgentExtraction:
    @staticmethod
    def split_lines(line: str) -> tuple[int, int, str]:
        pattern = r'(\d+)-(\d+)\s*:? ?(.*?)(?:\n)?$'

        # Applying the regular expression to each line
        match = re.match(pattern, line)
        if match:
            # Extracting the individual numbers and the text
            from_number = int(match.group(1))
            to_number = int(match.group(2))
            text_part = match.group(3).strip()
            return from_number, to_number, text_part

        raise LLMFormatException(f"Could not parse line: {line}")

    def __init__(self, config: dict[str, any]) -> None:
        nltk.download('punkt')
        detector = lingua.LanguageDetectorBuilder.from_all_languages()
        self.detector_built = detector.build()

        self.agent_extraction = PromptOpenAI(config)

        self._number_of_statements = 3
        self._target_language: str | None = "German"

        self._prompt_extraction = (
            f"```text\n"
            f"{{text}}\n"
            f"```\n"
            f"\n"
            f"Identify and extract the top {num2words.num2words(self._number_of_statements)} assertions from the above "
            f"text. Exclude examples, questions, opinions, descriptions of personal feelings, prose, and similar "
            f"non-factual content.\n"
            f"\n"
            f"Clearly reference the range of line numbers corresponding to each extracted assertion. Ensure that each "
            f"extracted assertion is brief, clear, and directly conveys the essential statement. Use only up to 20 "
            f"words for each assertion.\n"
            f"\n"
            f"Respond according to the following pattern:\n"
            f"```statements\n"
            f"<line start>-<line end>: <statement a>\n"
            f"012-015: <statement b>\n"
            f"036-036: <statement c>\n"
            f"[...]\n"
            f"```\n"
            f"\n"
            f"Answer in one triple single quote fenced code block with the keyword `statements`."
        )

        if self._target_language is not None:
            self._prompt_extraction += f" Translate the statements into {self._target_language}."

    def _detect_language(self, text: str) -> str:
        language = self.detector_built.detect_language_of(text)
        if language is None:
            return "en"

        return language.iso_code_639_1.name.lower()

    async def parse_url(self, url: str) -> newspaper.Article:
        article = newspaper.Article(url, fetch_images=False)
        article.download()
        article.parse()
        language = self._detect_language(article.text)
        article.config.set_language(language)
        article.nlp()

        """
        ui.label("Title:")
        ui.label(article.title)

        ui.label("Text:")
        ui.label(article.text)

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
        """
        return article

    async def extract_statements_from_html(self, html_text: str) -> list[tuple[list[XpathSlice], str]]:
        indexes = index_html_new(html_text)
        lines = list()
        indices_dict = dict[int, XpathSlice]()
        for each_xslice in indexes:
            each_line = f"{each_xslice.order:03d} {each_xslice.get_text()}"
            indices_dict[each_xslice.order] = each_xslice
            lines.append(each_line)

        numbered = "\n".join(lines)
        prompt = self._prompt_extraction.format(text=numbered)
        response = await self.agent_extraction.reply_to_prompt(prompt)

        lines = extract_code_block(response, "statements")
        results = list()
        for each_line in lines.splitlines():
            try:
                from_number, to_number, each_statement = AgentExtraction.split_lines(each_line)
                each_indices = [indices_dict[each_index] for each_index in range(from_number, to_number + 1)]
                results.append((each_indices, each_statement))

            except LLMFormatException as e:
                logger.error(e)

        return results

    async def extract_statements_from_text(self, text: str) -> list[tuple[str, str]]:
        wrapped = textwrap.wrap(text, width=50)

        numbered = "\n".join(f"{i + 1:02d} {line}" for i, line in enumerate(wrapped))
        prompt = self._prompt_extraction.format(text=numbered)
        response = await self.agent_extraction.reply_to_prompt(prompt)

        lines = extract_code_block(response, "statements")
        results = list()
        for each_line in lines.splitlines():
            print(each_line)
            try:
                from_number, to_number, each_statement = AgentExtraction.split_lines(each_line)
                source = " ".join(_numbered_line.strip() for _numbered_line in wrapped[from_number - 1:to_number])
                results.append((each_statement, source))

            except LLMFormatException as e:
                logger.error(e)

        return results
