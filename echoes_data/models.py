import enum
from typing import List, Optional

from sqlalchemy import String, ForeignKey, Float, Enum, BigInteger, Integer, Table, Column, Boolean, Text, text
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Region(Base):
    __tablename__ = "regions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), nullable=True)
    x: Mapped[int] = mapped_column(BigInteger, nullable=True)
    y: Mapped[int] = mapped_column(BigInteger, nullable=True)
    z: Mapped[int] = mapped_column(BigInteger, nullable=True)
    faction_id: Mapped[int] = mapped_column(Integer, nullable=True)
    radius: Mapped[int] = mapped_column(BigInteger, nullable=True)
    wormhole_class_id: Mapped[int] = mapped_column(Integer, nullable=True)
    constellations: Mapped[List["Constellation"]] = relationship(back_populates="region")

    def __repr__(self) -> str:
        return f"Region(id={self.id!r}, name={self.name!r})"


class Constellation(Base):
    __tablename__ = "constellations"
    id: Mapped[int] = mapped_column(primary_key=True)
    region_id = mapped_column(ForeignKey("regions.id", name="key_const_reg", ondelete="CASCADE"))
    region: Mapped[Region] = relationship(back_populates="constellations")
    name: Mapped[str] = mapped_column(String(30), nullable=True)
    x: Mapped[int] = mapped_column(BigInteger, nullable=True)
    y: Mapped[int] = mapped_column(BigInteger, nullable=True)
    z: Mapped[int] = mapped_column(BigInteger, nullable=True)
    faction_id: Mapped[int] = mapped_column(Integer, nullable=True)
    radius: Mapped[int] = mapped_column(BigInteger, nullable=True)
    wormhole_class_id: Mapped[int] = mapped_column(Integer, nullable=True)
    systems: Mapped[List["Solarsystem"]] = relationship(back_populates="constellation")

    def __repr__(self) -> str:
        return f"Constellation(id={self.id!r}, name={self.name!r})"


SystemConnections = Table(
    "system_connections", Base.metadata,
    Column("originId", Integer,
           ForeignKey("solarsystems.id", name="key_syscon_sys_or", ondelete="CASCADE"), primary_key=True),
    Column("destinationId", Integer,
           ForeignKey("solarsystems.id", name="key_syscon_sys_dest", ondelete="CASCADE"), primary_key=True))


class Solarsystem(Base):
    __tablename__ = "solarsystems"
    id: Mapped[int] = mapped_column(primary_key=True)
    region_id = mapped_column(ForeignKey("regions.id", name="key_sys_reg"))
    region: Mapped[Region] = relationship()
    constellation_id = mapped_column(ForeignKey("constellations.id", name="key_sys_const", ondelete="CASCADE"))
    constellation: Mapped[Constellation] = relationship(back_populates="systems")
    name: Mapped[str] = mapped_column(String(30), index=True, nullable=True)
    x: Mapped[int] = mapped_column(BigInteger, nullable=True)
    y: Mapped[int] = mapped_column(BigInteger, nullable=True)
    z: Mapped[int] = mapped_column(BigInteger, nullable=True)
    security: Mapped[int] = mapped_column(Float, nullable=True)
    faction_id: Mapped[int] = mapped_column(Integer, nullable=True)
    radius: Mapped[int] = mapped_column(BigInteger, nullable=True)
    celestials: Mapped[List["Celestial"]] = relationship(back_populates="system")
    planets: List["Celestial"]
    neighbours: Mapped[List["Solarsystem"]] = relationship("Solarsystem",
                                                           secondary=SystemConnections,
                                                           primaryjoin=SystemConnections.c.originId == id,
                                                           secondaryjoin=SystemConnections.c.destinationId == id)

    @property
    def planets(self) -> List["Celestial"]:
        planet_list = []
        for celestial in self.celestials:
            if celestial.type == Celestial.Type.planet:
                planet_list.append(celestial)
        return planet_list

    def __repr__(self) -> str:
        return f"System(id={self.id!r}, name={self.name!r})"


StargateConnections = Table(
    "stargates", Base.metadata,
    Column("from_gate_id", ForeignKey("celestials.id", name="key_gates_from", ondelete="CASCADE"), primary_key=True),
    Column("to_gate_id", ForeignKey("celestials.id", name="key_gates_to", ondelete="CASCADE"), primary_key=True),
    Column("from_sys_id", ForeignKey("solarsystems.id", name="key_gates_sys_from", ondelete="CASCADE")),
    Column("to_sys_id", ForeignKey("solarsystems.id", name="key_gates_sys_to", ondelete="CASCADE"))
)


class Celestial(Base):
    class GroupID(object):
        def __init__(self, group_id: Optional[int] = None):
            self.groupID = group_id

    class TypeID(object):
        def __init__(self, type_id: Optional[int] = None):
            self.typeID = type_id

    class TypeGroupID(TypeID, GroupID):
        def __init__(self, type_id: Optional[int] = None, group_id: Optional[int] = None):
            super().__init__(type_id)
            self.groupID = group_id

    class NamedTypeID(TypeID):
        def __init__(self, type_name: str, type_id: Optional[int] = None):
            super().__init__(type_id)
            self.type_name = type_name

    class Type(TypeGroupID, enum.Enum):
        region = 3, 3
        constellation = 4, 4
        system = 5, 5
        star = None, 6
        planet = None, 7
        moon = None, 8
        asteroid_belt = 15, 9
        stargate = None, 10
        npc_station = None, 15
        unknown_anomaly = None, 995

        def __repr__(self):
            return 'MapType(%s, type_id %r, group_id %r)' % (self.__name__, self.typeID, self.groupID)

        @staticmethod
        def from_group_id(group_id):
            for c_type in Celestial.Type:
                if c_type.groupID == group_id:
                    return c_type
            return None

    class PlanetType(NamedTypeID, enum.Enum):
        ice = "Ice", 12
        oceanic = "Oceanic", 2014
        temperate = "Temperate", 11
        barren = "Barren", 2016
        lava = "Lava", 2015
        gas = "Gas", 13
        storm = "Storm", 2017
        plasma = "Plasma", 2063
        unknown = "N/A", 30889

        @staticmethod
        def from_str(label: str):
            for p_type in Celestial.PlanetType:
                if p_type.name == label.casefold():
                    return p_type
            return None

        @staticmethod
        def from_type_id(type_id: int):
            for p_type in Celestial.PlanetType:
                if p_type.typeID == type_id:
                    return p_type
            return None

    __tablename__ = "celestials"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=True)
    type_id: Mapped[int] = mapped_column(Integer, nullable=True)
    group_id: Mapped[int] = mapped_column(Integer, nullable=True)
    system_id = mapped_column(ForeignKey("solarsystems.id", name="key_celest_sys", ondelete="CASCADE"))
    system: Mapped[Solarsystem] = relationship(back_populates="celestials")
    orbit_id: Mapped[int] = mapped_column(Integer, nullable=True)
    x: Mapped[int] = mapped_column(BigInteger, nullable=True)
    y: Mapped[int] = mapped_column(BigInteger, nullable=True)
    z: Mapped[int] = mapped_column(BigInteger, nullable=True)
    radius: Mapped[int] = mapped_column(BigInteger, nullable=True)
    security: Mapped[int] = mapped_column(Float, nullable=True)
    celestial_index: Mapped[int] = mapped_column(Integer, nullable=True)
    orbit_index: Mapped[int] = mapped_column(Integer, nullable=True)
    resources: Mapped[List["PlanetExploit"]] = relationship(back_populates="planet")

    @hybrid_property
    def type(self) -> Type:
        return Celestial.Type.from_group_id(self.group_id)

    @hybrid_property
    def planet_type(self) -> PlanetType:
        return Celestial.PlanetType.from_type_id(self.type_id)

    def __repr__(self) -> str:
        return "Celestial(id={id!s}, name={name!s}, type={type!s})".format(
            id=self.id,
            name=self.name,
            # system_name=self.system.name if self.system is not None else "None",
            type=self.type.name if self.type is not None else self.type_id
        )


class Unit(Base):
    __tablename__ = "unit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(Text(), nullable=True)
    displayName: Mapped[str] = mapped_column(String(64), nullable=True)
    unitName: Mapped[str] = mapped_column(String(64))


class LocalizedString(Base):
    __tablename__ = "localised_strings"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source: Mapped[str] = mapped_column(Text(), nullable=True)
    en: Mapped[str] = mapped_column(Text(), nullable=True)
    de: Mapped[str] = mapped_column(Text(), nullable=True)
    fr: Mapped[str] = mapped_column(Text(), nullable=True)
    ja: Mapped[str] = mapped_column(Text(), nullable=True)
    kr: Mapped[str] = mapped_column(Text(), nullable=True)
    por: Mapped[str] = mapped_column(Text(), nullable=True)
    ru: Mapped[str] = mapped_column(Text(), nullable=True)
    spa: Mapped[str] = mapped_column(Text(), nullable=True)
    zh: Mapped[str] = mapped_column(Text(), nullable=True)
    zhcn: Mapped[str] = mapped_column(Text(), nullable=True)


class MarketGroup(Base):
    __tablename__ = "market_group"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sourceName: Mapped[str] = mapped_column(String(32), nullable=False)
    localisationIndex: Mapped[int] = mapped_column(
        ForeignKey("localised_strings.id", name="localised_strings_market_group"), nullable=False)
    parentId: Mapped[int] = mapped_column(ForeignKey("market_group.id", name="market_group_parent"), nullable=True)
    iconIndex: Mapped[int] = mapped_column(BigInteger(), nullable=True)


class Attribute(Base):
    __tablename__ = "attributes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attributeCategory: Mapped[int] = mapped_column(Integer)
    attributeName: Mapped[str] = mapped_column(String(64))
    available: Mapped[bool] = mapped_column(Boolean)
    chargeRechargeTimeId: Mapped[int] = mapped_column(Integer)
    defaultValue: Mapped[float] = mapped_column(Float)
    highIsGood: Mapped[bool] = mapped_column(Boolean)
    maxAttributeId: Mapped[int] = mapped_column(Integer)
    attributeOperator: Mapped[str] = mapped_column(Text())
    stackable: Mapped[bool] = mapped_column(Boolean)
    toAttrId: Mapped[str] = mapped_column(Text())
    unitId = mapped_column(ForeignKey("unit.id", name="key_attributes_unit"))
    unit: Mapped[Unit] = relationship()
    # Those are not yet implemented and are only placeholders for now
    unitLocalisationKey: Mapped[int] = mapped_column(
        ForeignKey("localised_strings.id", name="localised_strings_local_unit"), nullable=True)
    attributeSourceUnit: Mapped[str] = mapped_column(String(64), nullable=True)
    attributeTip: Mapped[str] = mapped_column(String(128), nullable=True)
    attributeSourceName: Mapped[str] = mapped_column(String(64), nullable=True)
    nameLocalisationKey: Mapped[int] = mapped_column(
        ForeignKey("localised_strings.id", name="localised_strings_local_name"), nullable=True)
    tipLocalisationKey: Mapped[int] = mapped_column(
        ForeignKey("localised_strings.id", name="localised_strings_local_tip"), nullable=True)
    attributeFormula: Mapped[str] = mapped_column(String(64), server_default="A")


class Effect(Base):
    __tablename__ = "effects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    effectName: Mapped[str] = mapped_column(String(64))
    effectCategory: Mapped[int] = mapped_column(Integer, server_default="0")
    disallowAutoRepeat: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"))
    guid: Mapped[str] = mapped_column(String(64))
    isAssistance: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"))
    isOffensive: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"))
    isWarpSafe: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"))
    electronicChance: Mapped[int] = mapped_column(Integer, server_default="0")
    falloffAttributeId: Mapped[int] = mapped_column(
        Integer, ForeignKey("attributes.id", name="key_effect_attr_falloff"), nullable=True)
    fittingUsageChanceAttributeId: Mapped[int] = mapped_column(
        Integer, ForeignKey("attributes.id", name="key_effect_attr_fitting"), nullable=True)
    dischargeAttributeId: Mapped[int] = mapped_column(
        Integer, ForeignKey("attributes.id", name="key_effect_attr_discharge"), nullable=True)
    durationAttributeId: Mapped[int] = mapped_column(
        Integer, ForeignKey("attributes.id", name="key_effect_attr_duration"), nullable=True)
    rangeAttributeId: Mapped[int] = mapped_column(Integer, nullable=True)
    rangeChance: Mapped[int] = mapped_column(
        ForeignKey("attributes.id", name="key_effect_attr_range"), nullable=True)
    trackingSpeedAttributeId: Mapped[int] = mapped_column(
        ForeignKey("attributes.id", name="key_effect_attr_tracking"), nullable=True)


class Group(Base):
    __tablename__ = "groups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=True)
    anchorable: Mapped[bool] = mapped_column(Boolean, nullable=True)
    anchored: Mapped[bool] = mapped_column(Boolean, nullable=True)
    fittableNonSingleton: Mapped[bool] = mapped_column(Boolean, nullable=True)
    iconPath: Mapped[str] = mapped_column(String(128), nullable=True)
    useBasePrice: Mapped[bool] = mapped_column(Boolean, nullable=True)
    localisedNameIndex: Mapped[int] = mapped_column(
        ForeignKey("localised_strings.id", name="key_groups_loc"), nullable=True)
    sourceName: Mapped[str] = mapped_column(String(64), nullable=True)
    itemIds: Mapped[str] = mapped_column(String(64), nullable=True)


class Categories(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=True)
    groupIds: Mapped[str] = mapped_column(String(64), nullable=True)
    localisedNameIndex: Mapped[int] = mapped_column(
        ForeignKey("localised_strings.id", name="key_categories_loc"), nullable=True)
    sourceName: Mapped[str] = mapped_column(String(64), nullable=True)


class Type(Base):
    __tablename__ = "types"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    short_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(64))
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", name="key_types_groups"), nullable=True)
    group: Mapped[Group] = relationship()


class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=True)
    canBeJettisoned: Mapped[bool] = mapped_column(Boolean, nullable=True)
    descSpecial: Mapped[str] = mapped_column(String(64), nullable=True)
    mainCalCode: Mapped[str] = mapped_column(String(128), nullable=True)
    onlineCalCode: Mapped[str] = mapped_column(String(128), nullable=True)
    activeCalCode: Mapped[str] = mapped_column(String(128), nullable=True)
    sourceDesc: Mapped[str] = mapped_column(Text(), nullable=True)
    sourceName: Mapped[str] = mapped_column(String(64), nullable=True)
    nameKey: Mapped[int] = mapped_column(
        ForeignKey("localised_strings.id", name="key_items_loc_name"), nullable=True)
    descKey: Mapped[int] = mapped_column(
        ForeignKey("localised_strings.id", name="key_items_loc_desc"), nullable=True)
    marketGroupId: Mapped[int] = mapped_column(Integer, nullable=True)
    lockSkin: Mapped[str] = mapped_column(String(64), nullable=True)
    npcCalCodes: Mapped[str] = mapped_column(Text(), nullable=True)
    corpCamera: Mapped[str] = mapped_column(String(64), nullable=True)
    abilityList: Mapped[str] = mapped_column(String(64), nullable=True)
    normalDebris: Mapped[str] = mapped_column(String(64), nullable=True)
    shipBonusCodeList: Mapped[str] = mapped_column(Text(), nullable=True)
    shipBonusSkillList: Mapped[str] = mapped_column(Text(), nullable=True)
    # These are still not implemented properly
    product: Mapped[str] = mapped_column(BigInteger(), nullable=True)
    exp: Mapped[str] = mapped_column(Float(), nullable=True)
    published: Mapped[bool] = mapped_column(Boolean(), nullable=True)  # , server_default=text("FALSE"))
    preSkill: Mapped[str] = mapped_column(String(32), nullable=True)

    def __repr__(self) -> str:
        return f"Item(id={self.id!r}, name={self.name!r})"


class ItemNanocore(Base):
    __tablename__ = "item_nanocores"
    itemId: Mapped[int] = mapped_column(
        ForeignKey("items.id", name="key_itemnanocore_item"), primary_key=True)
    filmGroup: Mapped[str] = mapped_column(String(64), nullable=True)
    filmQuality: Mapped[int] = mapped_column(Integer, nullable=True)
    availableShips: Mapped[str] = mapped_column(Text(), nullable=True)
    selectableModifierItems: Mapped[str] = mapped_column(Text(), nullable=True)
    trainableModifierItems: Mapped[str] = mapped_column(Text(), nullable=True)


class CorpTaskItem(Base):
    __tablename__ = "corp_task_items"
    itemId: Mapped[int] = mapped_column(
        ForeignKey("items.id", name="key_corptask_item"), primary_key=True)
    fpReward: Mapped[int] = mapped_column(Integer)
    maxPerWeek: Mapped[int] = mapped_column(Integer)
    purchaseNum: Mapped[int] = mapped_column(Integer)
    randomGroup: Mapped[int] = mapped_column(Integer)
    weekTimes: Mapped[int] = mapped_column(Integer)


class ItemAttribute(Base):
    __tablename__ = "item_attributes"
    itemId: Mapped[int] = mapped_column(
        ForeignKey("items.id", name="key_itemattr_item"), primary_key=True)
    attributeId: Mapped[int] = mapped_column(
        ForeignKey("attributes.id", name="key_itemattr_attr"), primary_key=True)
    value: Mapped[float] = mapped_column(Float)


class ItemEffects(Base):
    __tablename__ = "item_effects"
    itemId: Mapped[int] = mapped_column(
        ForeignKey("items.id", name="key_itemeff_item"), primary_key=True)
    effectId: Mapped[int] = mapped_column(
        ForeignKey("effects.id", name="key_itemeff_eff"), primary_key=True)
    isDefault: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"))


class ModifierDefinition(Base):
    __tablename__ = "modifier_definition"
    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    changeTypes: Mapped[str] = mapped_column(Text())
    attributeOnly: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"))
    changeRanges: Mapped[str] = mapped_column(Text())
    changeRangeModuleNames: Mapped[str] = mapped_column(Text(), nullable=True)
    attributeIds: Mapped[str] = mapped_column(Text())


class ModifierValue(Base):
    __tablename__ = "modifier_value"
    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    attributes: Mapped[str] = mapped_column(Text())
    typeName: Mapped[str] = mapped_column(
        ForeignKey("modifier_definition.code", name="key_modifiervalue_modifierdef"), primary_key=True)


class ItemModifiers(Base):
    __tablename__ = "item_modifiers"
    # Every table have to have a primary key
    pk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64))
    typeCode: Mapped[str] = mapped_column(String(64))
    changeType: Mapped[str] = mapped_column(String(64))
    attributeOnly: Mapped[bool] = mapped_column(Boolean)
    changeRange: Mapped[str] = mapped_column(String(128))
    changeRangeModuleNameId: Mapped[int] = mapped_column(Integer)
    attributeId: Mapped[int] = mapped_column(Integer)
    attributeValue: Mapped[float] = mapped_column(Float)


class RepackageVolume(Base):
    __tablename__ = "repackage_volume"
    # Every table have to have a primary key
    pk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", name="key_repack_group"), unique=True, nullable=True)
    type_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", name="key_repack_item"), unique=True, nullable=True)
    volume: Mapped[float] = mapped_column(Float)


class Reprocess(Base):
    __tablename__ = "reprocess"
    itemId: Mapped[int] = mapped_column(
        ForeignKey("items.id", name="key_reprocess_item_base"), primary_key=True)
    resultId: Mapped[int] = mapped_column(
        ForeignKey("items.id", name="key_reprocess_item_result"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer)


class Blueprint(Base):
    __tablename__ = "blueprints"
    blueprintId: Mapped[int] = mapped_column(
        ForeignKey("items.id", name="key_blueprint_items_bp"), primary_key=True)
    blueprintItem: Mapped[Item] = relationship(foreign_keys=[blueprintId], lazy="joined")
    productId: Mapped[int] = mapped_column(
        ForeignKey("items.id", name="key_blueprint_items_prod"), primary_key=True)
    product: Mapped[Item] = relationship(foreign_keys=[productId], lazy="joined")
    outputNum: Mapped[int] = mapped_column(Integer)
    skillLvl: Mapped[int] = mapped_column(Integer)
    materialAmendAtt: Mapped[int] = mapped_column(
        ForeignKey("attributes.id", name="key_blueprint_attributes_mats"), primary_key=True)
    decryptorMul: Mapped[int] = mapped_column(Integer)
    money: Mapped[int] = mapped_column(BigInteger)
    time: Mapped[int] = mapped_column(Integer)
    timeAmendAtt: Mapped[int] = mapped_column(
        ForeignKey("attributes.id", name="key_blueprint_attributes_time"), primary_key=True)
    type: Mapped[int] = mapped_column(Integer)
    resourceCosts: Mapped[List["BlueprintCosts"]] = relationship(back_populates="blueprint", lazy="joined")

    def __repr__(self):
        return f"Blueprint({self.blueprintId})"


class CostType(enum.Enum):
    pi = 0
    minerals = 1
    component = 2
    module = 3
    salvage = 4
    ship = 5
    blueprint = 6
    datacore = 7

    @staticmethod
    def from_str(label: str):
        for p_type in CostType:
            if p_type.name.casefold() == label.casefold():
                return p_type
        return None


class BlueprintCosts(Base):
    __tablename__ = "blueprint_costs"
    blueprintId: Mapped[int] = mapped_column(
        ForeignKey("blueprints.blueprintId", name="key_blueprintcost_bp"), primary_key=True)
    blueprint: Mapped[Blueprint] = relationship(back_populates="resourceCosts")
    resourceId: Mapped[int] = mapped_column(
        ForeignKey("items.id", name="key_blueprintcost_item"), primary_key=True)
    resource: Mapped[Item] = relationship(foreign_keys=[resourceId], lazy="joined")
    amount: Mapped[int] = mapped_column(Integer)
    type: Mapped[CostType] = mapped_column(Enum(CostType), nullable=True)

    def __repr__(self):
        return f"BpCost({self.amount}x {self.resource.name})"


class Richness(enum.Enum):
    poor = "poor"
    medium = "medium"
    rich = "rich"
    perfect = "perfect"

    @staticmethod
    def from_str(label: str):
        for p_type in Richness:
            if p_type.value.casefold() == label.casefold():
                return p_type
        return None


class PlanetExploit(Base):
    # Eve Echoes PI Static Data Export CSV format:
    # Planet ID;Region;Constellation;System;Planet Name;Planet Type;Resource;Richness;Output
    __tablename__ = "planet_exploit"
    planet_id: Mapped[int] = mapped_column(ForeignKey("celestials.id", name="key_res_planet", ondelete="CASCADE"),
                                           primary_key=True)
    planet: Mapped[Celestial] = relationship(back_populates="resources")
    type_id: Mapped[int] = mapped_column(ForeignKey("items.id", name="key_res_item"), primary_key=True)
    type: Mapped[Item] = relationship()
    output: Mapped[float] = mapped_column(Float())
    richness: Mapped[int] = mapped_column(Enum(Richness))
    richness_value: Mapped[int] = mapped_column(Integer)
    location_index: Mapped[int] = mapped_column(Integer)

    def __repr__(self) -> str:
        return f"PlanetExploit(planet={self.planet_id}, res={self.type_id})"


class CorpTech(Base):
    __tablename__ = "corp_tech"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    corp_lv_require: Mapped[int] = mapped_column(Integer)
    max_lv: Mapped[int] = mapped_column(Integer)
    source_desc: Mapped[str] = mapped_column(String(64))
    desc_key: Mapped[int] = mapped_column(
        ForeignKey("localised_strings.id", name="key_corptech_loc_desc"), nullable=True)
    source_name: Mapped[str] = mapped_column(String(32))
    name_key: Mapped[int] = mapped_column(
        ForeignKey("localised_strings.id", name="key_corptech_loc_name"), nullable=True)
    ui_pos: Mapped[int] = mapped_column(Integer)


class CorpTechLevel(Base):
    __tablename__ = "corp_tech_level"
    tech_id: Mapped[int] = mapped_column(ForeignKey("corp_tech.id", name="key_level_corptech"), primary_key=True)
    tech_lvl: Mapped[int] = mapped_column(Integer, primary_key=True)
    fp_require: Mapped[int] = mapped_column(Integer)
    isk_require: Mapped[int] = mapped_column(BigInteger)
    online_cal_code: Mapped[str] = mapped_column(String(64))
