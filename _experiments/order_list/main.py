#!/usr/bin/env python3
from draganddrop import DraggableRow, ToDo

from nicegui import ui


def handle_drop(todo: ToDo, location: str) -> None:
    ui.notify(f'"{todo.title}" is now in {location}')


with DraggableRow() as row:
    row.add_column('Next', [
        ToDo('Simplify Layouting'),
        ToDo('Provide Deployment')
    ], handle_drop)
    row.add_column('Doing', [
        ToDo('Improve Documentation')
    ], handle_drop)
    row.add_column('Done', [
        ToDo('Invent NiceGUI'),
        ToDo('Test in own Projects'),
        ToDo('Publish as Open Source'),
        ToDo('Release Native-Mode')
    ], handle_drop)

ui.run()
