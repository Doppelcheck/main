import dataclasses

from src.agents.retrieval import Document
from src.tools.misc import extract_code_block
from src.tools.prompt_openai import PromptOpenAI


@dataclasses.dataclass(frozen=True)
class Match:
    claim: str
    source: str
    rating: int
    explanation: str


class AgentComparison:
    def __init__(self, comparison_config: dict[str, any], openai_config: dict[str, any]) -> None:
        self.agent_extraction = PromptOpenAI(openai_config)
        self._max_text_length = comparison_config["max_text_length"]
        _target_language = comparison_config.get("target_language", "")

        if len(_target_language) < 1:
            _language_instruction = "in the language of the claim"
        else:
            _language_instruction = f"in {_target_language}"

        self.prompt = (
            f"```claim\n"
            f"{{claim}}\n"
            f"```\n"
            f"\n"
            f"```text\n"
            f"{{text}}\n"
            f"```\n"
            f"\n"
            f"Carefully read the claim and the text provided. Your task is to assess how well the text matches the "
            f"claim and assign a score based on the following scale:\n"
            f"  +2: The text strongly supports the claim\n"
            f"  +1: The text generally supports the claim, with some limitations or minor contradictions\n"
            f"   0: The text neither clearly supports nor contradicts the claim, or it's unclear\n"
            f"  -1: The text contradicts the claim but not completely\n"
            f"  -2: The text is in strong opposition to the claim\n"
            f"Also provide a brief explanation for your rating. Respond {_language_instruction} and according to the "
            f"following pattern.\n"
            f"```rating\n"
            f"+1\n"
            f"<explanation>\n"
            f"```\n"
            f"Answer with a triple single quote fenced code block that starts with \"```rating\"."
        )

    async def compare(self, claim: str, document: Document) -> Match:
        text = document.content
        claim = await self.agent_extraction.summarize(claim, max_len_summary=1_000)
        text = await self.agent_extraction.summarize(text, max_len_summary=self._max_text_length)
        prompt = self.prompt.format(claim=claim.strip(), text=text.strip())
        reply = await self.agent_extraction.reply_to_prompt(prompt)
        response = extract_code_block(reply, "rating")
        rating_str, text_passage = response.split("\n", 1)
        return Match(claim, document.source, int(rating_str), text_passage.strip())
