import dataclasses
from typing import Callable

from pydantic import BaseModel


@dataclasses.dataclass(frozen=True)
class ViewCallbacks:
    dummy_callback: Callable[[str], None]


class Source(BaseModel):
    url: str
    text: str | None = None
