import dataclasses
from typing import Callable

from pydantic import BaseModel

from src.agents.extraction import AgentExtraction


@dataclasses.dataclass(frozen=True)
class ViewCallbacks:
    dummy_callback: Callable[[str], None]
    get_extractor_agent: Callable[[], AgentExtraction]


class Source(BaseModel):
    url: str
    html: str
    selected_text: str | None = None

