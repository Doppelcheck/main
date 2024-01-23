#!/usr/bin/env python3
import json

from nicegui import ui

from loguru import logger

from src.controller import Controller

# logger.add(sys.stderr, format="{time} {level} {message}", colorize=True, level="INFO")
logger.add("logs/file_{time}.log", backtrace=True, diagnose=True, rotation="500 MB", level="DEBUG")


def main() -> None:
    with open("config/config.json", mode="r") as config_file:
        config = json.load(config_file)

    nicegui_config = config.pop("nicegui")

    c = Controller(config)

    ui.run(**nicegui_config)


if __name__ in {"__main__", "__mp_main__"}:
    main()
