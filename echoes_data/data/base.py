from abc import ABC, abstractmethod


class CacheAble(ABC):
    @abstractmethod
    def get_id(self) -> int:
        pass

    def __hash__(self) -> int:
        return hash((self.__class__, self.get_id()))
