import dataclasses
from typing import Callable

from pydantic import BaseModel


@dataclasses.dataclass(frozen=True)
class ViewCallbacks:
    dummy_callback: Callable[[str], None]
    get_agent_config: Callable[[], dict[str, any]]


class Source(BaseModel):
    url: str
    text: str | None = None

