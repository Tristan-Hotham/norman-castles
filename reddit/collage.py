"""Reddit collage (2400 x 3000 px) for The Conquest in Castles. Run from anywhere: python3 reddit/collage.py"""
import json, os
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon as MPoly
from pyproj import Transformer
from shapely.geometry import box, shape
from shapely.ops import transform

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
F = '/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/fonts/'
for f in ['FrauncesVar.ttf', 'IBMPlexMono-Regular.ttf', 'IBMPlexMono-Medium.ttf', 'SourceSerif4-Regular.ttf', 'SourceSerif4-Semibold.ttf', 'SourceSerif4-It.ttf']:
    fm.fontManager.addfont(F + f)
DISP = fm.FontProperties(fname=F + 'FrauncesVar.ttf', weight=900)
SER, MONO = 'Source Serif 4', 'IBM Plex Mono'
BG, FG, MUT, LAND = '#DCE5D5', '#1A2118', '#56614F', '#C6D2BD'
HOT, GOLD, UND = '#9E2B1C', '#A8700C', '#9AA791'
R = json.load(open(os.path.join(ROOT, 'data', 'results.json')))
c = pd.read_csv(os.path.join(ROOT, 'data', 'castles.csv'))
dw = pd.read_csv(os.path.join(ROOT, 'data', 'castles_dated.csv'))
dc = pd.read_csv(os.path.join(ROOT, 'data', 'domesday_castles.csv'))
xy = c.set_index('qid')[['x', 'y']]
dw = dw.join(xy, on='qid')
TO = Transformer.from_crs('EPSG:4326', 'EPSG:27700', always_xy=True).transform
LANDP = []
for f in json.load(open('/home/claude/hist/_data3/ne/geojson/ne_10m_land.geojson'))['features']:
    g = shape(f['geometry']); gb = box(-8.8, 49.7, 2.1, 61.0)
    if not g.intersects(gb): continue
    g = transform(TO, g.intersection(gb))
    for p in getattr(g, 'geoms', [g]):
        if p.geom_type == 'Polygon' and p.area > 2e7: LANDP.append(np.array(p.exterior.coords))
B = TO(R['battle']['lon'], R['battle']['lat'])
cmap = matplotlib.colors.LinearSegmentedColormap.from_list('t', ['#6E1309', '#B8401F', '#D98A3A', '#E9C46A'])

def basemap(ax, ylim=(5000, 990000), xlim=(60000, 660000)):
    ax.set_facecolor(BG)
    for a in LANDP: ax.add_patch(MPoly(a, closed=True, fc=LAND, ec='none', zorder=0))
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect('equal'); ax.axis('off')

fig = plt.figure(figsize=(12, 15), dpi=200, facecolor=BG)
fig.text(0.04, 0.968, 'Hastings to Durham in six years', fontproperties=DISP, fontsize=45, color=FG, va='top')
fig.text(0.04, 0.918, f"How fast Norman castles spread across Britain. {R['n_items']:,} castle sites in Wikidata, the {R['n_window']} with a\n"
         f"date from 1066 to 1199, and the {R['n_domesday_castles']} castles that Domesday Book names in 1086.", family=SER, fontsize=15.5, color=FG, va='top', linespacing=1.35)

# hero map
ax = fig.add_axes([0.0, 0.31, 0.58, 0.56]); basemap(ax, xlim=(25000, 715000))
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch
LANDCLIP = PathPatch(MPath.make_compound_path(*[MPath(a) for a in LANDP]), transform=ax.transData)
u = c[c.inception_year.isna()]
ax.scatter(u.x, u.y, s=2.2, c=UND, lw=0, alpha=.9, zorder=1, rasterized=True)
for rk in range(100, 701, 100):
    ring = ax.add_patch(plt.Circle(B, rk * 1000, fill=False, ec=FG, lw=.7, ls=(0, (2, 4)), alpha=.5, zorder=2)); ring.set_clip_path(LANDCLIP)
    a = np.radians(122)
    if rk <= 600: ax.text(B[0] + rk * 1000 * np.cos(a), B[1] + rk * 1000 * np.sin(a), f'{rk} km', family=MONO, fontsize=9.5, color=MUT, ha='center', va='center', zorder=6, bbox=dict(fc=BG, ec='none', pad=.6))
s = dw.sort_values('year', ascending=False)
sc = ax.scatter(s.x, s.y, s=34, c=s.year, cmap=cmap, vmin=1066, vmax=1199, ec=FG, lw=.5, zorder=4)
ax.scatter(dc.x, dc.y, s=30, marker='D', c=GOLD, ec=BG, lw=.6, zorder=3)
ax.scatter([B[0]], [B[1]], s=150, facecolor=BG, edgecolor=FG, lw=2.2, zorder=7)
ax.text(B[0] - 14000, B[1] - 26000, 'Battle, 1066', family=MONO, fontsize=10.5, color=FG, ha='right', zorder=7)
for nm, dx, dy, ha in [('York Castle', 60000, 25000, 'left'), ('Durham Castle', 70000, 30000, 'left'), ('Lancaster Castle', -95000, 40000, 'right')]:
    r = dw[dw.label == nm].iloc[0]
    ax.annotate(f"{nm.replace(' Castle', '')} {r.year}\n{r.dist_km:.0f} km", xy=(r.x, r.y), xytext=(r.x + dx, r.y + dy), family=MONO, fontsize=10, color=FG, ha=ha,
                arrowprops=dict(arrowstyle='-', color=FG, lw=.8), zorder=8)
# legend
lx = fig.add_axes([0.6, 0.735, 0.36, 0.12]); lx.axis('off'); lx.set_xlim(0, 1); lx.set_ylim(0, 1)
grad = np.linspace(1066, 1199, 200)
lx.scatter(np.linspace(0.02, 0.62, 200), np.full(200, .86), c=grad, cmap=cmap, s=60, marker='s', lw=0)
lx.text(0.02, .66, '1066', family=MONO, fontsize=10.5, color=FG); lx.text(0.62, .66, '1199', family=MONO, fontsize=10.5, color=FG, ha='right')
lx.text(0.66, .82, 'castle dated\nin Wikidata', family=MONO, fontsize=10.5, color=FG, va='center')
lx.scatter([.04], [.38], s=40, marker='D', c=GOLD); lx.text(.09, .38, f"named in Domesday Book, 1086 ({R['n_domesday_castles']})", family=MONO, fontsize=10.5, color=FG, va='center')
lx.scatter([.04], [.12], s=12, c=UND); lx.text(.09, .12, f"no date at all ({R['n_undated']:,} sites)", family=MONO, fontsize=10.5, color=FG, va='center')

# numbers
tx = fig.add_axes([0.6, 0.33, 0.38, 0.39]); tx.axis('off')
notes = [(f"{R['furthest_by_1072_ew']['km']:.0f} km", f"from Battle to Durham Castle, dated\n{R['furthest_by_1072_ew']['built']}. Distance barely rises with date\n(Spearman {R['spearman_year_dist_ew']['rho']:.2f}): the frontier leapt."),
         (f"{R['houses_total']}", f"houses Domesday says were destroyed or\ntaken for castles in {R['houses_towns']} towns, {R['houses'][0]['n']} at Lincoln."),
         (f"{R['march_density_ratio']:.1f}×", f"castle density within {R['march_band_km']:.0f} km of the\nEngland and Wales border, against the rest."),
         (f"1 in {round(1 / R['share_dated_any'])}", f"castle sites with any date. The dated ones\nare the big stone castles: {R['bias']['grade1']['dated'] * 100:.0f}% Grade I listed,\nagainst {R['bias']['grade1']['undated'] * 100:.0f}% of the undated.")]
for (big, small), y in zip(notes, [1.0, 0.74, 0.50, 0.26]):
    tx.text(0, y, big, fontproperties=DISP, fontsize=30, color=HOT, va='top', transform=tx.transAxes)
    tx.text(0, y - 0.085, small, family=SER, fontsize=12.5, color=FG, va='top', transform=tx.transAxes, linespacing=1.3)

# small multiples: cumulative by period
P = [(1066, 1071, '1066 to 1071'), (1072, 1086, '1072 to 1086'), (1087, 1135, '1087 to 1135'), (1136, 1199, '1136 to 1199')]
for i, (lo, hi, lab) in enumerate(P):
    a = fig.add_axes([0.02 + i * 0.245, 0.07, 0.225, 0.19]); basemap(a, ylim=(5000, 990000), xlim=(40000, 700000))
    old = dw[dw.year < lo]; new = dw[(dw.year >= lo) & (dw.year <= hi)]
    a.scatter(old.x, old.y, s=9, c='#6F7D68', lw=0, zorder=2)
    a.scatter(new.x, new.y, s=20, c=HOT, ec=FG, lw=.3, zorder=3)
    a.scatter([B[0]], [B[1]], s=22, facecolor=BG, edgecolor=FG, lw=1.2, zorder=4)
    a.set_title(f"{lab}\n{len(new)} new, median {R[['p1066_1071','p1072_1086','p1087_1135','p1136_1199'][i]]['median_km']:.0f} km", family=MONO, fontsize=10.5, color=FG, pad=2)
fig.text(0.04, 0.297, 'DATED CASTLES BY PERIOD, ENGLAND, WALES AND SCOTLAND (RED: NEW; GREY: EARLIER). MEDIAN KM FROM BATTLE, ENGLAND AND WALES', family=MONO, fontsize=9.5, color=MUT)
fig.text(0.04, 0.016, "Data: Wikidata (CC0), castle items retrieved 27 Oct 2026; Hull Domesday Project via realm-domesday (CC BY-NC-SA); OS Open Names and\n"
         "ONS boundaries (OGL v3, contains OS data © Crown copyright 2026); Natural Earth. Dates are Wikidata inception years, some only to the century.\n"
         "Analysis and chart: Tristan Hotham, with Python and matplotlib.", family=MONO, fontsize=9, color=MUT, linespacing=1.45)
fig.savefig(os.path.join(HERE, 'hastings_to_durham.png'), facecolor=BG, dpi=200)
print('ok')
