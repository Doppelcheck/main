from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, TypeVar, List

from nicegui import ui


@dataclass
class Item:
    title: str


ImplementedItem = TypeVar("ImplementedItem", bound=Item)


@dataclass
class ToDo(Item):
    pass


class DraggableRow(ui.row):
    def __init__(self) -> None:
        super().__init__()
        self.dragged: Optional[DraggableCard] = None

    def add_column(self, name: str, todos: List[ToDo], on_drop: Optional[Callable[[ImplementedItem, str], None]] = None) -> None:
        with DraggableColumn(name, on_drop, row=self) as column:
            for todo in todos:
                DraggableCard(todo, row=self)

    def set_dragged(self, card: DraggableCard | None) -> None:
        self.dragged = card

    def get_dragged(self) -> Optional[DraggableCard]:
        return self.dragged


class DraggableColumn(ui.column):
    def __init__(self, name: str, on_drop: Optional[Callable[[ImplementedItem, str], None]], row: DraggableRow) -> None:
        super().__init__()
        self.row = row
        with self.classes('bg-blue-grey-2 w-60 p-4 rounded shadow-2'):
            ui.label(name).classes('text-bold ml-1')

        self.name = name
        self.on('dragover.prevent', self.highlight)
        self.on('dragleave', self.unhighlight)
        self.on('drop', lambda event: self.move_card(event))
        self.on_drop = on_drop

    def highlight(self) -> None:
        self.classes(remove='bg-blue-grey-2', add='bg-blue-grey-3')

    def unhighlight(self) -> None:
        self.classes(remove='bg-blue-grey-3', add='bg-blue-grey-2')

    def move_card(self, event) -> None:
        dragged = self.row.get_dragged()
        if dragged:
            self.unhighlight()
            dragged.parent_slot.parent.remove(dragged)
            with self:
                DraggableCard(dragged.item, row=self.row)
            if self.on_drop:
                self.on_drop(dragged.item, self.name)
            self.row.set_dragged(None)


class DraggableCard(ui.card):
    def __init__(self, item: Item, row: DraggableRow) -> None:
        super().__init__()
        self.item = item
        self.row = row
        with self.props('draggable').classes('w-full cursor-pointer bg-grey-1'):
            ui.label(item.title)

        self.on('dragstart', self.handle_dragstart)
        self.on('dragover.prevent', self.highlight)
        self.on('dragleave', self.unhighlight)
        self.on('drop', self.unhighlight)

    def handle_dragstart(self) -> None:
        self.row.set_dragged(self)

    def highlight(self) -> None:
        self.classes(add='bg-blue-grey-3')

    def unhighlight(self) -> None:
        self.classes(remove='bg-blue-grey-3')
