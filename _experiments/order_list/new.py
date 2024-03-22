from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, TypeVar
from nicegui import ui


@dataclass
class Item:
    title: str


ImplementedItem = TypeVar("ImplementedItem", bound=Item)


@dataclass
class ToDo(Item):
    pass


class DraggableCard(ui.card):
    def __init__(self, item: Item, parent: DraggableContainer) -> None:
        super().__init__()
        self.item = item
        self.parent = parent
        with self.props('draggable').classes('w-full cursor-pointer bg-grey-1'):
            ui.label(item.title)
        self.on('dragstart', self.on_drag_start)
        self.on('dragend', self.on_drag_end)

    def on_drag_start(self, event) -> None:
        self.parent.dragged = self

    def on_drag_end(self, event) -> None:
        self.parent.dragged = None

class DraggableContainer:
    def __init__(self):
        self.dragged: Optional[DraggableCard] = None
        self.columns: List[DraggableColumn] = []

    def add_column(self, name: str, todos: List[ToDo]) -> DraggableColumn:
        column = DraggableColumn(name, todos, self)
        self.columns.append(column)
        return column

class DraggableColumn(ui.column):
    def __init__(self, name: str, todos: List[ToDo], container: DraggableContainer) -> None:
        super().__init__()
        self.name = name
        self.todos = todos
        self.container = container
        self.build_column()

    def build_column(self) -> None:
        with self.classes('bg-blue-grey-2 w-60 p-4 rounded shadow-2 gap-0'):
            ui.label(self.name).classes('text-bold ml-1')

        for todo in self.todos:
            DraggableCard(todo, self.container)

        self.on('dragover.prevent', lambda e: self.highlight(True))
        self.on('dragleave', lambda e: self.highlight(False))
        self.on('drop', self.on_drop)

    def highlight(self, do_highlight: bool) -> None:
        if do_highlight:
            self.classes(add='bg-blue-grey-3')
        else:
            self.classes(remove='bg-blue-grey-3')

    def on_drop(self, event) -> None:
        dragged_card = self.container.dragged
        if dragged_card and dragged_card.item not in self.todos:
            # Remove from old column, if present
            for column in self.container.columns:
                if dragged_card.item in column.todos:
                    column.todos.remove(dragged_card.item)
                    column.build_column()
                    break
            # Add to new column
            self.todos.append(dragged_card.item)
            self.build_column()

# Usage example
container = DraggableContainer()
column1 = container.add_column('To Do', [ToDo('Task 1'), ToDo('Task 2')])
column2 = container.add_column('Done', [ToDo('Task 3')])

ui.run()
