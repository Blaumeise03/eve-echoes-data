from typing import Optional

from sqlalchemy import Engine, or_
from sqlalchemy.orm import Session

from echoes_data.exceptions import DataNotFoundException
from echoes_data.models import Solarsystem, Item, Blueprint
from echoes_data.utils import Dialect


class EchoesDB:
    def __init__(self, engine: Engine, dialect: Dialect) -> None:
        self.engine = engine
        self.dialect = dialect

    def fetch_blueprint(self, item_name: str):
        with Session(self.engine, expire_on_commit=False) as conn:
            item = conn.query(Item).filter(Item.name.ilike(item_name)).first()
            if item is None:
                raise DataNotFoundException(f"Item with name {item_name} not found")
            blueprint = (
                conn.query(Blueprint)
                .filter(or_(
                    Blueprint.productId == item.id,
                    Blueprint.blueprintId == item.id))
                .first()
            )
            if blueprint is None:
                raise DataNotFoundException(f"Blueprint for item {item_name}:{item.id} not found")
            print(blueprint)
            return blueprint
