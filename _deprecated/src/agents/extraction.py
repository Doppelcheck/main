import dataclasses
import re
import textwrap

import lingua
import newspaper
import nltk
import num2words
from loguru import logger

from experiments.navi_str import XpathSlice
from src.tools.misc import extract_code_block
from src.tools.prompt_openai import PromptOpenAI


Extract = tuple[list[XpathSlice], str]


@dataclasses.dataclass(frozen=True)
class Claim:
    statement: str
    quote: str


@dataclasses.dataclass(frozen=True)
class Essence:
    source: str
    claims: list[str]
    context: newspaper.Article | None = None


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

    def __init__(self, extraction_config: dict[str, any], openai_config: dict[str, any]) -> None:
        nltk.download('punkt')
        detector = lingua.LanguageDetectorBuilder.from_all_languages()
        self.detector_built = detector.build()

        self.agent_extraction = PromptOpenAI(openai_config)

        number_of_statements = extraction_config["number_of_statements"]
        len_claim = extraction_config["approx_words_claim"]
        self._target_language = extraction_config["target_language"]
        self._max_text_length = extraction_config["max_text_length"]

        statement_num_word = f"{number_of_statements:d}" \
            if number_of_statements >= 13 \
            else num2words.num2words(number_of_statements)

        claim_num_word = f"{len_claim:d}" \
            if len_claim >= 13 \
            else num2words.num2words(len_claim)

        self._prompt_extraction = (
            f"```text\n"
            f"{{text}}\n"
            f"```\n"
            f"\n"
            f"Identify and extract the {statement_num_word} key claims from the text in the code block above. Exclude "
            f"all examples, questions, opinions, descriptions of personal feelings, prose, advertisements, and similar "
            f"non-factual content.\n"
            f"\n"
            f"Precisely reference an exclusive range of line numbers with each extracted claim. Provide a brief, "
            f"clear, and direct rephrasing of each key claim to convey its essential statement. Use only up to "
            f"{claim_num_word} words for each claim.\n"
            f"\n"
            f"Respond according to the following pattern:\n"
            f"```key_claims\n"
            f"<line start>-<line end>: <key_claim a>\n"
            f"015-027: <key_claim b>\n"
            f"056-081: <key_claim c>\n"
            f"[...]\n"
            f"```\n"
            f"\n"
            f"Answer in one triple single quote fenced code block with the keyword `key_claims` containing all "
            f"{statement_num_word} key claims."
        )

        if len(self._target_language) < 1:
            self._prompt_extraction += " Respond in the same language as the text."
        else:
            self._prompt_extraction += f" Translate the claims into {self._target_language}."

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

    async def extract_from_slices(self, xslices: list[XpathSlice]) -> list[Extract]:
        lines = list()
        indices_dict = dict[int, XpathSlice]()
        for each_xslice in xslices:
            each_line = f"{each_xslice.order:03d} {each_xslice.get_text()}"
            indices_dict[each_xslice.order] = each_xslice
            lines.append(each_line)

        numbered = "\n".join(lines)

        logger.info(numbered)

        prompt = self._prompt_extraction.format(text=numbered)
        response = await self.agent_extraction.reply_to_prompt(prompt)
        lines = extract_code_block(response, "key_claims")

        logger.info(lines)

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
        text = await self.agent_extraction.summarize(text)
        # todo: pass on summarization warning
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
