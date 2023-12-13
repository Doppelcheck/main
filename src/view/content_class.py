from abc import ABC, abstractmethod

from nicegui import Client, ui

from src.dataobjects import ViewCallbacks


class ContentPage(ABC):
    def __init__(self, client: Client, callbacks: ViewCallbacks) -> None:
        self.client = client
        self.callbacks = callbacks

    def _javascript(self) -> str:
        return ""

    @abstractmethod
    async def _create_content(self) -> None:
        raise NotImplementedError()

    async def create_content(self) -> None:
        await self.client.connected()
        await self._create_content()
        js_code = self._javascript()
        _ = ui.run_javascript(js_code)

