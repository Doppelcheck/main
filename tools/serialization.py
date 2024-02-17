from __future__ import annotations

from abc import ABC
from typing import TypeVar, Generic

T = TypeVar('T', bound='DictSerializable')


class JsonSerializable(ABC, Generic[T]):
    """
    @staticmethod
    def class_from_dict(**args: any) -> T:
        class_name = args.pop("class_name")
        return cls(**args)
    """

    @classmethod
    def from_dict(cls: type[T], **args: any) -> T:
        return cls(**args)

    def to_dict(self) -> dict[str, any]:
        return dict(self.__dict__)
