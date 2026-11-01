"""Download C3S energy indicators (ERA5-based capacity factors) for the Faroe model year
Oct 2025 - Sep 2026, keep only the grid cells around the Faroes, delete the big Europe files.
Output: data/raw/c3s/c3s_faroe_cf_hourly.csv  (time UTC, one column per variable x cell)
"""
import glob, os, time, zipfile, shutil
import cdsapi, xarray as xr, pandas as pd

OUT = os.path.dirname(os.path.abspath(__file__))
MONTHS = [("2025", m) for m in ("10", "11", "12")] + [("2026", f"{m:02d}") for m in range(1, 10)]
VARS = {"wind_power_generation_onshore": "won", "solar_photovoltaic_power_generation": "spv"}
BOX = dict(latitude=slice(62.5, 61.25), longitude=slice(-7.75, -6.25))

c = cdsapi.Client(quiet=True, progress=False)
parts = []
for var, short in VARS.items():
    for y, m in MONTHS:
        tag = f"{short}_{y}_{m}"
        cache = os.path.join(OUT, f"cell_{tag}.csv")
        if os.path.exists(cache):
            parts.append(pd.read_csv(cache, index_col=0, parse_dates=True)); continue
        z = os.path.join(OUT, f"{tag}.zip"); tmp = os.path.join(OUT, f"tmp_{tag}")
        for attempt in range(3):
            try:
                t = time.time()
                c.retrieve("sis-energy-derived-reanalysis", {
                    "variable": [var], "spatial_aggregation": "original_grid",
                    "energy_product_type": "capacity_factor_ratio", "temporal_aggregation": "hourly",
                    "year": [y], "month": [m]}, z)
                break
            except Exception as e:
                print(f"{tag} attempt {attempt+1} failed: {e}", flush=True); time.sleep(30)
        else:
            raise SystemExit(f"giving up on {tag}")
        os.makedirs(tmp, exist_ok=True)
        zipfile.ZipFile(z).extractall(tmp)
        ds = xr.open_dataset(glob.glob(os.path.join(tmp, "*.nc"))[0])
        da = ds[list(ds.data_vars)[0]].sel(**BOX)
        df = da.to_dataframe().reset_index().dropna()
        df["col"] = short + "_" + df.latitude.astype(str) + "_" + df.longitude.astype(str)
        wide = df.pivot(index="time", columns="col", values=da.name)
        wide.to_csv(cache); parts.append(wide); ds.close()
        os.remove(z); shutil.rmtree(tmp)
        print(f"{tag}: {len(wide)} h, cells {list(wide.columns)}, mean {wide.mean().round(3).to_dict()}, {round(time.time()-t)} s", flush=True)

full = pd.concat(parts)                     # stack months (rows); wind/solar columns differ
full = full.groupby(level=0).first().sort_index()  # merge wind+solar rows of the same hour
full.to_csv(os.path.join(OUT, "c3s_faroe_cf_hourly.csv"))
print("DONE", full.shape, full.index.min(), full.index.max())
print(full.mean().round(3))
