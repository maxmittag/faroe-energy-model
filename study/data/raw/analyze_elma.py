import pandas as pd, numpy as np
import pathlib
raw = str(pathlib.Path(__file__).resolve().parent) + "/"
d = pd.read_csv(raw + "elma_dayahead.csv", parse_dates=["time_utc"])
fx = pd.read_csv(raw + "ecb_isk_eur_daily.csv", usecols=["TIME_PERIOD", "OBS_VALUE"])
fx["date"] = pd.to_datetime(fx.TIME_PERIOD)
usd = pd.read_csv(raw + "ecb_usd_eur_daily.csv", usecols=["TIME_PERIOD", "OBS_VALUE"])
usd["date"] = pd.to_datetime(usd.TIME_PERIOD)
d["date"] = pd.to_datetime(d.delivery_date)
cal = pd.DataFrame({"date": pd.date_range("2025-03-01", d.date.max())})
cal = cal.merge(fx[["date", "OBS_VALUE"]].rename(columns={"OBS_VALUE": "isk_per_eur"}), how="left") \
         .merge(usd[["date", "OBS_VALUE"]].rename(columns={"OBS_VALUE": "usd_per_eur"}), how="left").ffill()
d = d.merge(cal, on="date", how="left")
d["price_eur_mwh"] = d.price_isk_mwh / d.isk_per_eur
d.drop(columns="date").to_csv(raw + "elma_dayahead.csv", index=False)  # add FX + EUR columns

p = d.dropna(subset=["price_isk_mwh"])
qs = [.1, .25, .5, .75, .9]
def stats(s):
    return {"mean": s.mean(), "p10": s.quantile(.1), "p25": s.quantile(.25), "median": s.median(),
            "p75": s.quantile(.75), "p90": s.quantile(.9), "min": s.min(), "max": s.max()}
out = []
def block(name, sub):
    si, se = stats(sub.price_isk_mwh), stats(sub.price_eur_mwh)
    vw = (sub.price_isk_mwh * sub.volume_mwh).sum() / sub.volume_mwh.sum()
    vwe = (sub.price_eur_mwh * sub.volume_mwh).sum() / sub.volume_mwh.sum()
    out.append(f"| {name} | {len(sub)} | " + " | ".join(f"{si[k]:,.0f} / {se[k]:.1f}" for k in
               ["mean", "p10", "p25", "median", "p75", "p90"]) + f" | {vw:,.0f} / {vwe:.1f} |")
hdr = "| Period | hours | mean | P10 | P25 | median | P75 | P90 | vol-weighted mean |\n|---|---|---|---|---|---|---|---|---|"
block("Full 2025-03-12→2026-10-16", p)
block("2025 (Mar 12–Dec 31)", p[p.time_utc.dt.year == 2025])
block("2026 (Jan 1–Oct 16)", p[p.time_utc.dt.year == 2026])
last12 = p[p.time_utc >= "2025-10-17"]
block("Last 12 months (2025-10-17→2026-10-16)", last12)

m = p.assign(month=p.time_utc.dt.strftime("%Y-%m")).groupby("month").agg(
    hours=("price_isk_mwh", "size"), mean_isk=("price_isk_mwh", "mean"), median_isk=("price_isk_mwh", "median"),
    mean_eur=("price_eur_mwh", "mean"), isk_per_eur=("isk_per_eur", "mean"))
v = d.assign(month=d.time_utc.dt.strftime("%Y-%m")).groupby("month").agg(
    vol_mwh=("volume_mwh", "sum"), avg_mw=("volume_mwh", "mean"), zero_vol_h=("volume_mwh", lambda s: (s == 0).sum()))
m = m.join(v)
mt = "| Month | hours | mean ISK/MWh | median ISK/MWh | mean EUR/MWh | avg ISK/EUR | traded MWh | avg MW | zero-vol hours |\n|---|---|---|---|---|---|---|---|---|\n" + \
    "\n".join(f"| {i} | {r.hours} | {r.mean_isk:,.0f} | {r.median_isk:,.0f} | {r.mean_eur:.1f} | {r.isk_per_eur:.1f} | {r.vol_mwh:,.0f} | {r.avg_mw:.1f} | {r.zero_vol_h} |" for i, r in m.iterrows())
fxinfo = f"ISK/EUR ECB mean over period {d.isk_per_eur.mean():.1f} (range {d.isk_per_eur.min():.1f}–{d.isk_per_eur.max():.1f}); USD/EUR mean {d.usd_per_eur.mean():.3f}"
extra = (f"Total traded volume: {d.volume_mwh.sum():,.0f} MWh over {d.delivery_date.nunique()} days; "
         f"mean {d.volume_mwh.mean():.1f} MWh/h; max {d.volume_mwh.max():.1f} MWh/h; zero-volume hours {(d.volume_mwh==0).sum()}. "
         f"Missing price hours: {d.price_isk_mwh.isna().sum()}. Price min {p.price_isk_mwh.min():,.0f}, max {p.price_isk_mwh.max():,.0f} ISK/MWh. "
         f"Full-period mean in USD/MWh (hourly ISK→EUR→USD): {(p.price_eur_mwh*p.usd_per_eur).mean():.1f}")
open(raw + "_elma_tables.md", "w").write(hdr + "\n" + "\n".join(out) + "\n\n" + mt + "\n\n" + fxinfo + "\n\n" + extra + "\n")
print(hdr); print("\n".join(out)); print(mt); print(fxinfo); print(extra)
