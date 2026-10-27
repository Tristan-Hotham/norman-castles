"""Step 4. Make header.png, the 1200 by 630 social card, with matplotlib.

Usage:
    python3 code/04_header.py
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager as fm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = "/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/fonts/"
for f in ["FrauncesVar.ttf", "IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf", "SourceSerif4-Regular.ttf"]:
    if os.path.exists(FONTS + f):
        fm.fontManager.addfont(FONTS + f)
R = json.load(open(os.path.join(ROOT, "data", "results.json")))
c = pd.read_csv(os.path.join(ROOT, "data", "castles.csv"))
dc = pd.read_csv(os.path.join(ROOT, "data", "domesday_castles.csv"))
BG, FG, HOT, OLD, GOLD, UND, MUT = "#EDF0E8", "#1C1F1A", "#A3301F", "#4C6A7C", "#B07A10", "#A9B1A3", "#5F665B"
fig = plt.figure(figsize=(6, 3.15), dpi=200, facecolor=BG)
ax = fig.add_axes([0.57, 0.02, 0.41, 0.96])
ax.set_facecolor(BG)
ax.axis("off")
u = c[c.inception_year.isna()]
d = c[(c.inception_year >= 1066) & (c.inception_year <= 1199)]
ax.scatter(u.x, u.y, s=.5, c=UND, lw=0)
ax.scatter(d.x, d.y, s=4, c=[HOT if y <= 1086 else OLD for y in d.inception_year], lw=0)
ax.scatter(dc.x, dc.y, s=4, marker="D", c=GOLD, lw=0)
ax.set_xlim(30000, 710000)
ax.set_ylim(0, 980000)
ax.set_aspect("equal")
fig.text(.05, .86, "DATA STUDY  ·  HISTORY × DATA", family="IBM Plex Mono", fontsize=7, color=MUT)
fig.text(.05, .80, "The conquest\nin castles", family="Fraunces", fontweight="black", fontsize=30, color=FG, va="top", linespacing=.92)
fig.text(.05, .40, f"{R['n_items']:,} castle sites, {R['n_window']} dated 1066 to 1199,\n{R['n_domesday_castles']} named in Domesday Book. The frontier\nleapt: {R['furthest_by_1072_ew']['km']:.0f} km from Battle by {R['furthest_by_1072_ew']['year']}.",
         family="Source Serif 4", fontsize=8.6, color=FG, va="top", linespacing=1.4)
fig.text(.05, .07, "DR TRISTAN HOTHAM  ·  INDEPENDENT RESEARCHER", family="IBM Plex Mono", fontsize=6, color=MUT)
fig.savefig(os.path.join(ROOT, "header.png"), facecolor=BG)
print("header.png")
