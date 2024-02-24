import importlib
import inspect
import os
from types import ModuleType
from typing import TypeVar

from plugins.abstract import Interface


def load_plugins(plugin_path: str) -> list[ModuleType]:
    """
    Dynamically load all .py files within a specified directory as modules.

    Parameters:
    - directory: Path to the directory containing .py files.

    Returns:
    - A list of imported module objects.
    """
    modules = list()
    for filename in os.listdir(plugin_path):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = filename.removesuffix(".py")
            module_path = f"{plugin_path.replace('/', '.')}.{module_name}"
            module = importlib.import_module(module_path)
            modules.append(module)
    return modules


InterfaceSubclass = TypeVar("InterfaceSubclass", bound=Interface)


def get_interfaces(modules: list[ModuleType], target_type: type[InterfaceSubclass]) -> list[type[InterfaceSubclass]]:
    """
    Find all subclasses of InterfaceLLM in a list of modules.

    Parameters:
    - modules: A list of modules to search for subclasses.

    Returns:
    - A list of found subclasses of InterfaceLLM.
    """
    subclasses = list()
    for each_module in modules:
        for _, obj in inspect.getmembers(each_module, inspect.isclass):
            if issubclass(obj, target_type) and obj is not target_type:
                subclasses.append(obj)
    return subclasses
