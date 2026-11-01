"""prepare_v3.py - hourly model inputs for one model year, 2025-10-01 00:00 UTC to 2026-09-30 23:00 UTC (8760 h).

Output: data/input_hourly.csv with hour, time_utc, demand, ava_wind, ava_pv, hydro_inflow, biogas, pi
        (MW or MWh per hour, EUR/MWh for pi), and data/prepare_checks.txt (the printed checks).

Construction (one year for all inputs):
- SEV cleaning      the raw file holds several rows per (hour, plant): exact copies (all columns identical,
                    dropped) and separate partial records of the same plant and hour (summed). So:
                    drop exact duplicates, then sum mwh per (date_local, powerplant).
- demand d_t      = sum of all main-grid production per hour (no cable today, so production = consumption).
                    Suðuroy plants (Vágur, Botnur, Suðuroy, Sumba) are a separate grid and left out.
                    Missing hours and hours with load < 25 MW (data gaps) are filled by linear interpolation.
- ava_wind,t      = SEV main-grid wind output / 61.55 MW installed in the feed, clipped to [0, 1].
- ava_pv,t        = SEV output of the Sumba PV plant / 0.24 MW (SEV plant list), clipped to [0, 1].
- hydro_inflow_t  = SEV hydro production of the calendar month, spread evenly over the hours of that month.
- biogas_t        = Førka biogas output as produced (fixed injection).
- pi_t            = Elma (Iceland) day-ahead price, hourly, EUR/MWh; missing prices linearly interpolated.
Time: SEV reports local Faroese time (WET/WEST). It is converted to UTC; the repeated autumn hour is
ambiguous and dropped, the missing UTC hours are interpolated. Elma reports UTC (Iceland has no DST).
"""
import pathlib
import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).parent
FAROE = HERE.parent
SEV_RAW = FAROE / "data" / "raw" / "sev_production_hourly.csv"
ELMA_RAW = FAROE / "study" / "data" / "raw" / "elma_dayahead.csv"
OUT = HERE / "data"
OUT.mkdir(exist_ok=True)

START, END = "2025-10-01 00:00", "2026-09-30 23:00"   # UTC
# MW in the SEV wind feed: Neshagi 4.65 (SEV plant list, sev.fo, checked 21.10.2026) + Húsahagi 11.7
# + Gellingaklettur 25.2 + Flatnahagi 18 + Vestmanna 2
WIND_CAP = 4.65 + 11.7 + 25.2 + 18 + 2   # = 61.55
PV_CAP = 0.24          # MW, Sumba (SEV plant list, sev.fo, checked 21.10.2026)
SUDUROY = ["Vágur", "Botnur", "Suðuroy", "Sumba"]   # separate grid, not in the main-grid demand
FUELS = ["Biogas", "Oil", "Water", "Wind"]
LOG = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.append(s)


full = pd.date_range(START, END, freq="h")
say(f"model year {full[0]} .. {full[-1]} UTC, {len(full)} hours")

# ------------------------------------------------------------------ SEV hourly production per plant
raw = pd.read_csv(SEV_RAW)
n_raw = len(raw)
exact = raw.duplicated()                                   # all columns identical -> true copies
clean = raw[~exact]
rows_per_key = clean.groupby(["date_local", "powerplant"]).size()
sev = clean.groupby(["date_local", "powerplant", "motivepower", "area"], as_index=False).mwh.sum()
sev["t_local"] = pd.to_datetime(sev.date_local)
say(f"SEV rows {n_raw}; exact duplicate rows dropped: {int(exact.sum())}; remaining rows {len(clean)} -> "
    f"{len(sev)} (hour, plant) values after summing partial records; rows per (hour, plant): "
    f"{rows_per_key.value_counts().sort_index().to_dict()} (> 3 rows only at local hours "
    f"{sorted(rows_per_key[rows_per_key > 3].index.get_level_values(0).unique().tolist())}, the repeated autumn hour); "
    f"(hour, plant) keys split over two chunks: {int((clean.groupby(['date_local', 'powerplant']).chunk.nunique() > 1).sum())}")

# previous cleaning, for the before/after log only: keep the first row per (hour, plant)
sev_first = raw[~raw.duplicated(["date_local", "powerplant"], keep="first")].copy()
sev_first["t_local"] = pd.to_datetime(sev_first.date_local)


def to_utc(frame):
    idx = frame.index.tz_localize("Atlantic/Faroe", ambiguous="NaT", nonexistent="NaT")
    out = frame.copy()
    out.index = idx
    out = out[out.index.notna()]
    out.index = out.index.tz_convert("UTC").tz_localize(None)
    return out[~out.index.duplicated()]


def hourly(frame):
    """main-grid production per motive power + Sumba PV, local time -> UTC model year, gaps interpolated."""
    main = frame[~frame.powerplant.isin(SUDUROY)].pivot_table(
        index="t_local", columns="motivepower", values="mwh", aggfunc="sum")
    main["load"] = main[FUELS].sum(axis=1)
    pv = frame[frame.powerplant == "Sumba"].set_index("t_local").mwh.rename("pv")
    df = main.join(pv, how="outer")
    n_local = int(((df.index >= "2025-10-01 01:00") & (df.index <= "2026-10-01 00:00")).sum())
    out = to_utc(df).reindex(full)
    info = dict(n_local=n_local, n_missing=int(out.load.isna().sum()),
                missing_hours=[str(x) for x in out.index[out.load.isna()]])
    bad = out.load < 25
    info["n_bad"] = int(bad.sum())
    out.loc[bad, FUELS + ["load"]] = np.nan
    info["n_pv_missing"] = int(out.pv.isna().sum())
    return out.interpolate(limit_direction="both"), info


s, info = hourly(sev)
s_first, _ = hourly(sev_first)
n_local = info["n_local"]
say(f"DST: local rows in the window {n_local}; autumn change 26.10.2025 (local 01:00 twice) -> ambiguous hour dropped; "
    f"spring change 29.03.2026 (local 01:00 does not exist) -> no gap in UTC")
say(f"SEV main grid: missing UTC hours filled by interpolation: {info['n_missing']} {info['missing_hours']}; "
    f"hours with load < 25 MW interpolated: {info['n_bad']}; Sumba missing hours interpolated: {info['n_pv_missing']}")

say("\n=== SEV cleaning: before (first row per hour and plant kept) vs after (exact duplicates dropped, "
    "partial records summed), GWh ===")
ba = pd.DataFrame({"before": s_first[FUELS + ["load"]].sum() / 1e3, "after": s[FUELS + ["load"]].sum() / 1e3})
ba.loc["Sumba PV (MWh)"] = [s_first.pv.sum(), s.pv.sum()]
ba["diff"] = ba.after - ba.before
say("model year, main grid (UTC, as used in the model):")
say(ba.round(2).to_string())
yr = (sev_first.t_local >= "2025-10-01") & (sev_first.t_local < "2026-10-01")
yn = (sev.t_local >= "2025-10-01") & (sev.t_local < "2026-10-01")
pp = pd.DataFrame({"before": sev_first[yr].groupby("powerplant").mwh.sum() / 1e3,
                   "after": sev[yn].groupby("powerplant").mwh.sum() / 1e3,
                   "max_h_after_MWh": sev[yn].groupby("powerplant").mwh.max()})
pp["diff"] = pp.after - pp.before
say("model year per plant (local time, all plants; Suðuroy plants not in the model):")
say(pp.round(3).to_string())
for tag, d in [("before", sev_first), ("after", sev)]:
    c = d[(d.t_local >= "2024-01-01") & (d.t_local < "2025-01-01")]
    m = c[~c.powerplant.isin(SUDUROY)]
    say(f"calendar year 2024 {tag}: all plants {c.mwh.sum()/1e3:.1f} GWh (SEV annual accounts 2024: 271 GWh renewable = 56.6 % -> about 479 GWh), "
        f"main grid {m.mwh.sum()/1e3:.1f}, main-grid wind {m[m.motivepower == 'Wind'].mwh.sum()/1e3:.1f} GWh")

ava_wind = np.clip(s.Wind.values / WIND_CAP, 0, 1)
ava_pv = np.clip(s.pv.clip(lower=0).values / PV_CAP, 0, 1)
hyd = pd.Series(s.Water.values, index=full)
inflow = hyd.groupby([hyd.index.year, hyd.index.month]).transform("mean").values   # MWh per hour, flat per month

# ------------------------------------------------------------------ Elma day-ahead price (UTC)
e = pd.read_csv(ELMA_RAW)
e["t"] = pd.to_datetime(e.time_utc, utc=True).dt.tz_localize(None)
e = e.drop_duplicates("t").set_index("t").price_eur_mwh
p = e.reindex(full)
n_p_missing = int(p.isna().sum())
say(f"Elma: rows in file {len(e)} ({e.index.min()} .. {e.index.max()}), missing prices in the whole file "
    f"{int(e.isna().sum())}; missing in the model year (interpolated): {n_p_missing} "
    f"{[str(x) for x in p.index[p.isna()]]}")
p = p.interpolate(limit_direction="both")

ts = pd.DataFrame({
    "hour": np.arange(1, len(full) + 1),
    "time_utc": full.strftime("%Y-%m-%d %H:%M"),
    "demand": s.load.values.round(4),
    "ava_wind": ava_wind.round(5),
    "ava_pv": ava_pv.round(5),
    "hydro_inflow": inflow.round(5),
    "biogas": s.Biogas.values.round(4),
    "pi": p.values.round(4),
})
assert len(ts) == 8760 and not ts.isna().any().any()
ts.to_csv(OUT / "input_hourly.csv", index=False)

# ------------------------------------------------------------------ checks
say("\n=== yearly sums (model year) ===")
say(f"demand          {ts.demand.sum()/1e3:8.1f} GWh   peak {ts.demand.max():.1f} MW   min {ts.demand.min():.1f} MW")
say(f"  of which oil  {s.Oil.sum()/1e3:8.1f} GWh ({s.Oil.sum()/ts.demand.sum():.0%})  hydro {s.Water.sum()/1e3:.1f}  "
    f"wind {s.Wind.sum()/1e3:.1f}  biogas {s.Biogas.sum()/1e3:.1f} GWh")
say(f"wind            CF {ava_wind.mean():.3f}  ({ava_wind.sum():.0f} full-load h)  max ava {ava_wind.max():.3f}")
say(f"PV (Sumba)      {s.pv.sum():.1f} MWh -> {ava_pv.sum():.0f} full-load h at {PV_CAP} MW "
    f"(at 0.25 MW: {s.pv.sum()/0.25:.0f} h; literature for the Faroes 584-620 h)  max ava {ava_pv.max():.3f}  "
    f"hours clipped at 1: {int((s.pv.values/PV_CAP > 1).sum())}")
say(f"hydro inflow    {inflow.sum()/1e3:8.1f} GWh (= SEV hydro production)")
say(f"biogas          {ts.biogas.sum()/1e3:8.1f} GWh   max {ts.biogas.max():.2f} MW")
q = ts.pi.quantile([0.05, 0.25, 0.5, 0.75, 0.95]).round(1).tolist()
say(f"Elma price      mean {ts.pi.mean():.1f}  min {ts.pi.min():.2f}  max {ts.pi.max():.1f} EUR/MWh  "
    f"P5/P25/P50/P75/P95 {q}  hours <= 0: {int((ts.pi <= 0).sum())}")
say(f"demand-weighted Elma price {np.average(ts.pi, weights=ts.demand):.1f}; wind-weighted {np.average(ts.pi, weights=ava_wind):.1f}; "
    f"PV-weighted {np.average(ts.pi, weights=ava_pv):.1f} EUR/MWh")

say("\n=== monthly (GWh; PV in MWh; price EUR/MWh) ===")
mon = pd.DataFrame({"demand": ts.demand.values, "oil": s.Oil.values, "hydro": s.Water.values,
                    "wind": s.Wind.values, "pv_MWh": s.pv.values * 1e3, "pi": ts.pi.values}, index=full)
mt = mon.resample("MS").agg({"demand": "sum", "oil": "sum", "hydro": "sum", "wind": "sum", "pv_MWh": "sum", "pi": "mean"})
mt[["demand", "oil", "hydro", "wind", "pv_MWh"]] /= 1e3
mt.index = mt.index.strftime("%Y-%m")
say(mt.round(1).to_string())

wk = pd.Series(ava_wind, index=full).rolling(168).mean()
summer = wk[(wk.index >= "2026-06-07 23:00") & (wk.index <= "2026-08-31 23:00")]   # window fully in Jun-Aug
e7 = summer.idxmin()
say(f"\ncalmest summer week (lowest 7-day mean ava_wind, Jun-Aug 2026): {e7 - pd.Timedelta(hours=167)} .. {e7} UTC, "
    f"mean ava_wind {summer.min():.3f}")
(OUT / "prepare_checks.txt").write_text("\n".join(LOG), encoding="utf-8")
