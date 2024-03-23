#!/usr/bin/env python3
from nicegui.events import GenericEventArguments

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
    def update_chips(event) -> None:
        if len(ds_select.value) < 2:
            ds_select.props(remove='use-chips')
        else:
            ds_select.props(add='use-chips')

    names = ['Alice', 'Bob', 'Carol']
    with ui.select(names, multiple=True, value=names[:1], label='Select data sources', on_change=update_chips) as ds_select:
        ds_select.classes(add='w-64')

    ui.run()


if __name__ in {"__main__", "__mp_main__"}:
    main()
