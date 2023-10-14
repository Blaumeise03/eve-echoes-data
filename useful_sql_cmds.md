# Useful SQL commands

## Planetary production export
This command exports the planetary production in a similar format to the Google sheets document that was published after
the launch of the game.
```mysql
SELECT
    c.id as 'Planet ID',
    r.name as Region,
    const.name as Constellation,
    s.name as "System",
    c.name as "Planet Name",
    loc.en as Resource,
    pe.richness as Richness,
    pe.output as Output
FROM solarsystems as s
    JOIN celestials c on s.id = c.system_id
    JOIN planet_exploit pe on c.id = pe.planet_id
    JOIN items i on i.id = pe.type_id
    JOIN localised_strings loc on i.nameKey = loc.id
    JOIN constellations const on const.id = s.constellation_id
    JOIN regions r on r.id = s.region_id;
```

## Corp Tech
Extract the available corp techs with fp & isk-costs
```mysql
SELECT n.en as "name", t.corp_lv_require, ctl.tech_lvl, ctl.fp_require, ctl.isk_require
FROM corp_tech as t
JOIN localised_strings n on t.name_key = n.id
JOIN localised_strings d on t.desc_key = d.id
JOIN corp_tech_level ctl on t.id = ctl.tech_id
ORDER BY t.corp_lv_require, n.en, ctl.tech_lvl;
```
Extract all concord supplies items with their fp reward
```mysql
SELECT i.name, t.fpReward
FROM corp_task_items as t
JOIN items i on i.id = t.itemId
ORDER BY i.name;
```