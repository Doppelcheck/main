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


def drop_event(event) -> None:
    print('drop', event)


def main() -> None:
    with ui.column() as draggable_list:
        draggable_list.classes('bg-grey-3 p-4 rounded')

        draggable_list.on('drop', drop_event)
        draggable_list.on('dragover.prevent', lambda event: None)

        for each_text in ["Next", "Doing", "Done"]:
            with ui.card() as each_card:
                each_card.classes('w-full p-4 cursor-move')
                each_card.props('draggable')

                ui.label(each_text)

            each_separator = ui.separator()

    ui.run()


if __name__ in {"__main__", "__mp_main__"}:
    main()
