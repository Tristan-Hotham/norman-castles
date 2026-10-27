"""Step 2. Analyse the castles and write data/results.json plus the compact page data.

Usage:
    python3 code/02_analyse.py

Reads the files written by step 1 and writes:
  data/results.json          every number used in the page, paper, blog and collage
  data/castles_dated.csv     the dated castles 1066 to 1199 used for the time series, with distance from Battle
  data/decades.csv           per-decade counts and distances
  data/county_density.csv    castles per 1,000 km2 by county
  data/hexes.geojson         hexagon density grid (lon/lat), castles and earthwork castles per 1,000 km2 of land
  data/domesday_county_waste.csv  waste share and value change by Domesday county
  _work/site.json            compact data for the page (temporary; embedded by step 3)
"""
import csv
import json
import math
import os
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy import stats
from shapely.geometry import Point, Polygon, shape
from shapely.ops import unary_union
from shapely.strtree import STRtree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
WORK = os.path.join(ROOT, "_work")
TO_LL = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True).transform

R = {}
c = pd.read_csv(os.path.join(DATA, "castles.csv"))
B = json.load(open(os.path.join(WORK, "battle.json")))
R["battle"] = {"lat": B["lat"], "lon": B["lon"], "source": B["source"]}
c["dist_km"] = np.hypot(c.x - B["x"], c.y - B["y"]) / 1000.0
c["dated"] = c.inception_year.notna()
ew = c[c.nation.isin(["England", "Wales"])]

# ---------------- counts
R["n_items"] = int(len(c))
R["n_by_nation"] = {k: int(v) for k, v in c.nation.value_counts().items()}
R["n_by_type"] = {k: int(v) for k, v in c.type.value_counts().items()}
R["also_later_class_n"] = int(c.also_later_class.sum())
R["n_earthwork"] = int(c.type.isin(["motte", "ringwork"]).sum())
R["n_dated_any"] = int(c.dated.sum())
R["share_dated_any"] = float(c.dated.mean())
R["n_undated"] = int((~c.dated).sum())
R["share_undated"] = float((~c.dated).mean())
R["dated_share_by_type"] = {t: float(c[c.type == t].dated.mean()) for t in ["castle", "motte", "ringwork", "keep"]}
R["dated_n_by_type"] = {t: int(c[c.type == t].dated.sum()) for t in ["castle", "motte", "ringwork", "keep"]}
R["earthwork_dated_n"] = int(c[c.type.isin(["motte", "ringwork"])].dated.sum())
R["earthwork_dated_share"] = float(c[c.type.isin(["motte", "ringwork"])].dated.mean())
pre = c[c.dated & (c.inception_year < 1066)].sort_values("inception_year")
R["n_pre1066"] = int(len(pre))
R["pre1066"] = [{"label": r.label, "year": int(r.inception_year), "county": r.county} for r in pre.itertuples()]
R["n_after1199"] = int((c.dated & (c.inception_year > 1199)).sum())

# ---------------- the dated sample, 1066 to 1199
W = c[c.dated & (c.inception_year >= 1066) & (c.inception_year <= 1199)].copy()
W["year"] = W.inception_year.astype(int)
W["decade"] = (W.year // 10) * 10
W.sort_values(["year", "label"]).to_csv(os.path.join(DATA, "castles_dated.csv"), index=False,
                                         columns=["qid", "label", "type", "year", "round_year", "inception_all", "county", "nation",
                                                  "lat", "lon", "dist_km", "grade1", "scheduled", "wikidata", "date_source"], float_format="%.2f")
R["n_window"] = int(len(W))
R["window_by_nation"] = {k: int(v) for k, v in W.nation.value_counts().items()}
R["window_by_type"] = {k: int(v) for k, v in W.type.value_counts().items()}
R["window_round"] = int(W.round_year.sum())
R["window_round_share"] = float(W.round_year.mean())
R["window_year1100"] = int((W.year == 1100).sum())
R["window_1066_1086"] = int((W.year <= 1086).sum())
R["window_1066_1071"] = int((W.year <= 1071).sum())
R["window_1066_1069"] = int((W.year <= 1069).sum())
R["window_by_1086_share"] = float((W.year <= 1086).mean())
R["window_median_year"] = float(W.year.median())

dec = []
for d in range(1060, 1200, 10):
    s = W[W.decade == d]
    cum = W[W.year < d + 10]
    dec.append({"decade": d, "n": int(len(s)), "n_round": int(s.round_year.sum()),
                "median_km": float(s.dist_km.median()) if len(s) else None,
                "max_km": float(s.dist_km.max()) if len(s) else None,
                "cum_n": int(len(cum)), "cum_p90_km": float(cum.dist_km.quantile(.9)) if len(cum) else None,
                "cum_max_km": float(cum.dist_km.max()) if len(cum) else None,
                "median_north_km": float(s.y.median() / 1000) if len(s) else None})
R["decades"] = dec
pd.DataFrame(dec).to_csv(os.path.join(DATA, "decades.csv"), index=False, float_format="%.1f")
R["decade_peak"] = max(dec, key=lambda r: r["n"])
R["decade_1060s"] = dec[0]

# speed of the frontier: furthest dated castle by given years
def furthest_by(y, sub=W):
    s = sub[sub.year <= y]
    r = s.loc[s.dist_km.idxmax()]
    return {"year": int(y), "label": r.label, "built": int(r.year), "km": float(r.dist_km), "county": r.county, "n": int(len(s))}
R["furthest_by_1069"] = furthest_by(1069)
R["furthest_by_1072"] = furthest_by(1072)
R["furthest_by_1072_ew"] = furthest_by(1072, W[W.nation != "Scotland"])
R["furthest_by_1086_ew"] = furthest_by(1086, W[W.nation != "Scotland"])
R["furthest_by_1100_ew"] = furthest_by(1100, W[W.nation != "Scotland"])
Wew = W[W.nation != "Scotland"]
R["n_window_ew"] = int(len(Wew))
for lo, hi, key in [(1066, 1071, "p1066_1071"), (1072, 1086, "p1072_1086"), (1087, 1135, "p1087_1135"), (1136, 1199, "p1136_1199")]:
    s = Wew[(Wew.year >= lo) & (Wew.year <= hi)]
    R[key] = {"n": int(len(s)), "median_km": float(s.dist_km.median()), "p90_km": float(s.dist_km.quantile(.9)),
              "share_over_300": float((s.dist_km > 300).mean())}
rho, p = stats.spearmanr(Wew.year, Wew.dist_km)
R["spearman_year_dist_ew"] = {"rho": float(rho), "p": float(p), "n": int(len(Wew))}
sl = stats.linregress(Wew.year, Wew.dist_km)
R["slope_km_per_decade_ew"] = float(sl.slope * 10)
nr = Wew[Wew.round_year == 0]
rho2, p2 = stats.spearmanr(nr.year, nr.dist_km)
R["spearman_year_dist_ew_noround"] = {"rho": float(rho2), "p": float(p2), "n": int(len(nr))}
# share of first-five-year castles already more than 300 km from Battle
R["first_years_over_300"] = int((Wew[Wew.year <= 1072].dist_km > 300).sum())
R["first_years_n"] = int((Wew.year <= 1072).sum())

# ---------------- Domesday castles and their match to Wikidata
dc = pd.read_csv(os.path.join(DATA, "domesday_castles.csv"))
R["n_domesday_castles"] = int(len(dc))
R["n_domesday_castle_waste_entry"] = int(dc.entry_waste.sum())
# Match each Domesday castle to a Wikidata item only when the item's label names the same castle and lies
# within 8 km of the Domesday place. Ambiguous cases (Wareham/Corfe, the Berkeley "small castle", Alvington,
# Canterbury, Oswestry, the destroyed Stafford castle) are deliberately left unmatched.
WD_LABEL = {"Wallingford": "Wallingford Castle", "Windsor": "Windsor Castle", "Cambridge": "Cambridge Castle",
            "Rhuddlan": "Twtil, Castle Motte", "Penwortham": "Penwortham Castle", "Launceston": "Launceston Castle",
            "Trematon": "Trematon Castle", "Peveril (Castleton)": "Peveril Castle", "Okehampton": "Okehampton Castle",
            "Rayleigh": "Rayleigh Castle", "Gloucester": "Gloucester Castle", "Chepstow": "Chepstow Castle",
            "Wigmore": "Wigmore Castle", "Monmouth": "Monmouth Castle", "Clifford": "Clifford Castle and Barbican",
            "Richard's Castle": "Richard's Castle", "Ewyas Harold": "Ewyas Harold Castle", "Caerleon (castlery)": "Caerleon Castle",
            "Huntingdon": "Huntingdon Castle", "Lincoln": "Lincoln Castle", "Stamford": "Stamford Castle", "Norwich": "Norwich Castle",
            "Rockingham": "Rockingham Castle", "Shrewsbury": "Shrewsbury Castle", "Montgomery": "Hen Domen", "Holdgate": "Holdgate Castle",
            "Montacute (Bishopstone entry)": "Montacute Castle", "Dunster": "Dunster Castle", "Tutbury": "Tutbury Castle",
            "Eye": "Eye Castle", "Hastings (castlery)": "Hastings Castle", "Arundel": "Arundel Castle",
            "Bramber (Washington entry)": "Bramber Castle", "Warwick": "Warwick Castle", "Dudley": "Dudley Castle"}
match = []
for r in dc.itertuples():
    lab = WD_LABEL.get(r.castle)
    s = c[c.label == lab] if lab else c.iloc[0:0]
    s = s.assign(km=np.hypot(s.x - r.x, s.y - r.y) / 1000)
    s = s[s.km <= 8].sort_values("km")
    if len(s):
        j = s.iloc[0]
        match.append({"castle": r.castle, "dist_km": float(j.km), "qid": j.qid, "wd_label": j.label,
                      "wd_year": None if pd.isna(j.inception_year) else int(j.inception_year)})
    else:
        match.append({"castle": r.castle, "dist_km": None, "qid": "", "wd_label": "", "wd_year": None})
mt = pd.DataFrame(match)
dc["wd_qid"] = mt.qid
dc["wd_label"] = mt.wd_label
dc["wd_year"] = mt.wd_year
dc["wd_dist_km"] = mt.dist_km.astype(float).round(2)
dc.to_csv(os.path.join(DATA, "domesday_castles.csv"), index=False)
R["dc_matched"] = int((mt.qid != "").sum())
R["dc_matched_dated"] = int(mt.wd_year.notna().sum())
R["dc_matched_undated"] = int(((mt.qid != "") & mt.wd_year.isna()).sum())
R["dc_matched_after1086"] = int((mt.wd_year > 1086).sum())
R["dc_matched_before1066"] = [{"castle": r.castle, "wd_year": int(r.wd_year)} for r in mt[mt.wd_year < 1066].itertuples()]
R["dc_matched_before1066_n"] = len(R["dc_matched_before1066"])
R["dc_unmatched"] = int((mt.qid == "").sum())
R["dc_after1086_list"] = [{"castle": r.castle, "wd_label": r.wd_label, "wd_year": int(r.wd_year)} for r in mt[mt.wd_year > 1086].itertuples()]
R["dc_undated_examples"] = [r.wd_label for r in mt[(mt.qid != "") & mt.wd_year.isna()].itertuples()]
c["domesday"] = c.qid.isin(set(mt.qid[mt.qid != ""]))
# combined "known by 1086" set: Wikidata dated 1066 to 1086 plus Domesday-attested
known86 = set(W[W.year <= 1086].qid) | set(mt.qid[mt.qid != ""])
R["known_by_1086_items"] = int(len(known86))
R["known_by_1086_total"] = int(len(known86) + (mt.qid == "").sum())

houses = pd.read_csv(os.path.join(DATA, "domesday_castle_houses.csv"))
R["houses_total"] = int(houses.houses.sum())
R["houses_towns"] = int(len(houses))
R["houses"] = [{"town": r.town, "n": int(r.houses)} for r in houses.itertuples()]

# ---------------- is the dated sample biased? (England and Wales)
def share(s, col):
    return float(s[col].mean())
ewd, ewu = ew[ew.dated], ew[~ew.dated]
ew = ew.assign(earth=ew.type.isin(["motte", "ringwork"]).astype(int), dom=c.loc[ew.index, "domesday"].astype(int))
ewd, ewu = ew[ew.dated], ew[~ew.dated]
bias = {}
for col, lab in [("earth", "earthwork (motte or ringwork)"), ("grade1", "Grade I listed"), ("listed_any", "listed building (any grade)"),
                 ("scheduled", "scheduled monument"), ("dom", "named in Domesday")]:
    a, b_ = int(ewd[col].sum()), int(ewu[col].sum())
    tab = [[a, len(ewd) - a], [b_, len(ewu) - b_]]
    chi = stats.chi2_contingency(tab)
    bias[col] = {"label": lab, "dated": float(ewd[col].mean()), "undated": float(ewu[col].mean()),
                 "dated_n": a, "undated_n": b_, "p": float(chi[1])}
R["bias"] = bias
R["bias_n_dated"] = int(len(ewd))
R["bias_n_undated"] = int(len(ewu))
R["bias_dist_median_dated"] = float(ewd.dist_km.median())
R["bias_dist_median_undated"] = float(ewu.dist_km.median())
R["bias_dist_mwu_p"] = float(stats.mannwhitneyu(ewd.dist_km, ewu.dist_km).pvalue)
R["bias_grade1_ratio"] = bias["grade1"]["dated"] / bias["grade1"]["undated"]
R["bias_dom_ratio"] = bias["dom"]["dated"] / bias["dom"]["undated"]
R["dated_share_wales"] = float(c[c.nation == "Wales"].dated.mean())
R["dated_share_england"] = float(c[c.nation == "England"].dated.mean())
R["dated_share_scotland"] = float(c[c.nation == "Scotland"].dated.mean())

# ---------------- density by county and the Welsh March
cb = json.load(open(os.path.join(WORK, "counties_bng.json")))
polys = {f["county"]: (shape(f["geom"]), f["nation"]) for f in cb["features"]}
rows = []
for name, (g, nat) in polys.items():
    s = c[c.county == name]
    a = g.area / 1e6
    rows.append({"county": name, "nation": nat, "area_km2": round(a), "castles": int(len(s)),
                 "earthworks": int(s.type.isin(["motte", "ringwork"]).sum()), "dated": int(s.dated.sum()),
                 "per_1000km2": len(s) / a * 1000, "earthworks_per_1000km2": s.type.isin(["motte", "ringwork"]).sum() / a * 1000})
cd = pd.DataFrame(rows).sort_values("per_1000km2", ascending=False)
cd.to_csv(os.path.join(DATA, "county_density.csv"), index=False, float_format="%.2f")
big = cd[cd.area_km2 >= 500]
R["county_top"] = big.head(8)[["county", "nation", "castles", "earthworks", "per_1000km2", "earthworks_per_1000km2", "area_km2"]].to_dict("records")
R["county_top_earth"] = big.sort_values("earthworks_per_1000km2", ascending=False).head(8)[["county", "nation", "earthworks", "earthworks_per_1000km2"]].to_dict("records")
R["county_min_area_km2"] = 500
R["county_bottom_eng"] = big[big.nation == "England"].tail(3)[["county", "castles", "per_1000km2"]].to_dict("records")
R["county_lancs"] = cd[cd.county == "Lancashire"][["county", "castles", "earthworks", "per_1000km2", "earthworks_per_1000km2"]].to_dict("records")[0]
R["county_hereford"] = cd[cd.county == "Herefordshire"][["county", "castles", "earthworks", "per_1000km2", "earthworks_per_1000km2"]].to_dict("records")[0]
R["county_shrop"] = cd[cd.county == "Shropshire"][["county", "castles", "earthworks", "per_1000km2", "earthworks_per_1000km2"]].to_dict("records")[0]
eng_area = sum(g.area for g, n in polys.values() if n == "England") / 1e6
wal_area = sum(g.area for g, n in polys.values() if n == "Wales") / 1e6
sco_area = sum(g.area for g, n in polys.values() if n == "Scotland") / 1e6
R["density_nation"] = {n: {"per_1000km2": float((c.nation == n).sum() / a * 1000),
                           "earth_per_1000km2": float(((c.nation == n) & c.type.isin(["motte", "ringwork"])).sum() / a * 1000)}
                       for n, a in [("England", eng_area), ("Wales", wal_area), ("Scotland", sco_area)]}

# border band: within 40 km either side of the England-Wales border
eng_u = unary_union([g for g, n in polys.values() if n == "England"]).buffer(0)
wal_u = unary_union([g for g, n in polys.values() if n == "Wales"]).buffer(0)
border = eng_u.buffer(300).intersection(wal_u.buffer(300)).buffer(0)
BAND = 40000
band = border.buffer(BAND).intersection(unary_union([eng_u, wal_u]))
band_area = band.area / 1e6
ew_area = (eng_area + wal_area)
pts_in = np.array([band.contains(Point(x, y)) for x, y in zip(ew.x, ew.y)])
ew = ew.assign(band=pts_in)
R["march_band_km"] = BAND / 1000
R["march_band_area_km2"] = float(band_area)
R["march_band_area_share"] = float(band_area / ew_area)
R["march_band_castles"] = int(ew.band.sum())
R["march_band_share"] = float(ew.band.mean())
R["march_band_earth"] = int((ew.band & (ew.earth == 1)).sum())
R["march_band_earth_share"] = float((ew.band & (ew.earth == 1)).sum() / ew.earth.sum())
R["march_density"] = float(ew.band.sum() / band_area * 1000)
R["rest_density"] = float((~ew.band).sum() / (ew_area - band_area) * 1000)
R["march_density_ratio"] = R["march_density"] / R["rest_density"]
R["march_earth_density"] = float((ew.band & (ew.earth == 1)).sum() / band_area * 1000)
R["rest_earth_density"] = float(((~ew.band) & (ew.earth == 1)).sum() / (ew_area - band_area) * 1000)
R["march_earth_ratio"] = R["march_earth_density"] / R["rest_earth_density"]
c["march"] = False
c.loc[ew.index, "march"] = ew.band.values

# hexes (pointy-top), 15 km centre to corner
H = 15000.0
land = unary_union([g for g, _ in polys.values()]).buffer(0)
minx, miny, maxx, maxy = land.bounds
hexes = []
dx, dy = math.sqrt(3) * H, 1.5 * H
row = 0
y = miny
pts = np.c_[c.x.values, c.y.values]
earth = c.type.isin(["motte", "ringwork"]).values
ltree = STRtree([g for g, _ in polys.values()])
lgeoms = [g for g, _ in polys.values()]
while y < maxy + H:
    x = minx + (dx / 2 if row % 2 else 0)
    while x < maxx + dx:
        hx = Polygon([(x + H * math.cos(math.radians(60 * k + 30)), y + H * math.sin(math.radians(60 * k + 30))) for k in range(6)])
        idx = ltree.query(hx)
        if len(idx):
            la = sum(hx.intersection(lgeoms[i]).area for i in idx) / 1e6
            if la > 50:
                inside = (np.abs(pts[:, 0] - x) < H) & (np.abs(pts[:, 1] - y) < H)
                n = ne = 0
                for k in np.where(inside)[0]:
                    if hx.contains(Point(pts[k])):
                        n += 1
                        ne += int(earth[k])
                hexes.append({"x": x, "y": y, "land_km2": la, "n": n, "ne": ne, "poly": hx})
        x += dx
    y += dy
    row += 1
feats = []
for h in hexes:
    ring = [list(map(lambda v: round(v, 4), TO_LL(px, py))) for px, py in h["poly"].exterior.coords]
    feats.append({"type": "Feature", "properties": {"castles": h["n"], "earthworks": h["ne"], "land_km2": round(h["land_km2"], 1),
                                                    "per_1000km2": round(h["n"] / h["land_km2"] * 1000, 2),
                                                    "earth_per_1000km2": round(h["ne"] / h["land_km2"] * 1000, 2)},
                  "geometry": {"type": "Polygon", "coordinates": [ring]}})
json.dump({"type": "FeatureCollection", "features": feats}, open(os.path.join(DATA, "hexes.geojson"), "w"), separators=(",", ":"))
R["hex_size_km"] = H / 1000
R["hex_n"] = len(hexes)
hx_sorted = sorted([h for h in hexes if h["land_km2"] > 300], key=lambda h: -h["n"] / h["land_km2"])
top = hx_sorted[0]
tl = TO_LL(top["x"], top["y"])
R["hex_top"] = {"n": top["n"], "per_1000km2": top["n"] / top["land_km2"] * 1000, "lon": tl[0], "lat": tl[1]}
# which county holds the densest hexes
def county_at(x, y):
    for name, (g, nat) in polys.items():
        if g.contains(Point(x, y)):
            return name
    return ""
R["hex_top"]["county"] = county_at(top["x"], top["y"])
R["hex_top10_counties"] = dict(Counter(county_at(h["x"], h["y"]) for h in hx_sorted[:10]).most_common())

# ---------------- north-west
nw = ["Lancashire", "Cumbria", "Merseyside", "Greater Manchester"]
nwd = W[W.county.isin(nw)].sort_values("year")
R["nw_dated"] = [{"label": r.label, "year": int(r.year), "county": r.county, "round": int(r.round_year), "km": float(r.dist_km)} for r in nwd.itertuples()]
R["nw_n_items"] = int(c.county.isin(nw).sum())
R["nw_earliest_wd"] = R["nw_dated"][0]
R["nw_median_year"] = float(nwd.year.median())
se = ["East Sussex", "West Sussex", "Kent", "Surrey", "Greater London", "Hampshire", "Berkshire", "Essex", "Hertfordshire"]
R["se_median_year"] = float(W[W.county.isin(se)].year.median())
R["se_n"] = int(W.county.isin(se).sum())
R["nw_n"] = int(len(nwd))
for nm, q in [("lancaster", "Q2969640"), ("clitheroe", "Q5134437"), ("penwortham", "Q7165387"), ("hastings", "Q5680295"), ("york", "Q80637"), ("durham", "Q752266"), ("carlisle", "Q614836")]:
    r = c[c.qid == q].iloc[0]
    R["k_" + nm] = {"label": r.label, "year": None if pd.isna(r.inception_year) else int(r.inception_year), "round": int(r.round_year),
                    "type": r.type, "km": float(r.dist_km), "qid": q}
# median distance-from-Battle band and median year
bands = [(0, 150), (150, 300), (300, 450), (450, 2000)]
R["band_year"] = [{"lo": lo, "hi": hi, "n": int(((Wew.dist_km >= lo) & (Wew.dist_km < hi)).sum()),
                   "median_year": float(Wew[(Wew.dist_km >= lo) & (Wew.dist_km < hi)].year.median())} for lo, hi in bands]

# ---------------- Scotland
sc = W[W.nation == "Scotland"].sort_values("year")
R["scot_window"] = [{"label": r.label, "year": int(r.year), "county": r.county, "round": int(r.round_year)} for r in sc.itertuples()]
R["scot_n_items"] = int((c.nation == "Scotland").sum())
R["scot_earth"] = int(((c.nation == "Scotland") & c.type.isin(["motte", "ringwork"])).sum())

# ---------------- Domesday: waste and values near castles
dp = pd.read_csv(os.path.join(DATA, "domesday_places_waste.csv"))
R["dp_n"] = int(len(dp))
R["dp_waste_share"] = float(dp.any_waste.mean())
cs = dp.groupby("countyName").agg(n=("placeId", "size"), waste=("any_waste", "mean"), v66=("value1066_paired", "sum"), v86=("value1086_paired", "sum")).reset_index()
cs["value_ratio"] = cs.v86 / cs.v66
cs = cs.sort_values("waste", ascending=False)
cs.to_csv(os.path.join(DATA, "domesday_county_waste.csv"), index=False, float_format="%.4f")
R["dom_county_waste"] = cs[["countyName", "n", "waste", "value_ratio"]].to_dict("records")
yk = cs[cs.countyName == "Yorkshire"].iloc[0]
R["yorks_waste"] = float(yk.waste)
R["yorks_value_ratio"] = float(yk.value_ratio)
R["yorks_n"] = int(yk.n)
rest = dp[dp.countyName != "Yorkshire"]
R["rest_waste"] = float(rest.any_waste.mean())
R["rest_value_ratio"] = float(rest.value1086_paired.sum() / rest.value1066_paired.sum())
R["waste_county_2"] = cs.iloc[1][["countyName", "waste"]].to_dict()
R["waste_county_3"] = cs.iloc[2][["countyName", "waste"]].to_dict()

# neighbourhood test: Domesday places within 5 km of a castle known by 1086 vs others in the same county
k86 = c[c.qid.isin(known86)]
kx = np.r_[k86.x.values, dc[dc.wd_qid.isna() | (dc.wd_qid == "")].x.values]
ky = np.r_[k86.y.values, dc[dc.wd_qid.isna() | (dc.wd_qid == "")].y.values]
dmin = np.min(np.hypot(dp.x.values[:, None] - kx[None, :], dp.y.values[:, None] - ky[None, :]), axis=1) / 1000
dp["near_castle"] = dmin <= 5
R["near_n"] = int(dp.near_castle.sum())
R["near_km"] = 5
# stratified by county: mean within-county difference in waste share, weighted by near count
diffs, wts, vr_near, vr_far = [], [], [], []
for cn, g in dp.groupby("countyName"):
    a, b_ = g[g.near_castle], g[~g.near_castle]
    if len(a) >= 5 and len(b_) >= 5:
        diffs.append(a.any_waste.mean() - b_.any_waste.mean())
        wts.append(len(a))
R["near_waste"] = float(dp[dp.near_castle].any_waste.mean())
R["far_waste"] = float(dp[~dp.near_castle].any_waste.mean())
R["near_waste_diff_within_county"] = float(np.average(diffs, weights=wts))
R["near_waste_counties"] = len(diffs)
R["near_waste_diff_pts"] = R["near_waste_diff_within_county"] * 100
pv = dp[dp.value1066_paired > 0]
pv = pv.assign(r=pv.value1086_paired / pv.value1066_paired)
R["near_value_median_ratio"] = float(pv[pv.near_castle].r.median())
R["far_value_median_ratio"] = float(pv[~pv.near_castle].r.median())
R["near_value_n"] = int(pv.near_castle.sum())
R["far_value_n"] = int((~pv.near_castle).sum())
R["near_value_mwu_p"] = float(stats.mannwhitneyu(pv[pv.near_castle].r, pv[~pv.near_castle].r).pvalue)
R["near_fell_share"] = float((pv[pv.near_castle].r < 1).mean())
R["far_fell_share"] = float((pv[~pv.near_castle].r < 1).mean())
# same excluding Yorkshire
ny = dp[dp.countyName != "Yorkshire"]
R["near_waste_noyorks"] = float(ny[ny.near_castle].any_waste.mean())
R["far_waste_noyorks"] = float(ny[~ny.near_castle].any_waste.mean())
pvy = pv[pv.countyName != "Yorkshire"]
R["near_value_median_ratio_noyorks"] = float(pvy[pvy.near_castle].r.median())
R["far_value_median_ratio_noyorks"] = float(pvy[~pvy.near_castle].r.median())
# Yorkshire alone
yy = dp[dp.countyName == "Yorkshire"]
R["yorks_near_waste"] = float(yy[yy.near_castle].any_waste.mean())
R["yorks_far_waste"] = float(yy[~yy.near_castle].any_waste.mean())
R["yorks_near_n"] = int(yy.near_castle.sum())

# ---------------- OSM coverage check
osm = pd.read_csv(os.path.join(DATA, "osm_castles.csv"))
R["osm_n"] = int(len(osm))
R["osm_by_nation"] = {k: int(v) for k, v in osm.nation.value_counts().items()}
op = np.c_[osm.x.values, osm.y.values]
dd = np.min(np.hypot(op[:, 0, None] - pts[None, :, 0], op[:, 1, None] - pts[None, :, 1]), axis=1)
osm["near_wd"] = dd <= 1000
R["osm_within_1km_share"] = float(osm.near_wd.mean())
R["osm_with_wd_tag"] = int((osm.wikidata.fillna("") != "").sum())
R["osm_wd_in_study"] = int(osm.wikidata.isin(set(c.qid)).sum())
dd2 = np.min(np.hypot(pts[:, 0, None] - op[None, :, 0], pts[:, 1, None] - op[None, :, 1]), axis=1)
R["wd_with_osm_1km_share"] = float((dd2 <= 1000).mean())
R["wd_with_osm_1km_share_earth"] = float((dd2[earth] <= 1000).mean())
R["osm_wd_ratio_by_nation"] = {n: float(R["osm_by_nation"].get(n, 0) / R["n_by_nation"][n]) for n in R["n_by_nation"]}

# ---------------- site data
nat_i = {"England": 0, "Wales": 1, "Scotland": 2}
TI = {"castle": 0, "motte": 1, "ringwork": 2, "keep": 3}
site_c = []
for r in c.itertuples():
    y = None if pd.isna(r.inception_year) else int(r.inception_year)
    site_c.append([round(r.lat, 4), round(r.lon, 4), r.label, TI[r.type], y, int(r.round_year), r.county, nat_i[r.nation],
                   r.qid[1:], round(r.dist_km), int(r.grade1), int(bool(r.domesday))])
site_d = [[round(r.lat, 4), round(r.lng, 4), r.castle, r.domesday_ref, r.domesday_place, r.quote[:260], r.open_domesday,
           "" if pd.isna(r.wd_qid) else str(r.wd_qid)] for r in dc.itertuples()]
site_h = [[round(h["x"] / 1000, 1), round(h["y"] / 1000, 1), h["n"], h["ne"], round(h["land_km2"])] for h in hexes]
site = {"bxy": [round(B["x"] / 1000, 1), round(B["y"] / 1000, 1)], "c": site_c, "d": site_d, "h": site_h, "battle": [B["lat"], B["lon"]], "dec": dec,
        "dw": [[r.year, round(r.dist_km), r.label, r.county, int(r.round_year), r.nation] for r in W.sort_values("year").itertuples()],
        "waste": [[r["countyName"], r["n"], round(r["waste"], 4), round(r["value_ratio"], 3)] for r in R["dom_county_waste"]],
        "cd": [[r.county, r.nation, r.castles, r.earthworks, round(r.per_1000km2, 2), round(r.earthworks_per_1000km2, 2), r.area_km2] for r in big.itertuples()],
        "houses": R["houses"]}
json.dump(site, open(os.path.join(WORK, "site.json"), "w"), ensure_ascii=False, separators=(",", ":"))


def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, float) and math.isnan(o):
        return None
    return o


json.dump(clean(R), open(os.path.join(DATA, "results.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps(clean({k: R[k] for k in ["n_items", "n_dated_any", "n_window", "window_round", "furthest_by_1072_ew", "p1066_1071", "p1072_1086", "p1087_1135", "p1136_1199", "spearman_year_dist_ew", "bias", "march_density_ratio", "march_earth_ratio", "march_band_share", "march_band_area_share", "county_top", "hex_top", "hex_top10_counties", "nw_dated", "se_median_year", "nw_median_year", "dc_matched", "dc_matched_dated", "dc_matched_undated", "dc_after1086_list", "houses_total", "yorks_waste", "rest_waste", "near_waste", "far_waste", "near_waste_diff_within_county", "near_value_median_ratio", "far_value_median_ratio", "near_value_mwu_p", "near_waste_noyorks", "far_waste_noyorks", "osm_within_1km_share", "wd_with_osm_1km_share", "wd_with_osm_1km_share_earth", "band_year", "scot_window", "known_by_1086_total"]}), indent=0)[:9000])
