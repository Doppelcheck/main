#!/usr/bin/env python3
from draganddrop import DraggableRow, Item

from nicegui import ui


def _main() -> None:
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


def main() -> None:
    with ui.column() as draggable_list:
        draggable_list.classes('bg-grey-3 p-4 rounded')

        draggable_list.on('drop', lambda event: print('drop', event))

        for each_text in ["Next", "Doing", "Done"]:
            with ui.card() as each_card:
                each_card.classes('w-full p-4 cursor-move')
                each_card.props('draggable')

                ui.label(each_text)

            each_separator = ui.separator()
            each_separator.on('drop', lambda event: print('drop', event))

    ui.run()


if __name__ in {"__main__", "__mp_main__"}:
    main()
