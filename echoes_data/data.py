import math
from typing import Optional, List, Tuple, Dict, Union, Literal

from typeguard import typechecked

from echoes_data.models import CostType


@typechecked
class Item:
    """
    Represents a basic item. This class does implement the __eq__ method. Two items are equal if their id are equals,
    even if they are different objects of different classes. E.g. if an Item is compared with a Blueprint (while both
    represent the same item with the same ID), they will be equal even if they provide different information.

    This behaviour might change in the future.
    """
    def __init__(self, item_id: int, name: Optional[str]):
        if type(item_id) != int:
            raise TypeError(f"Item ID must be an integer, got {type(item_id)}")
        self.id = item_id
        if name is not None and type(name) != str:
            raise TypeError(f"Item name must be a string, got {type(name)}")
        self.name: Optional[str] = name

    def __eq__(self, other):
        if not isinstance(other, Item):
            return False
        return other.id == self.id

    def __repr__(self):
        return f"Item({self.name})"

    def __hash__(self) -> int:
        return hash((self.__class__, self.id))


@typechecked
class Blueprint(Item):
    """
    Represents a blueprint item. This class might also change in the future, at the moment it inherits from the
    :class:`Item`.
    """
    @typechecked
    class Cost:
        """
        Represents a required material for a blueprint. It contains the :class:`Item` of the material, the required
        base amount (when building with 100% efficiency) and the type of the material.
        """
        def __init__(self,
                     item: Item,
                     amount: int,
                     res_type: CostType):
            self.item = item
            self.amount: int = amount
            self.type: CostType = res_type

        def __repr__(self):
            return f"Cost({self.amount}x {self.item.name})"

    def __init__(self,
                 item_id: int,
                 name: Optional[str],
                 product: Item,
                 output_num: int,
                 skill_lvl: int,
                 decryptor_mult: int,
                 money: int,
                 time: int):
        """
        Create a new blueprint

        :param item_id: the id of the blueprint item.
        :param name: the name of the blueprint item.
        :param product:  the product :class:`Item`.
        :param output_num: the number of output items.
        :param skill_lvl: the required tech level to build this blueprint.
        :param decryptor_mult: the decryptor multiplier.
        :param money: the amount of ISK required to start the build job of this blueprint.
        :param time: the time required to build this blueprint.
        """
        super().__init__(item_id, name)
        self.product: Item = product
        self.outputNum: int = output_num
        self.skill_lvl: int = skill_lvl
        self.decryptor_mult: int = decryptor_mult
        self.money: int = money
        self.time: int = time
        self.resources: List[Blueprint.Cost] = []

    def sort_resources(self, sort_by: Literal["id", "name"] = "id") -> None:
        """
        Sorts the resources by type and name or id. The resource type will be the primary sorting criteria.

        :param sort_by: whether the name or the id should be the secondary sorting criteria.
        """
        def _key(resource: Blueprint.Cost) -> Tuple[int, str]:
            return resource.type.value, resource.item.name if sort_by == "name" else resource.item.id

        self.resources.sort(key=_key)

    def calculate_costs(self, efficiency: float = 1) -> Dict[Union[Item, "Blueprint"], int]:
        """
        Calculates the total costs of the item given a specific efficiency. If the blueprint was loaded recursively, this
        function will add up all base costs from the sub-blueprints (e.g. capital components).

        :param efficiency: the target efficiency.
        :return: A dictionary with the items as keys and the required value as the dictionary value.
        """
        total_costs = {}  # type: Dict[Union[Item, Blueprint], int]
        for cost in self.resources:
            if isinstance(cost.item, Blueprint):
                sub_cost = cost.item.calculate_costs(efficiency)
                for c in sub_cost.keys():
                    a = total_costs.get(c, 0)
                    total_costs[c] = a + sub_cost[c] * math.ceil(cost.amount * efficiency)
            a = total_costs.get(cost.item, 0)
            total_costs[cost.item] = a + math.ceil(cost.amount * efficiency)
        return total_costs
