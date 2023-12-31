Eve Echoes Data Tools
=====================

![GitHub last commit (branch)](https://img.shields.io/github/last-commit/Blaumeise03/eve-echoes-data/master)
![GitHub tag (with filter)](https://img.shields.io/github/v/tag/Blaumeise03/eve-echoes-data?label=latest)
![GitHub forks](https://img.shields.io/github/forks/Blaumeise03/eve-echoes-data)
![GitHub Repo stars](https://img.shields.io/github/stars/Blaumeise03/eve-echoes-data)

This tool is designed to export static data from the game. This tool does NOT decompile/extract data from the APK. The
apk has to be already extracted/decompiled. To do so, use [xforce/eve-echoes-tools](https://github.com/xforce/eve-echoes-tools).
The data gets exported into a sqlite3 database called `echoes.db`.

> At the moment of writing, `xforce/eve-echoes-tools` is broken. Please use my forks of [eve-echoes-tools](https://github.com/blaumeise03/eve-echoes-tools)
> **AND** [neox-tools](https://github.com/blaumeise03/neox-tools) (it is crucial to use the lates version of neox-tools, the old one is broken).
>
> The `eve-echoes-tools` also contains detailed installation and usage instruction.

At the moment this tool is capable of exporting the following data (the data should be compatible with the SWEET db
format, but is not completed/tested at the moment):
```
Items/module data:
    items (all items from the game)
    attributes, item_attributes, item_effects, item_nanocores, 
    effects,
    modifier_definition, modifier_value, item_modifiers,
    blueprints, blueprint_cost
General data:
    unit (al units from the game, e.g. m/s, kg, ...)
    categories, groups, types
    localised_strings (translations)
Universe data:
    regions
    constellations
    solarsystems
    system_connections
    celestials (only "normal" celestials and stargates;  NPC stations are WIP)
    plane_exploit (planetary production)
```

Instructions on how to use it will follow, for now just make sure you have the following directory structure
> Copy the required files/directory or the whole `staticdata` directory from `eve-echoes-tools`
```
eve-echoes-data/ (this folder name doesn't matter)
    main.py and other stuff from this repo
    staticdata/
        manual_static_data/universe/planet_exploit_resource.json
        py_data/
            data_common/*
        script/data_common/static/item/item_type.py
        sigmadata/eve/universe/*
        staticdata/
            gettext/*
            items/*
            dogma/*
```
Please launch the script with `python main.py -m <one or more modes>`, these are the available modes:
```
lang:   Loads language files
base:   Loads basic stuff like groups and categories
attrs:  Loads attributes
items:  Loads items
item_extra: Loads extra data for items, like reprocessing data and repackaging volume
bps:        Loads manufacturing blueprints (Reverse Engineerin BPs are WIP)
item_attrs: Loads attributes of items
modifier:   Loads modifier data
universe:   Loads universe data (regions, systems,...)
cobalt:     Initilaizes the system connections in Cobalt Edge
planet_exploit: Loads planetary production data
```
e.g.
```shell
python extract_data.py -m items lang base universe planet_exploit
```
This will export the data into a sqlite3 database by default. You can specify another database via the `-db <url>` and
`--dialect <sqlite|mysql>` argument. For example:
```shell
python extract_data.py -db "mariadb+mariadbconnector://user:password@localhost:3306/database" --dialect mysql

python extract_data.py -db "sqlite+pysqlite:///echoes.db" --dialect sqlite
```
Please make sure to install the required dependencies for your database, e.g. `mariadb` if you want to use a MariaDB
database.
You can also force the database to get dropped before reloading, to ensure that no wrong data gets persisted. To do
so, append the `--drop` parameter.

You can find useful SQL commands in [useful_sql_cmds.md](useful_sql_cmds.md).

## Command Line Interface
There is also a WIP CLI, that can get used to access the data, e.g:
```shell
python data_cli.py -db "sqlite+pysqlite:///echoes.db" --dialect sqlite
```
