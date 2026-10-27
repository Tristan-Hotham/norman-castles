"""Step 1. Extract castles, Domesday castle records and Domesday places.

Usage:
    python3 code/01_extract.py

Reads (in place, never copied):
  /home/claude/hist/_data8/uk_bundle_wikidata_osm.json   Wikidata (CC0) and OpenStreetMap (ODbL) bundle
  /home/claude/hist/how-roman-is-your-road/data/counties.geojson   county polygons (ONS, OGL v3)
  /home/claude/hist/realm-domesday/reference/*.yml        Hull Domesday Project data via realm-domesday (CC BY-NC-SA)
  /home/claude/hist/osnames_gb.tsv                        OS Open Names (OGL v3), for the Battle reference point

Writes:
  data/castles.csv            one row per Wikidata castle item in Great Britain (deduplicated by item)
  data/domesday_castles.csv   castles named in the 1086 text of Domesday Book (curated, with quotes)
  data/domesday_castle_houses.csv  houses the Domesday text says were destroyed or taken for castles
  data/domesday_places_waste.csv   one row per located Domesday place: waste flag and values 1066/1086
  data/osm_castles.csv        OpenStreetMap castle features used as a coverage check
  _work/counties_bng.json     county polygons in British National Grid (temporary, for step 2)
"""
import csv
import glob
import json
import os
import re
from collections import defaultdict

import yaml
from pyproj import Transformer
from shapely.geometry import Point, shape, mapping
from shapely.ops import transform
from shapely.strtree import STRtree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
WORK = os.path.join(ROOT, "_work")
os.makedirs(DATA, exist_ok=True)
os.makedirs(WORK, exist_ok=True)
BUNDLE = "/home/claude/hist/_data8/uk_bundle_wikidata_osm.json"
COUNTIES = "/home/claude/hist/how-roman-is-your-road/data/counties.geojson"
REF = "/home/claude/hist/realm-domesday/reference"
OSN = "/home/claude/hist/osnames_gb.tsv"

TO_BNG = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True).transform

# Classes that count as a castle of the Norman type for this study.
TYPE_OF = {
    "motte-and-bailey castle": "motte",
    "motte": "motte",
    "ringwork castle": "ringwork",
    "shell keep": "keep",
    "keep": "keep",
    "castle": "castle",
    "castle ruin": "castle",
    "enclosure castle": "castle",
    "siege castle": "castle",
}
# Later or non-Norman forms, kept out of the study set (recorded for transparency).
OTHER = {"tower house", "fortified manor house", "quadrangular castle", "Welsh princes' castles",
         "fortification", "L-plan castle", "Z-plan castle", "mock castle", "bridge castle",
         "castle chapel", "fortified house", "fortified tower", "milecastle"}

# ---------------- counties
cty = json.load(open(COUNTIES, encoding="utf-8"))
cgeo, cname, cnat = [], [], []
cbng = []
for f in cty["features"]:
    g = shape(f["geometry"])
    cgeo.append(g)
    cname.append(f["properties"]["county"])
    cnat.append(f["properties"]["nation"])
    cbng.append(transform(TO_BNG, g))
tree = STRtree(cgeo)


def county_of(lon, lat):
    p = Point(lon, lat)
    idx = tree.query(p)
    for i in idx:
        if cgeo[i].covers(p):
            return cname[i], cnat[i]
    # nearest within ~2 km for coastal points
    j = tree.nearest(p)
    if cgeo[j].distance(p) < 0.03:
        return cname[j], cnat[j]
    return "", ""


json.dump({"features": [{"county": cname[i], "nation": cnat[i], "geom": mapping(cbng[i].simplify(200))}
                        for i in range(len(cname))]}, open(os.path.join(WORK, "counties_bng.json"), "w"))

# ---------------- Wikidata castles
B = json.load(open(BUNDLE, encoding="utf-8"))
lines = B["wd_structures_tsv"].split("\n")
items = {}
for ln in lines[1:]:
    if not ln.strip():
        continue
    r = ln.split("\t")
    while len(r) < 7:
        r.append("")
    q = r[0].rsplit("/", 1)[-1].rstrip(">")
    cl = r[3].split('"')[1] if '"' in r[3] else r[3]
    it = items.setdefault(q, {"label": "", "cls": set(), "coord": r[4], "inc": set(), "her": set()})
    if r[1] and not it["label"]:
        it["label"] = r[1].rsplit("@", 1)[0].strip('"')
    it["cls"].add(cl)
    m = re.match(r"(-?\d{1,4})-\d\d-\d\dT", r[5])
    if m:
        it["inc"].add(int(m.group(1)))
    if r[6]:
        it["her"].add(r[6].rsplit("/", 1)[-1].rstrip(">"))

HER = {"Q219538": "scheduled", "Q15700818": "grade1", "Q15700831": "grade2s", "Q15700834": "grade2"}
rows = []
for q, it in items.items():
    types = [TYPE_OF[c] for c in it["cls"] if c in TYPE_OF]
    if not types:
        continue
    m = re.match(r"POINT\(([-\d.]+) ([-\d.]+)\)", it["coord"])
    if not m:
        continue
    lon, lat = float(m.group(1)), float(m.group(2))
    county, nation = county_of(lon, lat)
    if nation not in ("England", "Wales", "Scotland"):
        continue  # Northern Ireland and points outside the polygons are left out
    # one type per item: the most specific earthwork form wins
    t = "motte" if "motte" in types else "ringwork" if "ringwork" in types else "keep" if "keep" in types else "castle"
    x, y = TO_BNG(lon, lat)
    year = min(it["inc"]) if it["inc"] else None
    rows.append({
        "qid": q, "label": it["label"] or q, "type": t,
        "classes": "; ".join(sorted(it["cls"])),
        "also_later_class": int(bool(it["cls"] & OTHER)),
        "lon": round(lon, 5), "lat": round(lat, 5), "x": round(x), "y": round(y),
        "county": county, "nation": nation,
        "inception_year": year if year is not None else "",
        "inception_all": "; ".join(str(v) for v in sorted(it["inc"])),
        "round_year": int(year is not None and year % 100 in (0, 1)),
        "scheduled": int("Q219538" in it["her"]),
        "grade1": int("Q15700818" in it["her"]),
        "listed_any": int(bool(it["her"] & {"Q15700818", "Q15700831", "Q15700834"})),
        "wikidata": f"https://www.wikidata.org/wiki/{q}",
        "date_source": "Wikidata P571 (inception)" if year is not None else "",
    })
rows.sort(key=lambda r: (r["nation"], r["county"], r["label"]))
with open(os.path.join(DATA, "castles.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print("castles", len(rows), "dated", sum(1 for r in rows if r["inception_year"] != ""))

# ---------------- Domesday entries and places
places = {}
for path in sorted(glob.glob(os.path.join(REF, "03-places-*.yml"))):
    for d in yaml.load(open(path, encoding="utf-8"), Loader=yaml.CSafeLoader) or []:
        p = d["data"]
        places[str(p["placeId"])] = p
agg = defaultdict(lambda: {"entries": 0, "waste": 0, "v66": 0.0, "v86": 0.0, "nv": 0, "hh": 0.0})
entries = []
for path in sorted(glob.glob(os.path.join(REF, "05-entries-*.yml"))):
    for e in yaml.load(open(path, encoding="utf-8"), Loader=yaml.CSafeLoader) or []:
        d = e["data"]
        desc = [str(r["to"]["placeId"]) for r in e.get("relations", []) if r["predicate"] == "DESCRIBES"]
        entries.append((d, desc))
        k = len(desc)
        for pid in desc:
            a = agg[pid]
            a["entries"] += 1
            if d.get("isWaste"):
                a["waste"] += 1
            if d.get("households") is not None:
                a["hh"] += float(d["households"]) / k
            if d.get("value1066") is not None and d.get("value1086") is not None:
                a["v66"] += float(d["value1066"]) / k
                a["v86"] += float(d["value1086"]) / k
                a["nv"] += 1
prow = []
for pid, p in places.items():
    if p.get("lat") is None or pid not in agg:
        continue
    a = agg[pid]
    x, y = TO_BNG(p["lng"], p["lat"])
    prow.append({"placeId": pid, "name": p.get("name"), "county": p.get("county"), "countyName": p.get("countyName"),
                 "lat": p["lat"], "lng": p["lng"], "x": round(x), "y": round(y), "entries": a["entries"],
                 "waste_entries": a["waste"], "any_waste": int(a["waste"] > 0),
                 "households1086": round(a["hh"], 2),
                 "value1066_paired": round(a["v66"], 1) if a["nv"] else "",
                 "value1086_paired": round(a["v86"], 1) if a["nv"] else "",
                 "openDomesdayPath": p.get("openDomesdayPath") or ""})
with open(os.path.join(DATA, "domesday_places_waste.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(prow[0].keys()))
    w.writeheader()
    w.writerows(prow)
print("domesday places", len(prow))

# ---------------- Castles named in the Domesday text (curated by entry reference)
# Each row: entry ref, castle name as used here, how the castle is placed. Only entries whose 1086 text
# (English translation in the source) speaks of a castle at or of a place are kept. Entries flagged only
# because a modern place name contains "Castle" (e.g. [Castle] Hedingham) are left out, as are entries that
# mention a castle somewhere else (the castle of Lewes in Norfolk entries, castle wardens in Sussex).
DC = [
    ("Berkshire B1", "Wallingford", None),
    ("Berkshire 49,1", "Windsor", None),
    ("Cambridgeshire B1", "Cambridge", None),
    ("Cheshire FT2,19", "Rhuddlan", None),
    ("Cheshire R6,5", "Penwortham", "WD:Q7165387"),
    ("Cornwall 5,1,22", "Launceston", None),
    ("Cornwall 5,2,11", "Trematon", None),
    ("Derbyshire 7,7", "Peveril (Castleton)", None),
    ("Devon 16,3", "Okehampton", None),
    ("Dorset 19,10", "Wareham Castle (Kingston entry)", None),
    ("Essex 24,17", "Rayleigh", None),
    ("Gloucestershire G4", "Gloucester", None),
    ("Gloucestershire S1", "Chepstow", None),
    ("Gloucestershire 1,19", "Small castle (Berkeley, Sharpness entry)", None),
    ("Hampshire IoW1,15", "Castle at Alvington, Isle of Wight", None),
    ("Herefordshire 9,1", "Wigmore", "70331"),
    ("Herefordshire 1,48", "Monmouth", None),
    ("Herefordshire 8,1", "Clifford", None),
    ("Herefordshire 12,2", "Richard's Castle", None),
    ("Herefordshire 19,1", "Ewyas Harold", "23921"),
    ("Herefordshire 14,1", "Caerleon (castlery)", None),
    ("Huntingdonshire B6", "Huntingdon", None),
    ("Kent C1", "Canterbury", None),
    ("Lincolnshire C26", "Lincoln", None),
    ("Lincolnshire S2", "Stamford", None),
    ("Norfolk 1,61", "Norwich", None),
    ("Northamptonshire 1,27", "Rockingham", None),
    ("Shropshire C14", "Shrewsbury", None),
    ("Shropshire 4,1,11", "Oswestry (Maesbury entry)", None),
    ("Shropshire 4,1,35", "Montgomery", None),
    ("Shropshire 4,21,6", "Holdgate", None),
    ("Somerset 19,86", "Montacute (Bishopstone entry)", None),
    ("Somerset 25,2", "Dunster", None),
    ("Staffordshire 10,1", "Tutbury", None),
    ("Staffordshire 10,2", "Burtone", None),
    ("Staffordshire 10,9", "Stafford (Chebsey entry, castle destroyed by 1086)", "STAFFORD"),
    ("Suffolk 18,1", "Eye", "EYE"),
    ("Sussex 9,11", "Hastings (castlery)", "HASTINGS"),
    ("Sussex 11,2", "Arundel", None),
    ("Sussex 13,9", "Bramber (Washington entry)", None),
    ("Warwickshire B2", "Warwick", None),
    ("Worcestershire 23,10", "Dudley", None),
]
byref = {d["ref"]: (d, desc) for d, desc in entries}
byname = defaultdict(list)
for pid, p in places.items():
    byname[(p.get("name"), p.get("county"))].append(pid)
special = {"STAFFORD": ("Stafford", "STS"), "EYE": ("Eye", "SUF"), "HASTINGS": ("Hastings", "SUS")}
drows = []
for ref, nm, pick in DC:
    d, desc = byref[ref]
    t = d.get("text") or ""
    sents = [s for s in re.split(r"(?<=[.;])\s+", t) if re.search("castl", s, re.I)]
    quote = " ".join(sents)[:400]
    if pick in special:
        cand = byname.get(special[pick], [])
        pid = cand[0] if cand else None
    elif pick:
        pid = pick
    else:
        pid = desc[0] if desc else None
    p = places.get(pid) if pid else None
    locsrc = "Domesday place grid reference (realm-domesday / Hull Domesday Project)"
    if pick and pick.startswith("WD:"):
        # the Domesday place has no grid reference in the source; use the castle's Wikidata coordinates
        q = pick[3:]
        m = re.match(r"POINT\(([-\d.]+) ([-\d.]+)\)", items[q]["coord"])
        p = dict(places[desc[0]], lng=float(m.group(1)), lat=float(m.group(2)))
        pid = desc[0]
        locsrc = f"Wikidata {q} coordinates (the Domesday place has no grid reference in the source)"
    if not p or p.get("lat") is None:
        print("  not located:", ref, nm)
        continue
    x, y = TO_BNG(p["lng"], p["lat"])
    drows.append({"castle": nm, "domesday_ref": ref, "domesday_place": p.get("name"), "placeId": pid,
                  "county": d.get("countyName"), "lat": p["lat"], "lng": p["lng"], "x": round(x), "y": round(y),
                  "entry_waste": int(bool(d.get("isWaste"))), "quote": quote,
                  "location_source": locsrc,
                  "open_domesday": f"https://opendomesday.org/place/{p.get('openDomesdayPath')}/" if p.get("openDomesdayPath") else ""})
with open(os.path.join(DATA, "domesday_castles.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(drows[0].keys()))
    w.writeheader()
    w.writerows(drows)
print("domesday castles", len(drows))

# Houses destroyed or taken for castles, as the Domesday text states them (numbers read from the quoted sentence).
HOUSES = [
    ("Lincolnshire C26", "Lincoln", 166, "166 were destroyed because of the castle"),
    ("Norfolk 1,61", "Norwich", 98, "17 empty messuages which are in the occupation of the castle premises; 81 in the occupation of the castle"),
    ("Shropshire C14", "Shrewsbury", 51, "the Earl's castle has taken over 51 messuages"),
    ("Cambridgeshire B1", "Cambridge", 27, "27 houses have been destroyed for the castle"),
    ("Huntingdonshire B6", "Huntingdon", 20, "On the castle site there were 20 messuages"),
    ("Gloucestershire G4", "Gloucester", 16, "Where the castle is sited there were 16 houses which do not exist now"),
    ("Berkshire B1", "Wallingford", 8, "8 were destroyed for the castle"),
    ("Lincolnshire S2", "Stamford", 5, "5 which are unoccupied because of the construction of the castle"),
    ("Warwickshire B2", "Warwick", 4, "4 are waste, because of the castle site"),
]
with open(os.path.join(DATA, "domesday_castle_houses.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["domesday_ref", "town", "houses", "words_in_text", "full_sentence"])
    for ref, town, n, words in HOUSES:
        d, _ = byref[ref]
        t = d.get("text") or ""
        assert words.split(";")[0][:25] in t, (ref, words)
        sents = [s for s in re.split(r"(?<=[.;])\s+", t) if re.search("castl", s, re.I)]
        w.writerow([ref, town, n, words, " ".join(sents)[:500]])

# ---------------- OSM castles (coverage check)
orows = []
for o in B["osm_uk_features"]:
    if not (o["kind"] == "castle_type" or (o["kind"] == "historic" and o["hist"] in ("castle", "motte", "ringwork"))):
        continue
    county, nation = county_of(o["lon"], o["lat"])
    if nation not in ("England", "Wales", "Scotland"):
        continue
    x, y = TO_BNG(o["lon"], o["lat"])
    orows.append({"osm": o["osm"], "kind": o["kind"], "historic": o["hist"], "name": o["name"], "lon": o["lon"],
                  "lat": o["lat"], "x": round(x), "y": round(y), "wikidata": o["wd"], "county": county, "nation": nation})
seen = set()
orows = [r for r in orows if not (r["osm"] in seen or seen.add(r["osm"]))]
with open(os.path.join(DATA, "osm_castles.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(orows[0].keys()))
    w.writeheader()
    w.writerows(orows)
print("osm castles", len(orows))

# ---------------- reference point: Battle (site of the battle of Hastings), from OS Open Names
with open(OSN, encoding="utf-8") as f:
    for ln in f:
        c = ln.rstrip("\n").split("\t")
        if c[0] == "Battle" and c[5] == "Town" and c[12] == "East Sussex":
            json.dump({"name": "Battle, East Sussex", "lat": float(c[6]), "lon": float(c[7]), "x": float(c[8]), "y": float(c[9]),
                       "source": "OS Open Names, populated place 'Battle' (Town, East Sussex)"},
                      open(os.path.join(WORK, "battle.json"), "w"))
            print("Battle", c[6], c[7])
            break
