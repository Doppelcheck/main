#!/usr/bin/env python3
from draganddrop import DraggableRow, Item

from nicegui import ui


def main() -> None:
    with DraggableRow() as row:
        row.add_column('Next', [
            Item('Simplify Layouting'),
            Item('Provide Deployment')
        ])
        row.add_column('Doing', [
            Item('Improve Documentation')
        ])
        row.add_column('Done', [
            Item('Invent NiceGUI'),
            Item('Test in own Projects'),
            Item('Publish as Open Source'),
            Item('Release Native-Mode')
        ])

    ui.run()


if __name__ in {"__main__", "__mp_main__"}:
    main()
