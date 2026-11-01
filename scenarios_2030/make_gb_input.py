"""Build the two 'today' input files of scenarios_2030 from the model_v4 output.

1. data/input_hourly.csv    = byte-for-byte copy of ../model_v4/data/input_hourly.csv (Iceland, Elma price)
2. data/input_hourly_gb.csv = the Scotland (GB) variant: same file, only the price column 'pi' is replaced
   by the GB day-ahead price:
- source: Elexon BMRS Market Index Data, data/raw/gb_market_index_price.csv (from data/01_download.py),
  half-hourly, two providers per half hour (APXMIDP, N2EXMIDP).
- keep provider APXMIDP and rows with volume > 0 (N2EXMIDP rows and empty half hours carry price 0.0,
  which is "no data", not a real price of zero).
- startTime is UTC; each half hour goes to the UTC hour it starts in (floor), hourly price = mean of the
  two half hours (or the one that exists).
- hours of the model year without any valid half hour are linearly interpolated (then bfill/ffill at the ends).
- GBP -> EUR with a fixed rate of 1.16 EUR/GBP, rounded to 4 decimals.
All other columns are taken unchanged from data/input_hourly.csv.

python make_gb_input.py  ->  data/input_hourly.csv, data/input_hourly_gb.csv
"""
import pathlib
import shutil

import pandas as pd

HERE = pathlib.Path(__file__).parent
FAROE = HERE.parent
GB_RAW = FAROE / "data" / "raw" / "gb_market_index_price.csv"
V4_INPUT = FAROE / "model_v4" / "data" / "input_hourly.csv"
DATA = HERE / "data"
EUR_PER_GBP = 1.16

DATA.mkdir(exist_ok=True)
shutil.copyfile(V4_INPUT, DATA / "input_hourly.csv")
print("copied model_v4/data/input_hourly.csv -> scenarios_2030/data/input_hourly.csv")

ts = pd.read_csv(DATA / "input_hourly.csv", parse_dates=["time_utc"])
gb = pd.read_csv(GB_RAW, parse_dates=["startTime"])
gb = gb[(gb.dataProvider == "APXMIDP") & (gb.volume > 0)].copy()
gb["h"] = gb.startTime.dt.tz_localize(None).dt.floor("h")      # UTC hour the half hour starts in
hourly = gb.groupby("h").price_gbp_mwh.mean()

p = ts.time_utc.map(hourly)
missing = ts.time_utc[p.isna()].dt.strftime("%Y-%m-%d %H:%M").tolist()
print(f"model year hours without a valid GB price (interpolated): {len(missing)} {missing}")
ts["pi"] = (p.interpolate().bfill().ffill() * EUR_PER_GBP).round(4)
ts["time_utc"] = ts.time_utc.dt.strftime("%Y-%m-%d %H:%M")
assert len(ts) == 8760 and not ts.isna().any().any()
ts.to_csv(DATA / "input_hourly_gb.csv", index=False)
print(f"written data/input_hourly_gb.csv, GB price mean {ts.pi.mean():.1f} EUR/MWh, "
      f"min {ts.pi.min():.1f}, max {ts.pi.max():.1f}, hours < 0: {int((ts.pi < 0).sum())}")
