import dataclasses
from typing import Callable


@dataclasses.dataclass(frozen=True)
class ViewCallbacks:
    dummy_callback: Callable[[str], None]
