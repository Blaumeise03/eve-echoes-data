from enum import Enum
from typing import Iterable

from sqlalchemy import TextClause, text

from echoes_data.exceptions import DataException


class Dialect(Enum):
    sqlite = 1
    mysql = 2

    def replace(self, table: str, keys: Iterable[str]) -> TextClause:
        placeholders = ", ".join(map(lambda s: f":{s}", keys))
        columns = ", ".join(keys)
        return text("REPLACE INTO %s ( %s ) VALUES ( %s )" % (table, columns, placeholders))

    def upsert(self, table: str, keys: Iterable[str]):
        placeholders = ", ".join(map(lambda s: f":{s}", keys))
        columns = ", ".join(keys)
        set_ = ", ".join(map(lambda s: f"{s}=:{s}", keys))
        if self == Dialect.sqlite:
            return text(
                f"INSERT INTO {table} ( {columns} ) "
                f"  VALUES ( {placeholders} ) "
                f"  ON CONFLICT DO UPDATE SET {set_}"
            )
        elif self == Dialect.mysql:
            return text(
                f"INSERT INTO {table} ( {columns}) "
                f"  VALUES ( {placeholders}  ) ON DUPLICATE KEY UPDATE {set_}"
            )
        raise DataException(f"Unknown dialect {self}")

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Dialect) and __o.value == self.value

    @classmethod
    def from_str(cls, string: str):
        match string:
            case "sqlite":
                return Dialect.sqlite
            case "mysql":
                return Dialect.mysql
