"""make_figures_v3.py - three seaborn figures from results/summary.csv and results/hourly_ntc*.csv."""
import pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

HERE = pathlib.Path(__file__).parent
RES = HERE / "results"
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)
sns.set_theme(style="whitegrid", context="notebook")
pal = sns.color_palette("deep")

s = pd.read_csv(RES / "summary.csv").sort_values("ntc_MW")
s["cable"] = s.ntc_MW.astype(int).astype(str) + " MW"
order = s.cable.tolist()

# ---------------------------------------------------------------- 1) yearly cost vs cable size
comp = {"c_wind_MEUR": "new wind", "c_pv_MEUR": "new solar PV", "c_storage_MEUR": "new storage",
        "c_trade_MEUR": "net import cost", "c_cable_MEUR": "cable"}
long = s.melt(id_vars="cable", value_vars=list(comp), var_name="component", value_name="MEUR")
long["component"] = long.component.map(comp)
long.loc[long.component == "new storage", "MEUR"] += long.loc[long.component == "new storage", "cable"].map(
    s.set_index("cable").c_storage_vc_MEUR)   # storage discharge cost added to storage
colors = dict(zip(comp.values(), [pal[0], pal[1], pal[2], pal[4], pal[7]]))
fig, ax = plt.subplots(figsize=(7.5, 4.6))
pos = np.zeros(len(order))
neg = np.zeros(len(order))
x = np.arange(len(order))
for c in comp.values():
    v = long[long.component == c].set_index("cable").MEUR.reindex(order).values
    bottom = np.where(v >= 0, pos, neg)
    ax.bar(x, v, bottom=bottom, color=colors[c], label=c, width=0.6, edgecolor="white")
    pos += np.where(v >= 0, v, 0)
    neg += np.where(v < 0, v, 0)
sns.scatterplot(x=x, y=s.total_cost_MEUR.values, color="black", marker="D", s=60, zorder=5, ax=ax,
                label="total")
for xi, (tot, per) in enumerate(zip(s.total_cost_MEUR, s.cost_per_MWh_demand)):
    ax.annotate(f"{tot:.1f} M EUR\n{per:.0f} EUR/MWh", (xi, max(tot, pos[xi])), xytext=(0, 8),
                textcoords="offset points", ha="center", fontsize=9)
ax.axhline(0, color="black", lw=0.8)
ax.set_xticks(x, order)
ax.set_xlabel("cable capacity to Iceland (ntc)")
ax.set_ylabel("additional cost (M EUR per year)")
ax.set_ylim(min(-2, neg.min() * 1.3), max(pos.max(), s.total_cost_MEUR.max()) * 1.25)
ax.set_title("Yearly cost of an oil-free main grid by cable size")
ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8, frameon=False)
fig.tight_layout()
fig.savefig(FIG / "fig1_cost_vs_cable.png", dpi=200)
plt.close(fig)

# ---------------------------------------------------------------- 2) new capacity per cable size
capc = {"new_wind_MW": "wind", "new_pv_MW": "solar PV", "new_bat_MW": "battery", "new_phs_MW": "pumped hydro"}
lc = s.melt(id_vars="cable", value_vars=list(capc), var_name="tech", value_name="MW")
lc["tech"] = lc.tech.map(capc)
lc["MW"] = lc.MW.clip(lower=0)
fig, ax = plt.subplots(figsize=(7.5, 4.6))
sns.histplot(data=lc, x="cable", hue="tech", weights="MW", multiple="stack", discrete=True, shrink=0.6,
             hue_order=list(capc.values()), palette=[pal[0], pal[1], pal[2], pal[9]], edgecolor="white",
             ax=ax, alpha=1)
tot = s.set_index("cable")[list(capc)].clip(lower=0).sum(axis=1).reindex(order)
for xi, c in enumerate(order):
    r = s.set_index("cable").loc[c]
    ax.annotate(f"battery {r.new_bat_MWh:.0f} MWh", (xi, tot[c]), xytext=(0, 5), textcoords="offset points",
                ha="center", fontsize=9)
ax.set_xlabel("cable capacity to Iceland (ntc)")
ax.set_ylabel("new capacity (MW)")
ax.set_ylim(0, tot.max() * 1.15 + 5)
tech = pd.read_csv(HERE / "data" / "technologies.csv").set_index("technology")
ax.set_title(f"New capacity on top of today's system ({tech.g_max['wind']:g} MW wind, {tech.g_max['hydro']:g} MW hydro, "
             f"{tech.g_max['battery']:g} MW battery)", fontsize=10)
sns.move_legend(ax, "upper right", title=None, fontsize=9)
fig.tight_layout()
fig.savefig(FIG / "fig2_capacity_vs_cable.png", dpi=200)
plt.close(fig)

# ---------------------------------------------------------------- 3) dispatch in the calmest summer week
inp = pd.read_csv(HERE / "data" / "input_hourly.csv", parse_dates=["time_utc"])
wk = inp.set_index("time_utc").ava_wind.rolling(168).mean()
summer = wk[(wk.index >= "2026-06-07 23:00") & (wk.index <= "2026-08-31 23:00")]
end = summer.idxmin()
start = end - pd.Timedelta(hours=167)
fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True, sharey=True)
layers = [("biogas", "biogas", pal[5]), ("hydro", "hydro", pal[9]), ("wind_used", "wind", pal[0]),
          ("pv_used", "solar PV", pal[1]), ("bat_dis", "battery discharge", pal[2]),
          ("imp", "import from Iceland", pal[4])]
for ax, n in zip(axes, [0, 50]):
    h = pd.read_csv(RES / f"hourly_ntc{n}.csv", parse_dates=["time_utc"])
    h = h[(h.time_utc >= start) & (h.time_utc <= end)].copy()
    res = h.wind_avail + h.pv_avail
    share_w = np.where(res > 0, h.wind_avail / res.where(res > 0, 1), 0)
    h["wind_used"] = h.wind_avail - h.curtailment * share_w
    h["pv_used"] = h.pv_avail - h.curtailment * (1 - share_w)
    h["bat_dis"] = h.bat_dis + h.phs_dis
    ax.stackplot(h.time_utc, *[h[c] for c, _, _ in layers], labels=[l for _, l, _ in layers],
                 colors=[c for _, _, c in layers], alpha=0.9)
    ax.stackplot(h.time_utc, -(h.bat_ch + h.phs_ch), -h.exp, colors=[pal[2], pal[4]], alpha=0.45,
                 labels=["battery charge", "export"])
    sns.lineplot(x=h.time_utc, y=h.demand, color="black", lw=1.6, label="demand", ax=ax)
    ax.axhline(0, color="black", lw=0.6)
    ax.set_ylabel("MW")
    ax.set_title(f"ntc = {n} MW", loc="left", fontsize=11)
    ax.legend().remove()
handles, labels = axes[0].get_legend_handles_labels()
h1, l1 = axes[1].get_legend_handles_labels()
for hh, ll in zip(h1, l1):
    if ll not in labels:
        handles.append(hh)
        labels.append(ll)
fig.legend(handles, labels, loc="lower center", ncol=5, fontsize=9, frameon=False)
fig.suptitle(f"Dispatch in the calmest summer week ({start:%d.%m.} - {end:%d.%m.%Y}, UTC)", fontsize=12)
axes[1].set_xlabel("")
fig.tight_layout(rect=(0, 0.08, 1, 1))
fig.savefig(FIG / "fig3_dispatch_calm_week.png", dpi=200)
plt.close(fig)
print("figures written to", FIG, "calm week", start, end)
