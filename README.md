# Eve Echoes Data Tools

![GitHub last commit (branch)](https://img.shields.io/github/last-commit/Blaumeise03/eve-echoes-data/master)
![GitHub tag (with filter)](https://img.shields.io/github/v/tag/Blaumeise03/eve-echoes-data?label=latest)
![GitHub forks](https://img.shields.io/github/forks/Blaumeise03/eve-echoes-data)
![GitHub Repo stars](https://img.shields.io/github/stars/Blaumeise03/eve-echoes-data)

This tool is designed to export static data from the game. This tool does NOT decompile/extract data from the APK. The
apk has to be already extracted/decompiled. To do so, use [xforce/eve-echoes-tools](https://github.com/xforce/eve-echoes-tools).
I will provide detailed instructions on how to install `eve-echoes-tools` in the future.

At the moment this tool is capable of exporting the following data (the data should be compatible with the S.W.E.E.T db
format, but is not completed/tested):
```
Items/module data:
    items (all items from the game)
    attributes, item_attributes, item_effects, item_nanocores, 
    effects,
    modifier_definition, modifier_value, item_modifiers
General data:
    unit (al units from the game, e.g. m/s, kg, ...)
    categories, groups, types
    localised_strings (translations)
Universe data:
    regions
    constellations
    solarsystems
    system_connections (does not include cobalt edge yet)
    celestials (only "normal" celestials; stargates & NPC stations WIP)
    plane_exploit (planetary production)
```

Instructions on how to use it will follow, for now just make sure you have the following directory structure:
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
```python
["lang", "items", "item_attrs", "base", "modifier", "universe", "planet_exploit"]
```
e.g.
```shell
python main.py -m items lang base universe planet_exploit
```