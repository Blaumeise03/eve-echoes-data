import re
from typing import Optional, Dict, Set, Type, TypeVar, List, Union

from sqlalchemy import Engine, or_, select, orm
from sqlalchemy.orm import Session

from echoes_data import models
from echoes_data.exceptions import DataNotFoundException, DataException, CacheException, DataIntegrityException
from echoes_data.utils import Dialect
from ._items import BlueprintData, Item, CacheAble

C_ = TypeVar("C_", bound=CacheAble)


class DataCache:
    def __init__(self):
        self._cache = {}  # type: Dict[Type[C_], Dict[int, C_]]

    def get(self, class_: Type[C_], id_: int) -> Optional[C_]:
        if class_ not in self._cache:
            return None
        if id_ not in self._cache[class_]:
            return None
        return self._cache[class_][id_]

    def find(self, class_: Type[C_], **kwargs) -> Optional[C_]:
        if class_ not in self._cache:
            return None
        for obj in self._cache[class_].values():
            for k, v in kwargs.items():
                if getattr(obj, k) != v:
                    continue
            return obj
        return None

    def get_or_create(self, class_: Type[C_], id_: int, **kwargs) -> C_:
        item = self.get(class_, id_)
        if item is None:
            item = class_(**kwargs)
        self.add(item)
        return item

    def add(self, obj: C_) -> None:
        if not isinstance(obj, CacheAble):
            raise TypeError(f"Object {obj} is not cachable")
        if obj.__class__ not in self._cache:
            self._cache[obj.__class__] = {}
        self._cache[obj.__class__][obj.get_id()] = obj

    def free(self) -> None:
        self._cache.clear()

    def contains(self, class_: Type[C_], id_: int) -> bool:
        if class_ not in self._cache:
            return False
        if id_ not in self._cache[class_]:
            return False
        return True

    def __contains__(self, item) -> bool:
        if type(item) is int:
            for c in self._cache.values():
                if item in c:
                    return True
            return False
        if not isinstance(item, CacheAble):
            return False
        if item.__class__ not in self._cache:
            return False
        if item.get_id() not in self._cache[item.__class__]:
            return False
        return True


MODEL_PRIMARY = {
    models.Item: "id",
    models.Blueprint: "blueprintId"
}  # type: Dict[Type, str]

MODEL_MAPPINGS = {
    models.Blueprint: {
        "blueprintItem": "bp_item",
        "resourceCosts": "resources"
    },
    models.Item: {

    },
    models.BlueprintCosts: {
        "resource": "item"
    }
}
MODEL_TYPES = {
    models.Item: Item,
    models.Blueprint: BlueprintData,
    models.BlueprintCosts: BlueprintData.Cost
}
ATOMIC_ATTRIBUTES = [
    orm.base.Mapped[str],
    orm.base.Mapped[int],
    orm.base.Mapped[float]
]
_re_camel_snake_name = re.compile("(.)([A-Z][a-z]+)")
_re_camel_snake_replace = re.compile("([a-z0-9])([A-Z])")


def camel_to_snake(name):
    name = _re_camel_snake_name.sub(r'\1_\2', name)
    return _re_camel_snake_replace.sub(r'\1_\2', name).lower()


def snake_to_camel(name):
    return name[:1].lower() + ''.join(word.title() for word in name.split('_'))[1:]


# noinspection PyTypeChecker
def _auto_mapper(cache: DataCache, obj: models.Base) -> C_:
    hints = obj.__annotations__
    target_class = MODEL_TYPES[type(obj)]
    if obj.__class__ in MODEL_PRIMARY:
        p_key = MODEL_PRIMARY[obj.__class__]
        key = getattr(obj, p_key)
        res_obj = cache.get(target_class, key)
    else:
        res_obj = None
    if res_obj is not None:
        return res_obj
    if res_obj is None:
        res_obj = target_class()  # type: C_
    for attr, attr_hint in hints.items():
        # Only initialize atomic data types in the first iteration to ensure the id is loaded
        if attr_hint not in ATOMIC_ATTRIBUTES:
            continue
        # Handle int, str, floats
        value = getattr(obj, attr)

        if attr in MODEL_MAPPINGS[obj.__class__]:
            t_name = MODEL_MAPPINGS[obj.__class__][attr]
        else:
            t_name = camel_to_snake(attr)
        if not hasattr(res_obj, f"_{t_name}"):
            continue
        setattr(res_obj, f"_{t_name}", value)

    if isinstance(res_obj, CacheAble):
        cache.add(res_obj)
    # Create a deep copy of complex child objects after the new object has been cached to prevent infinite loops
    for attr, attr_hint in hints.items():
        if attr_hint in ATOMIC_ATTRIBUTES:
            continue
        # Handle complex objects, but only those specified in MODEL_TYPES
        if attr in MODEL_MAPPINGS[obj.__class__]:
            t_name = MODEL_MAPPINGS[obj.__class__][attr]
        else:
            t_name = camel_to_snake(attr)
        if not hasattr(res_obj, f"_{t_name}"):
            continue
        child = getattr(obj, attr)
        if hasattr(child, "__iter__"):
            value = []
            for o in child:
                value.append(_auto_mapper(cache, o))
        elif type(child) not in MODEL_TYPES:
            continue
        else:
            value = _auto_mapper(cache, child)
        setattr(res_obj, f"_{t_name}", value)

    return res_obj


class EchoesDB:
    def __init__(self, engine: Engine, dialect: Dialect) -> None:
        self.engine = engine
        self.dialect = dialect
        self.session = EchoesSession(bind=self)

    def __enter__(self):
        return self.session.__enter__()

    def __exit__(self, exc_type, exc_value, tb):
        return self.session.__exit__(exc_type, exc_value, tb)

    def fetch_item(self,
                   item_name: str,
                   session: Optional[Session] = None,
                   cache: Optional[DataCache] = None) -> Item:
        if session is None:
            with Session(self.engine) as session:
                return self.fetch_item(item_name=item_name, cache=cache, session=session)
        if cache is None:
            cache = DataCache()
        item = cache.find(Item, name=item_name)
        if item is not None:
            return item
        # noinspection PyTypeChecker
        db_item = session.query(models.Item).filter(models.Item.name.ilike(item_name)).first()  # type: models.Item
        if db_item is None:
            raise DataNotFoundException(f"Item with name {item_name} not found")
        return _auto_mapper(cache, db_item)

    def fetch_all_blueprint_data(self,
                                 items: List[Item],
                                 recursive=False,
                                 session: Optional[Session] = None,
                                 cache: Optional[DataCache] = None) -> List[Item]:
        return self._fetch_blueprint_data(items=items, recursive=recursive, session=session, cache=cache)

    def fetch_blueprint_data(self,
                             item: Item,
                             recursive=False,
                             session: Optional[Session] = None,
                             cache: Optional[DataCache] = None) -> Item:
        return self._fetch_blueprint_data(item=item, recursive=recursive, session=session, cache=cache)

    def _fetch_blueprint_data(self,
                              item: Optional[Item] = None,
                              items: Union[List[Item], Set[Item], None] = None,
                              recursive=False,
                              session: Optional[Session] = None,
                              cache: Optional[DataCache] = None,
                              no_error=False) -> Union[List[Item], Item]:
        if item is None and items is None:
            raise TypeError("Either an item or a list of items must be given")
        if item is not None and items is not None:
            raise TypeError("Either an item or a list of items may be given, not both")
        if session is None:
            with Session(self.engine) as session:
                return self._fetch_blueprint_data(item=item, items=items, recursive=recursive, session=session,
                                                  cache=cache)
        if cache is None:
            cache = DataCache()
        if item is not None:
            items = [item]
        item_ids = list(map(lambda i: i.id, items))
        # noinspection PyTypeChecker
        db_bps = (
            session.query(models.Blueprint)
            .filter(or_(
                models.Blueprint.productId.in_(item_ids),
                models.Blueprint.blueprintId.in_(item_ids)))
            .all()
        )  # type: List[models.Blueprint]
        if len(db_bps) > len(items):
            raise DataIntegrityException(f"More blueprints found than queried: Got {len(db_bps)}, queried {len(items)}")
        if len(items) > len(db_bps):
            if len(items) == 1:
                raise DataNotFoundException(f"Blueprint for item {items[0]} not found")
            if not no_error:
                found = list(map(lambda i: i.blueprintId, db_bps))
                missing = ", ".join(map(str, filter(lambda i_id: i_id not in found, item_ids)))
                raise DataNotFoundException(f"Blueprints for items {missing} not found")
        children = set()
        for i in items:
            bp = next(filter(lambda b: b.blueprintId == i.id or b.productId == i.id, db_bps), None)
            if bp is None:
                continue
            bp_data = _auto_mapper(cache, bp)  # type: BlueprintData
            i._blueprint = bp_data
            for cost in bp_data.resources:
                if cost.item.blueprint is None:
                    children.add(cost.item)
        if recursive and len(children) > 0:
            self._fetch_blueprint_data(
                items=children, recursive=recursive, session=session, cache=cache, no_error=True
            )
        print()
        if item is not None:
            return items[0]
        return items


class EchoesSession:
    def __init__(self, bind: EchoesDB):
        self.cache = None  # type: Optional[DataCache]
        self.db = bind

    def __enter__(self):
        self.cache = DataCache()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.cache.free()
        self.cache = None

    def close(self):
        if self.cache is None:
            raise CacheException("Session is already closed")
        self.cache.free()
        self.cache = None

    def fetch_item(self, item_name: str, sql_session: Optional[Session] = None) -> Optional[Item]:
        return self.db.fetch_item(item_name=item_name, cache=self.cache, session=sql_session)

    def fetch_blueprint(self, item: Item, recursive=False,
                        sql_session: Optional[Session] = None) -> Item:
        return self.db.fetch_blueprint_data(item=item, recursive=recursive, session=sql_session, cache=self.cache)
