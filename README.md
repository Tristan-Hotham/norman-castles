# The Conquest in Castles

How fast did Norman castles spread across England and Wales (and into Scotland) after Hastings? Every castle site of Norman type in Wikidata, decade by decade from 1066, checked against the castles Domesday Book names in 1086.

**Interactive version:** https://tristan-hotham.github.io/norman-castles/

**Paper:** https://doi.org/10.5281/zenodo.23688584

This repository holds the interactive page, the datasets, the computed results and the analysis code for a data study by Dr Tristan Hotham (Independent researcher).

## Headline results

- Wikidata holds 3,288 castle sites of Norman type (castles, mottes, ringworks and keeps) in England, Wales and Scotland. Only 317 (10%) have any date, and 113 have a date from 1066 to 1199.
- The castle frontier leapt rather than crept. By 1069 the furthest dated castle (York Castle) was 354 km from Battle; by 1072, Durham Castle was 451 km away. Year and distance are barely related in England and Wales (Spearman 0.12, n = 106).
- The dated castles are a biased sample: 60% are Grade I listed against 6% of undated sites, and 15% are earthworks against 43%. They are not biased by distance from Battle (medians 282 and 293 km).
- Domesday Book's text names 41 castles. In 9 towns it records 395 houses destroyed, emptied or taken for castles, 166 of them at Lincoln.
- Domesday waste is regional: Cheshire (57% of places), Shropshire, Herefordshire and Yorkshire lead. Yorkshire's 1086 value was 39% of its 1066 value. Within counties, places near castles show only a small excess of waste (1.5 percentage points).
- A band 40 km either side of the England and Wales border holds 35% of the castle sites of the two countries on 15% of the land: 3.2 times the density of the rest.
- In the north-west the first dated castles are of the 1090s (Lancaster 1093), but Domesday already records a castle at Penwortham by 1086.

## Files

- `index.html`: the interactive page (Leaflet map with a decade slider and type filter, charts, tables). Data embedded.
- `header.png`: social card (1200 by 630).
- `data/castles.csv`: one row per Wikidata castle item (3,288), deduplicated, with type, classes, coordinates (WGS84 and British National Grid), county, nation, earliest inception year and all inception values, a round-year flag, heritage designations and the Wikidata link. Every date comes from Wikidata P571.
- `data/castles_dated.csv`: the 113 castles dated 1066 to 1199 with their distance from Battle.
- `data/decades.csv`: counts and distances by decade.
- `data/domesday_castles.csv`: the 41 castles named in the 1086 text, with the Domesday reference, the quoted sentence, location and how it was located, and the Wikidata match (if any).
- `data/domesday_castle_houses.csv`: houses lost to castles, with the words of the text.
- `data/domesday_places_waste.csv`: one row per located Domesday place (11,974), with waste entries and paired 1066 and 1086 values.
- `data/domesday_county_waste.csv`: waste share and value change by Domesday county.
- `data/county_density.csv` and `data/hexes.geojson`: castle sites per 1,000 km² of land by county and by hexagon (15 km centre to corner).
- `data/osm_castles.csv`: OpenStreetMap castle features used as a coverage check.
- `data/results.json`: every number quoted on the page, in the paper, the blog post and the collage.
- `code/01_extract.py`, `code/02_analyse.py`, `code/03_build_page.py` (fills `code/page_template.html`), `code/04_header.py`.
- `release/`: figures, paper source and build script, blog post, Zenodo files. `reddit/`: collage.

## How to rerun

The scripts read the shared inputs in place (paths at the top of `code/01_extract.py`): the Wikidata and OpenStreetMap bundle (retrieved 27 October 2026 via QLever), county boundaries built from ONS data, a clone of https://github.com/embabel-worlds/realm-domesday, and OS Open Names.

```
python3 code/01_extract.py
python3 code/02_analyse.py
python3 code/03_build_page.py
python3 code/04_header.py
python3 release/make_figures.py
python3 release/paper/build_paper.py
python3 reddit/collage.py
```

It needs Python 3 with pandas, numpy, scipy, shapely, pyproj, pyyaml and matplotlib, and xelatex for the paper.

## Method in brief and known limits

- Castle classes kept: castle, motte-and-bailey castle, motte, ringwork castle, shell keep, keep, castle ruin, enclosure castle, siege castle. Items with only later or non-Norman classes (tower house, fortified manor house, quadrangular castle, Welsh princes' castles and others) are left out; Northern Ireland is left out.
- Dates are never added by hand. Wikidata stores a year for dates of every precision, so years ending in 00 or 01 (17 of the 113 dated castles) may stand for a century; results are checked without them.
- The generic "castle" class includes later castles, and Scotland's items are mostly later tower castles, so Scotland is treated as context.
- Domesday castles were kept only where the translated 1086 text speaks of a castle at or of a place; entries flagged only because a modern name contains "Castle" were dropped. Wikidata matches need the same castle's name within 8 km; 6 ambiguous cases are left unmatched. Penwortham has no grid reference in the source and is placed at its Wikidata coordinates.
- Wikipedia could not be consulted from the build machine, so no Wikipedia dates are used.

## Sources and licences

- Wikidata (CC0), https://www.wikidata.org/
- OpenStreetMap contributors (ODbL), https://www.openstreetmap.org/copyright
- Domesday data: Hull Domesday Project, Professor J.J.N. Palmer, George Slater and the University of Hull (CC BY-NC-SA), https://digitalcollections.hull.ac.uk/collections/3t945r28b, via the realm-domesday repository by embabel-worlds, https://github.com/embabel-worlds/realm-domesday
- County boundaries: Office for National Statistics, Open Government Licence v3.0. Contains OS data © Crown copyright and database right.
- OS Open Names (Battle reference point): Contains OS data © Crown copyright and database right 2026 (OGL v3).
- Coastline in the static figures: Natural Earth (public domain).
- Base map tiles: © Esri, HERE, Garmin, © OpenStreetMap contributors, and the GIS user community.

Because the Domesday figures are CC BY-NC-SA, the derived data (`data/`) and the page text are released under CC BY-NC-SA 4.0 (https://creativecommons.org/licenses/by-nc-sa/4.0/); the OpenStreetMap extract stays under the ODbL. The code (`code/`, `release/`, `reddit/`) is released under the MIT licence (see `LICENSE`).

## Citation

Hotham, T. (2026). *The Conquest in Castles: Dating the Spread of Norman Castles across Britain, 1066 to 1199*. Zenodo. https://doi.org/10.5281/zenodo.23688584

Dr Tristan Hotham, Independent researcher, ORCID 0000-0003-4931-9349.

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
