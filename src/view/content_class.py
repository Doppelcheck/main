from abc import ABC, abstractmethod

from nicegui import Client

from src.dataobjects import ViewCallbacks


class ContentPage(ABC):
    def __init__(self, client: Client, callbacks: ViewCallbacks) -> None:
        self.client = client
        self.callbacks = callbacks

    @abstractmethod
    async def create_content(self) -> None:
        raise NotImplementedError()
