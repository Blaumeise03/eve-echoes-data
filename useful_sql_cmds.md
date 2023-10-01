# Useful SQL commands

## Planetary production export
This command exports the planetary production in a similar format to the Google sheets document that was published after
the launch of the game.
```sqlite
SELECT
    c.id as 'Planet ID',
    r.name as Region,
    const.name as Constellation,
    s.name as System,
    c.name as "Planet Name",
    loc.en as Resource,
    pe.richness as Richness,
    pe.output as Output
FROM solarsystems as s
    JOIN main.celestials c on s.id = c.system_id
    JOIN main.planet_exploit pe on c.id = pe.planet_id
    JOIN main.items i on i.id = pe.type_id
    JOIN main.localised_strings loc on i.nameKey = loc.id
    JOIN main.constellations const on const.id = s.constellation_id
    JOIN main.regions r on r.id = s.region_id;
```