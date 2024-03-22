from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

from nicegui import ui


@dataclass
class Item:
    title: str


class DropSeparator(ui.element):
    def __init__(self, column: DraggableColumn, index: int) -> None:
        super().__init__(tag="div")
        self.column = column
        self.index = index
        self.classes(add='bg-transparent h-4 w-full')

        with self:
            self.separator = ui.separator().classes('w-full my-2 h-0.5')
            # self.separator = ui.element("div").classes('bg-grey-2 w-full my-2 h-1')

        self.on('dragover.prevent', self.highlight)
        self.on('dragleave', self.unhighlight)
        self.on('drop', self.drop)

    def highlight(self) -> None:
        self.separator.classes(add='bg-white')
        self.column.highlight()

    def unhighlight(self) -> None:
        self.separator.classes(remove='bg-white')
        self.column.unhighlight()

    def drop(self, event) -> None:
        # print(self.column.default_slot.children)
        print(self.index)
        self.unhighlight()


class DraggableCard(ui.card):
    def __init__(self, item: Item, row: DraggableRow) -> None:
        super().__init__()
        self.item = item
        self.row = row
        with self.props('draggable').classes('w-full cursor-pointer bg-grey-1'):
            ui.label(item.title)

        self.on('dragstart', self.handle_dragstart)

    def handle_dragstart(self) -> None:
        self.row.set_dragged(self)

    def highlight(self) -> None:
        self.classes(add='bg-blue-grey-3')

    def unhighlight(self) -> None:
        self.classes(remove='bg-blue-grey-3')


class Element:
    def __init__(self, item: Item, row: DraggableRow, column: DraggableColumn, index: int) -> None:
        self.item = item
        self.row = row
        self.index = index
        if self.index < 1:
            DropSeparator(column, 0)
        DraggableCard(item, row=row)
        DropSeparator(column, index + 1)


class DraggableRow(ui.row):
    def __init__(self) -> None:
        super().__init__()
        self.dragged: Optional[DraggableCard] = None

    def add_column(self, name: str, todos: List[Item]) -> None:
        with DraggableColumn(name, row=self) as column:
            for i, each_todo in enumerate(todos):
                Element(each_todo, self, column, i)

    def set_dragged(self, card: DraggableCard | None) -> None:
        self.dragged = card

    def get_dragged(self) -> Optional[DraggableCard]:
        return self.dragged


class DraggableColumn(ui.column):
    def __init__(self, name: str, row: DraggableRow) -> None:
        super().__init__()
        self.row = row
        with self.classes('bg-blue-grey-2 w-60 p-4 rounded shadow-2 gap-0'):
            ui.label(name).classes('text-bold ml-1')

        self.name = name
        self.on('dragover.prevent', self.highlight)
        self.on('dragleave', self.unhighlight)
        # self.on('drop', lambda event: self.move_card(event))
        self.on('drop', self.unhighlight)

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

            self.row.set_dragged(None)
