import math
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple, Dict, Union, Literal

from typeguard import typechecked

from echoes_data.data.base import CacheAble
from echoes_data.models import CostType


@typechecked
class Item(CacheAble):
    """
    Represents a basic item. This class does implement the __eq__ method. Two items are equal if their id are equals,
    even if they are different objects of different classes. E.g. if an Item is compared with a Blueprint (while both
    represent the same item with the same ID), they will be equal even if they provide different information.

    This behaviour might change in the future.
    """

    def __init__(self, item_id: Optional[int] = None, name: Optional[str] = None):
        self._id = item_id
        self._name: Optional[str] = name
        self._blueprint: Optional[BlueprintData] = None

    def __eq__(self, other):
        if not isinstance(other, Item):
            return False
        return other.id == self.id

    def __repr__(self):
        return f"Item({self.name})"

    def __hash__(self) -> int:
        return hash((self.__class__, self.get_id()))

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def blueprint(self):
        return self._blueprint

    def get_id(self) -> int:
        return self.id


@typechecked
class BlueprintData(CacheAble):
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

        def __init__(self):
            self._item: Item = None
            self._amount: int = None
            self._type: CostType = None

        def __repr__(self):
            return f"Cost({self.amount}x {self.item.name})"

        @property
        def item(self):
            return self._item

        @property
        def amount(self):
            return self._amount

        @property
        def type(self):
            return self._type

    def __init__(self):
        self._blueprint_id: Optional[int] = None
        self._blueprint: Optional[Item] = None
        self._product: Optional[Item] = None
        self._output_num: Optional[int] = None
        self._skill_lvl: Optional[int] = None
        self._decryptor_mult: Optional[int] = None
        self._money: Optional[int] = None
        self._time: Optional[int] = None
        self._resources: List[BlueprintData.Cost] = []

    def __hash__(self) -> int:
        return hash((self.__class__, self.get_id()))

    def get_id(self) -> int:
        return self._blueprint_id or self._blueprint.id

    @property
    def blueprint(self):
        return self._blueprint

    @property
    def product(self):
        return self._product

    @property
    def output_num(self):
        return self._output_num

    @property
    def skill_lvl(self):
        return self._skill_lvl

    @property
    def decryptor_mult(self):
        return self._decryptor_mult

    @property
    def money(self):
        return self._money

    @property
    def time(self):
        return self._time

    @property
    def resources(self):
        return tuple(self._resources)

    def sort_resources(self, sort_by: Literal["id", "name"] = "id") -> None:
        """
        Sorts the resources by type and name or id. The resource type will be the primary sorting criteria.

        :param sort_by: whether the name or the id should be the secondary sorting criteria.
        """

        def _key(resource: BlueprintData.Cost) -> Tuple[int, str]:
            return resource.type.value, resource.item.name if sort_by == "name" else resource.item.get_id()

        self._resources.sort(key=_key)

    def calculate_costs(self, efficiency: float = 1) -> Dict[Item, int]:
        """
        Calculates the total costs of the item given a specific efficiency. If the blueprint was loaded recursively, this
        function will add up all base costs from the sub-blueprints (e.g. capital components).

        :param efficiency: the target efficiency.
        :return: A dictionary with the items as keys and the required value as the dictionary value.
        """
        total_costs = {}  # type: Dict[Union[Item, BlueprintData], int]
        for cost in self.resources:
            if cost.item.blueprint is not None:
                sub_cost = cost.item.blueprint.calculate_costs(efficiency)
                for c in sub_cost.keys():
                    a = total_costs.get(c, 0)
                    total_costs[c] = a + sub_cost[c] * math.ceil(cost.amount * efficiency)
            a = total_costs.get(cost.item, 0)
            total_costs[cost.item] = a + math.ceil(cost.amount * efficiency)
        return total_costs
