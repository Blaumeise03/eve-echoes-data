from typing import Optional, Dict, Set, Union

from sqlalchemy import Engine, or_, select
from sqlalchemy.orm import Session

from echoes_data import models
from echoes_data.data import Blueprint, Item
from echoes_data.exceptions import DataNotFoundException, DataException
from echoes_data.utils import Dialect


class EchoesDB:
    def __init__(self, engine: Engine, dialect: Dialect) -> None:
        self.engine = engine
        self.dialect = dialect

    def fetch_blueprint(self, item_name: str,
                        recursive=False,
                        session: Optional[Session] = None) -> Blueprint:
        """
        Fetch a blueprint for an item.

        :param item_name: the name of the item, should be case-insensitive but might depend on the underlying database.
        :param recursive: fetch recursively sub blueprints
        :param session: if given, the sqlalchemy sessions used to fetch the data
        :return: The resulting blueprint
        :raises DataNotFoundException: if the item was not found or does not have a blueprint
        """
        if session is None:
            with Session(self.engine) as session:
                return self.fetch_blueprint(item_name=item_name, recursive=recursive, session=session)

        item = session.query(models.Item).filter(models.Item.name.ilike(item_name)).first()
        if item is None:
            raise DataNotFoundException(f"Item with name {item_name} not found")
        # noinspection PyTypeChecker
        db_blueprint = (
            session.query(models.Blueprint)
            .filter(or_(
                models.Blueprint.productId == item.id,
                models.Blueprint.blueprintId == item.id))
            .first()
        )  # type: models.Blueprint
        if db_blueprint is None:
            raise DataNotFoundException(f"Blueprint for item {item_name}:{item.id} not found")
        product = Item(item_id=db_blueprint.product.id, name=db_blueprint.product.name)
        blueprint = Blueprint(
            item_id=db_blueprint.blueprintItem.id,
            name=db_blueprint.blueprintItem.name,
            product=product,
            output_num=db_blueprint.outputNum,
            skill_lvl=db_blueprint.skillLvl,
            decryptor_mult=db_blueprint.decryptorMul,
            money=db_blueprint.money,
            time=db_blueprint.time
        )
        db_sub_costs = {}  # type: Dict[int, models.Blueprint]
        item_cache = {}  # type: Dict[int, Union[Item, Blueprint]]
        loaded = set()  # type: Set[int]
        # Load iterative all child blueprints until
        if recursive:
            not_loaded = [c.resource.id for c in db_blueprint.resourceCosts]
            while len(not_loaded) > 0:
                stmt = select(models.Blueprint).filter(models.Blueprint.productId.in_(not_loaded))
                new = session.execute(stmt).unique().fetchall()
                loaded.update(not_loaded)
                not_loaded = []
                for bp, in new:  # type: models.Blueprint
                    not_loaded.extend(
                        filter(lambda i: i not in loaded,
                               map(lambda c: c.resource.id,
                                   bp.resourceCosts)
                               ))
                    db_sub_costs[bp.productId] = bp
        sub_bps = {}  # type: Dict[int, Blueprint]
        # No start converting the objects, we will start by searching blueprints that only consist of base resources
        # and work our way towards the "root"-blueprint db_blueprint. All converted bps get stored in sub_bps
        while len(db_sub_costs) > 0:
            next_bp = None
            for bp in db_sub_costs.values():
                valid = True
                for cost in bp.resourceCosts:  # type: models.BlueprintCosts
                    if cost.resource.id in db_sub_costs.keys() and cost.resource.id not in sub_bps.keys():
                        valid = False
                        break
                if not valid:
                    continue
                next_bp = bp
                break
            if next_bp is None:
                # This case should in theory not happen because cyclic blueprints are not allowed
                raise DataException(
                    f"Failed resolving blueprint chain for bp {db_blueprint.blueprintId}, possibly cycle detected")
            if next_bp.productId in db_sub_costs:
                db_sub_costs.pop(next_bp.productId)
            if next_bp.productId not in item_cache:
                item_cache[next_bp.productId] = Blueprint(
                    item_id=next_bp.blueprintId, name=next_bp.blueprintItem.name, output_num=next_bp.outputNum,
                    skill_lvl=next_bp.skillLvl, decryptor_mult=next_bp.decryptorMul, money=next_bp.money,
                    product=Item(item_id=next_bp.productId, name=next_bp.product.name), time=next_bp.time
                )
            for cost in next_bp.resourceCosts:
                if cost.resourceId not in item_cache:
                    item_cache[cost.resourceId] = Item(item_id=cost.resourceId, name=cost.resource.name)
                item_cache[next_bp.productId].resources.append(
                    Blueprint.Cost(
                        item=item_cache[cost.resourceId],
                        amount=cost.amount, res_type=cost.type
                    ))

        for cost in db_blueprint.resourceCosts:  # type: models.BlueprintCosts
            if cost.resourceId in item_cache:
                c_i = item_cache[cost.resourceId]
            else:
                c_i = Item(item_id=cost.resource.id, name=cost.resource.name)
            cost_item = Blueprint.Cost(
                item=c_i,
                amount=cost.amount,
                res_type=cost.type
            )
            blueprint.resources.append(cost_item)
        blueprint.sort_resources()
        return blueprint
