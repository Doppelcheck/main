import dataclasses
from typing import Callable

from pydantic import BaseModel

from _deprecated.src.agents.comparison import AgentComparison
from _deprecated.src.agents.extraction import AgentExtraction
from _deprecated.src.agents.retrieval import AgentRetrieval


@dataclasses.dataclass(frozen=True)
class ViewCallbacks:
    dummy_callback: Callable[[str], None]
    get_extractor_agent: Callable[[], AgentExtraction]
    get_retrieval_agent: Callable[[], AgentRetrieval]
    get_comparison_agent: Callable[[], AgentComparison]


class Source(BaseModel):
    url: str
    html: str
    selected_text: str | None = None
