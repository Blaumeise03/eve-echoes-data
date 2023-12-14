from abc import ABC, abstractmethod
from typing import Type, TypeVar

from echoes_data import models

_T = TypeVar("_T")
_K = TypeVar("_K")


class Converter(ABC):
    def __init__(self, _cls_from: Type[_T], _cls_to: Type[_K]):
        self._from = _cls_from
        self._to = _cls_to
        self.mappings = {}

    @abstractmethod
    def map(self):
        pass

