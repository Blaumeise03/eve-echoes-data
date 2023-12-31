from sqlite3 import Connection

from sqlalchemy.util import deprecated


@deprecated(version="0.0.2-alpha", message="The table creation should happen via SQLAlchemy")
def setup_basic_tables(conn: Connection, sweet_compatible=False):
    conn.execute("create table if not exists unit("
                 "    id          INTEGER primary key,"
                 "    description TEXT,"
                 "    displayName TEXT,"
                 "    unitName    TEXT );")
    conn.execute("create table if not exists localised_strings("
                 "    id     INTEGER primary key,"
                 "    source TEXT,"
                 "    en     TEXT,"
                 "    de     TEXT,"
                 "    fr     TEXT,"
                 "    ja     TEXT,"
                 "    kr     TEXT,"
                 "    por    TEXT,"
                 "    ru     TEXT,"
                 "    spa    TEXT,"
                 "    zh     TEXT,"
                 "    zhcn   TEXT);")

    if not sweet_compatible:
        conn.execute("create table if not exists attributes("
                     "    id                   INTEGER             not null primary key,"
                     "    attributeCategory    INTEGER             not null,"
                     "    attributeName        TEXT                not null,"
                     "    available            INTEGER             not null,"
                     "    chargeRechargeTimeId INTEGER             not null,"
                     "    defaultValue         REAL                not null,"
                     "    highIsGood           INTEGER             not null,"
                     "    maxAttributeId       INTEGER             not null,"
                     "    attributeOperator    TEXT                not null,"
                     "    stackable            INTEGER             not null,"
                     "    toAttrId             TEXT                not null,"
                     "    unitId               INTEGER             not null,"
                     "    unitLocalisationKey  INTEGER             null ,"
                     "    attributeSourceUnit  TEXT                null,"
                     "    attributeTip         TEXT                null,"
                     "    attributeSourceName  TEXT                null,"
                     "    nameLocalisationKey  INTEGER             null,"
                     "    tipLocalisationKey   INTEGER             null,"
                     "    attributeFormula     TEXT    default 'A' not null,"
                     "    constraint key_attributes_local"
                     "        foreign key (unitLocalisationKey) references localised_strings (id),"
                     "    constraint key_attributes_local"
                     "        foreign key (nameLocalisationKey) references localised_strings (id),"
                     "    constraint key_attributes_local"
                     "        foreign key (tipLocalisationKey) references localised_strings (id),"
                     "    constraint key_attributes_unit"
                     "        foreign key (unitId) references unit (id)"
                     ")")
    else:
        conn.execute("create table if not exists attributes("
                     "    id                   INTEGER             not null primary key,"
                     "    attributeCategory    INTEGER             not null,"
                     "    attributeName        TEXT                not null,"
                     "    available            INTEGER             not null,"
                     "    chargeRechargeTimeId INTEGER             not null,"
                     "    defaultValue         REAL                not null,"
                     "    highIsGood           INTEGER             not null,"
                     "    maxAttributeId       INTEGER             not null,"
                     "    attributeOperator    TEXT                not null,"
                     "    stackable            INTEGER             not null,"
                     "    toAttrId             TEXT                not null,"
                     "    unitId               INTEGER             not null,"
                     "    unitLocalisationKey  INTEGER default 0,"
                     "    attributeSourceUnit  TEXT    default '',"
                     "    attributeTip         TEXT    default '',"
                     "    attributeSourceName  TEXT    default '',"
                     "    nameLocalisationKey  INTEGER default 0,"
                     "    tipLocalisationKey   INTEGER default 0,"
                     "    attributeFormula     TEXT    default 'A' not null);")

    if not sweet_compatible:
        conn.execute("create table if not exists effects("
                     "    id                            INTEGER           not null primary key,"
                     "    effectName                    TEXT              not null,"
                     "    effectCategory                INTEGER default 0 not null,"
                     "    disallowAutoRepeat            INTEGER default 0 not null,"
                     "    guid                          TEXT              not null,"
                     "    isAssistance                  INTEGER default 0 not null,"
                     "    isOffensive                   INTEGER default 0 not null,"
                     "    isWarpSafe                    INTEGER default 0 not null,"
                     "    electronicChance              INTEGER default 0 not null,"
                     "    falloffAttributeId            INTEGER null,"
                     "    fittingUsageChanceAttributeId INTEGER default 0 not null,"
                     "    dischargeAttributeId          INTEGER null,"
                     "    durationAttributeId           INTEGER null,"
                     "    rangeAttributeId              INTEGER null,"
                     "    rangeChance                   INTEGER default 0 not null,"
                     "    trackingSpeedAttributeId      INTEGER null,"
                     "    constraint key_effect_attr_discharge"
                     "        foreign key (dischargeAttributeId) references attributes (id),"
                     "    constraint key_effect_attr_duration"
                     "        foreign key (durationAttributeId) references attributes (id),"
                     "    constraint key_effect_attr_falloff"
                     "        foreign key (falloffAttributeId) references attributes (id),"
                     "    constraint key_effect_attr_fitting"
                     "        foreign key (fittingUsageChanceAttributeId) references attributes (id),"
                     "    constraint key_effect_attr_range"
                     "        foreign key (rangeAttributeId) references attributes (id),"
                     "    constraint key_effect_attr_tracking"
                     "        foreign key (trackingSpeedAttributeId) references attributes (id)"
                     ")")
    else:
        conn.execute("create table if not exists effects("
                     "    id                            INTEGER           not null primary key,"
                     "    disallowAutoRepeat            INTEGER default 0 not null,"
                     "    dischargeAttributeId          INTEGER default 0 not null,"
                     "    durationAttributeId           INTEGER default 0 not null,"
                     "    effectCategory                INTEGER default 0 not null,"
                     "    effectName                    TEXT              not null,"
                     "    electronicChance              INTEGER default 0 not null,"
                     "    falloffAttributeId            INTEGER default 0 not null,"
                     "    fittingUsageChanceAttributeId INTEGER default 0 not null,"
                     "    guid                          TEXT              not null,"
                     "    isAssistance                  INTEGER default 0 not null,"
                     "    isOffensive                   INTEGER default 0 not null,"
                     "    isWarpSafe                    INTEGER default 0 not null,"
                     "    rangeAttributeId              INTEGER default 0 not null,"
                     "    rangeChance                   INTEGER default 0 not null,"
                     "    trackingSpeedAttributeId      INTEGER default 0 not null);")

    if not sweet_compatible:
        conn.execute("create table if not exists groups("
                     "    id                   INTEGER primary key,"
                     "    name                 TEXT    null,"
                     "    anchorable           INTEGER not null default 0,"
                     "    anchored             INTEGER not null default 0,"
                     "    fittableNonSingleton INTEGER not null default 0,"
                     "    iconPath             TEXT,"
                     "    useBasePrice         INTEGER not null default 0,"
                     "    localisedNameIndex   INTEGER     null,"
                     "    sourceName           TEXT,"
                     "    itemIds              TEXT,"
                     "    constraint key_groups_loc"
                     "        foreign key (localisedNameIndex) references localised_strings (id)"
                     ");")
    else:
        conn.execute("create table if not exists groups("
                     "    id                   INTEGER primary key,"
                     "    name                 TEXT    null,"
                     "    anchorable           INTEGER not null default 0,"
                     "    anchored             INTEGER not null default 0,"
                     "    fittableNonSingleton INTEGER not null default 0,"
                     "    iconPath             TEXT,"
                     "    useBasePrice         INTEGER not null default 0,"
                     "    localisedNameIndex   INTEGER not null default 0,"
                     "    sourceName           TEXT,"
                     "    itemIds              TEXT);")
    if not sweet_compatible:
        conn.execute("create table if not exists categories("
                     "    id                 INTEGER primary key,"
                     "    name               TEXT    null,"
                     "    groupIds           TEXT    default '[]',"
                     "    localisedNameIndex INTEGER default 0 not null,"
                     "    sourceName         TEXT,"
                     "    constraint key_categories_loc"
                     "        foreign key (localisedNameIndex) references localised_strings (id)"
                     ");")
    else:
        conn.execute("create table if not exists categories("
                     "    id                 INTEGER primary key,"
                     "    name               TEXT    null,"
                     "    groupIds           TEXT    default '[]',"
                     "    localisedNameIndex INTEGER default 0 not null,"
                     "    sourceName         TEXT"
                     ");")
    conn.execute("create table if not exists types("
                 "    id       INTEGER primary key,"
                 "    short_id INTEGER null UNIQUE,"
                 "    name     TEXT    null,"
                 "    group_id INTEGER null,"
                 "    constraint key_types_groups"
                 "        foreign key (group_id) references groups (id)"
                 "            on delete cascade)")
    if not sweet_compatible:
        conn.execute("create table if not exists items("
                     "    id                 INTEGER primary key,"
                     "    canBeJettisoned    INTEGER            not null,"
                     "    descSpecial        TEXT               not null,"
                     "    mainCalCode        TEXT    default '' not null,"
                     "    onlineCalCode      TEXT    default '',"
                     "    activeCalCode      TEXT    default '',"
                     "    sourceDesc         TEXT               not null,"
                     "    sourceName         TEXT               not null,"
                     "    nameKey            INTEGER            not null,"
                     "    descKey            INTEGER            not null,"
                     "    marketGroupId      INTEGER,"
                     "    lockSkin           TEXT,"
                     "    npcCalCodes        TEXT,"
                     "    product            INTEGER,"
                     "    exp                REAL    default 0  not null,"
                     "    published          INTEGER default 0  not null,"
                     "    preSkill           TEXT,"
                     "    corpCamera         TEXT               not null,"
                     "    abilityList        TEXT               not null,"
                     "    normalDebris       TEXT               not null,"
                     "    shipBonusCodeList  TEXT               not null,"
                     "    shipBonusSkillList TEXT               not null,"
                     "    constraint key_items_loc_name"
                     "        foreign key (nameKey) references localised_strings (id),"
                     "    constraint key_items_loc_desc"
                     "        foreign key (descKey) references localised_strings (id)"
                     ");")
    else:
        conn.execute("create table if not exists items("
                     "    id                 INTEGER primary key,"
                     "    canBeJettisoned    INTEGER            not null,"
                     "    descSpecial        TEXT               not null,"
                     "    mainCalCode        TEXT    default '' not null,"
                     "    onlineCalCode      TEXT    default '',"
                     "    activeCalCode      TEXT    default '',"
                     "    sourceDesc         TEXT               not null,"
                     "    sourceName         TEXT               not null,"
                     "    nameKey            INTEGER            not null,"
                     "    descKey            INTEGER            not null,"
                     "    marketGroupId      INTEGER,"
                     "    lockSkin           TEXT,"
                     "    npcCalCodes        TEXT,"
                     "    product            INTEGER,"
                     "    exp                REAL    default 0  not null,"
                     "    published          INTEGER default 0  not null,"
                     "    preSkill           TEXT,"
                     "    corpCamera         TEXT               not null,"
                     "    abilityList        TEXT               not null,"
                     "    normalDebris       TEXT               not null,"
                     "    shipBonusCodeList  TEXT               not null,"
                     "    shipBonusSkillList TEXT               not null"
                     ");")
    if not sweet_compatible:
        conn.execute("create table if not exists item_nanocores("
                     "    itemId                  INTEGER not null primary key,"
                     "    filmGroup               TEXT    not null,"
                     "    filmQuality             INTEGER not null,"
                     "    availableShips          TEXT    not null,"
                     "    selectableModifierItems TEXT    not null,"
                     "    trainableModifierItems  TEXT    not null,"
                     "    constraint key_nanocore_item"
                     "        foreign key (itemId) references items (id)"
                     ");")
    else:
        conn.execute("create table if not exists item_nanocores("
                     "    itemId                  INTEGER not null primary key,"
                     "    filmGroup               TEXT    not null,"
                     "    filmQuality             INTEGER not null,"
                     "    availableShips          TEXT    not null,"
                     "    selectableModifierItems TEXT    not null,"
                     "    trainableModifierItems  TEXT    not null"
                     ");")
    if not sweet_compatible:
        conn.execute("create table if not exists item_attributes ("
                     "    itemId      INTEGER not null,"
                     "    attributeId INTEGER not null,"
                     "    value       REAL    not null,"
                     "    primary key (itemId, attributeId),"
                     "    constraint key_itemattributes_item"
                     "        foreign key (itemId) references items (id),"
                     "    constraint key_itemattributes_attributes"
                     "        foreign key (attributeId) references attributes (id)"
                     ");")
    else:
        conn.execute("create table if not exists item_attributes ("
                     "    itemId      INTEGER not null,"
                     "    attributeId INTEGER not null,"
                     "    value       REAL    not null,"
                     "    primary key (itemId, attributeId)"
                     ");")
    if not sweet_compatible:
        conn.execute("create table if not exists item_effects("
                     "    itemId    INTEGER           not null,"
                     "    effectId  INTEGER           not null,"
                     "    isDefault INTEGER default 0 not null,"
                     "    primary key (itemId, effectId),"
                     "    constraint key_itemeffects_item"
                     "        foreign key (itemId) references items (id),"
                     "    constraint key_itemeffects_effects"
                     "        foreign key (effectId) references effects (id)"
                     ");")
    else:
        conn.execute("create table if not exists item_effects("
                     "    itemId    INTEGER           not null,"
                     "    effectId  INTEGER           not null,"
                     "    isDefault INTEGER default 0 not null,"
                     "    primary key (itemId, effectId)"
                     ");")
    conn.execute("create table if not exists modifier_definition("
                 "    code                   TEXT    not null primary key,"
                 "    changeTypes            TEXT    not null,"
                 "    attributeOnly          INTEGER not null,"
                 "    changeRanges           TEXT    not null,"
                 "    changeRangeModuleNames TEXT    not null,"
                 "    attributeIds           TEXT    not null"
                 ");")
    if not sweet_compatible:
        conn.execute("create table if not exists modifier_value("
                     "    code       TEXT not null primary key,"
                     "    attributes TEXT not null,"
                     "    typeName   TEXT not null,"
                     "    constraint key_modifiervalue_modifierdef"
                     "        foreign key (typeName) references modifier_definition (code)"
                     ");")
    else:
        conn.execute("create table if not exists modifier_value("
                     "    code       TEXT not null primary key,"
                     "    attributes TEXT not null,"
                     "    typeName   TEXT not null"
                     ");")
    if not sweet_compatible:
        # ToDo: Improve and populate item_modifiers
        conn.execute("create table if not exists item_modifiers("
                     "    code                    TEXT    not null,"
                     "    typeCode                TEXT    not null,"
                     "    changeType              TEXT    not null,"
                     "    attributeOnly           INTEGER not null,"
                     "    changeRange             TEXT    not null,"
                     "    changeRangeModuleNameId INTEGER not null,"
                     "    attributeId             INTEGER not null,"
                     "    attributeValue          REAL"
                     ");")
    else:
        conn.execute("create table if not exists item_modifiers("
                     "    code                    TEXT    not null,"
                     "    typeCode                TEXT    not null,"
                     "    changeType              TEXT    not null,"
                     "    attributeOnly           INTEGER not null,"
                     "    changeRange             TEXT    not null,"
                     "    changeRangeModuleNameId INTEGER not null,"
                     "    attributeId             INTEGER not null,"
                     "    attributeValue          REAL"
                     ");")
    conn.execute("create table if not exists repackage_volume("
                 "    group_id INTEGER null unique,"
                 "    type_id  INTEGER null unique,"
                 "    volume   REAL    not null,"
                 "    constraint key_repack_group"
                 "        foreign key (group_id) references groups (id),"
                 "    constraint key_repack_type"
                 "        foreign key (type_id) references types (id))")
    conn.execute("create table if not exists reprocess("
                 "    itemId   INTEGER not null,"
                 "    resultId INTEGER not null,"
                 "    quantity INTEGER not null,"
                 "    primary key (itemId, resultId),"
                 "    constraint key_reprocess_item_base"
                 "        foreign key (itemId) references items (id),"
                 "    constraint key_reprocess_item_result"
                 "        foreign key (resultId) references items (id)"
                 ");")
    conn.execute("create table if not exists blueprints("
                 "   blueprintId       INTEGER not null primary key,"
                 "   productId         INTEGER not null UNIQUE,"
                 "   outputNum         INTEGER not null,"
                 "   skillLvl          INTEGER not null,"
                 "   materialAmendAtt  INTEGER not null,"
                 "   decryptorMul      INTEGER not null,"
                 "   money             INTEGER not null,"
                 "   time              INTEGER not null,"
                 "   timeAmendAtt      INTEGER not null,"
                 "   type              INTEGER not null, "
                 "    constraint key_blueprint_items_bp"
                 "        foreign key (blueprintId) references items (id),"
                 "    constraint key_blueprint_items_prod"
                 "        foreign key (productId) references items (id),"
                 "    constraint key_blueprint_attributes_mats"
                 "        foreign key (materialAmendAtt) references attributes (id),"
                 "    constraint key_blueprint_attributes_time"
                 "        foreign key (timeAmendAtt) references attributes (id)"
                 ");")
    conn.execute("create table if not exists blueprint_costs("
                 "    blueprintId INTEGER not null,"
                 "    resourceId  INTEGER not null,"
                 "    amount      INTEGER not null,"
                 "    type        TEXT CHECK(type in ('pi', 'mins', 'comp', 'mod', 'salv', 'ship')) null,"
                 "    primary key (blueprintId, resourceId),"
                 "    constraint key_blueprintcost_bp"
                 "        foreign key (blueprintId) references blueprints (blueprintId),"
                 "    constraint key_blueprintcost_bp"
                 "        foreign key (resourceId) references items (id)"
                 ");")
    conn.commit()


@deprecated(version="0.0.2-alpha", message="The table creation should happen via SQLAlchemy")
def setup_universe_tables(conn: Connection):
    conn.execute("create table if not exists regions ("
                 "    id         int    not null primary key,"
                 "    name       TEXT   not null,"
                 "    x          bigint null,"
                 "    y          bigint null,"
                 "    z          bigint null,"
                 "    faction_id int    null,"
                 "    radius     bigint null,"
                 "    wormhole_class_id int null"
                 ")")
    conn.execute("create table if not exists constellations("
                 "    id                int    not null primary key,"
                 "    region_id         int    null,"
                 "    name              TEXT   not null,"
                 "    x                 bigint null,"
                 "    y                 bigint null,"
                 "    z                 bigint null,"
                 "    faction_id        int    null,"
                 "    radius            bigint null,"
                 "    wormhole_class_id int    null,"
                 "    constraint key_const_reg"
                 "        foreign key (region_id) references regions (id)"
                 "            on delete cascade"
                 ")")
    conn.execute("create table if not exists solarsystems("
                 "    id               int    not null primary key,"
                 "    region_id        int    null,"
                 "    constellation_id int    null,"
                 "    name             TEXT   not null,"
                 "    x                bigint null,"
                 "    y                bigint null,"
                 "    z                bigint null,"
                 "    security         float  null,"
                 "    faction_id       int    null,"
                 "    radius           bigint null,"
                 "    constraint key_sys_const"
                 "        foreign key (constellation_id) references constellations (id)"
                 "            on delete cascade,"
                 "    constraint key_sys_reg"
                 "        foreign key (region_id) references regions (id))")

    conn.execute("create index if not exists ix_solarsystem_name"
                 "    on solarsystems (name);")

    conn.execute("create table if not exists system_connections("
                 "    origin_id      int not null,"
                 "    destination_id int not null,"
                 "    PRIMARY KEY (origin_id, destination_id), "
                 "    constraint key_sys_const"
                 "        foreign key (origin_id) references solarsystems (id)"
                 "            on delete cascade,"
                 "    constraint key_sys_const"
                 "       foreign key (destination_id) references solarsystems (id)"
                 "            on delete cascade)")
    conn.execute("create table if not exists celestials("
                 "    id              int auto_increment primary key,"
                 "    name            TEXT   not null,"
                 "    type_id         int    null,"
                 "    group_id        int    null,"
                 "    system_id       int    null,"
                 "    orbit_id        int    null,"
                 "    x               bigint null,"
                 "    y               bigint null,"
                 "    z               bigint null,"
                 "    radius          bigint null,"
                 "    security        float  null,"
                 "    celestial_index int    null,"
                 "    orbit_index     int    null,"
                 "    constraint key_celest_sys"
                 "        foreign key (system_id) references solarsystems (id)"
                 "            on delete cascade,"
                 "    constraint key_celest_celest"
                 "        foreign key (orbit_id) references celestials (id)"
                 "            on delete cascade)")
    conn.execute("create table if not exists planet_exploit("
                 "    planet_id      int    not null,"
                 "    type_id        bigint not null,"
                 "    output         float  not null,"
                 "    richness       text  CHECK(richness in ('poor', 'medium', 'rich', 'perfect')) not null,"
                 "    richness_value int    not null,"
                 "    location_index int    not null,"
                 "    primary key (planet_id, type_id),"
                 "    constraint key_planex_item"
                 "        foreign key (type_id) references items (id),"
                 "    constraint key_planex_planet"
                 "        foreign key (planet_id) references celestials (id)"
                 "            on delete cascade)")
    conn.commit()
