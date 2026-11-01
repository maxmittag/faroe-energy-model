"""Download C3S hourly CF (onshore wind + solar PV) for the Faroe main cell (62.25, -6.75),
calendar years 2016-2025, missing months only. Saves cell_<won|spv>_YYYY_MM.csv, deletes zip/nc.
4 parallel requests (one cdsapi.Client per thread), 3 retries with 30 s sleep."""
import glob, os, time, zipfile, shutil, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import cdsapi, xarray as xr

OUT = os.path.dirname(os.path.abspath(__file__))
VARS = {"wind_power_generation_onshore": "won", "solar_photovoltaic_power_generation": "spv"}
LAT, LON = 62.25, -6.75
tls = threading.local()


def client():
    if not hasattr(tls, "c"):
        tls.c = cdsapi.Client(quiet=True, progress=False)
    return tls.c


def covered(short, y, m):
    """True if any existing cell file already holds this month (older years come back as full-year files)."""
    import pandas as pd
    hrs = pd.date_range(f"{y}-{m:02d}-01", periods=1, freq="MS")
    for f in glob.glob(os.path.join(OUT, f"cell_{short}_{y}_*.csv")):
        t = pd.read_csv(f, usecols=[0]).iloc[:, 0]
        if (pd.to_datetime(t).dt.to_period("M") == hrs.to_period("M")[0]).sum() >= 24 * 28:
            return True
    return False


def job(var, short, y, m):
    tag = f"{short}_{y}_{m:02d}"
    cache = os.path.join(OUT, f"cell_{tag}.csv")
    if os.path.exists(cache) or covered(short, y, m):
        return f"{tag}: exists"
    z = os.path.join(OUT, f"my_{tag}.zip"); tmp = os.path.join(OUT, f"my_tmp_{tag}")
    t = time.time()
    for attempt in range(3):
        try:
            client().retrieve("sis-energy-derived-reanalysis", {
                "variable": [var], "spatial_aggregation": "original_grid",
                "energy_product_type": "capacity_factor_ratio", "temporal_aggregation": "hourly",
                "year": [str(y)], "month": [f"{m:02d}"]}, z)
            break
        except Exception as e:
            print(f"{tag} attempt {attempt+1} failed: {e}", flush=True); time.sleep(30)
    else:
        return f"{tag}: FAILED"
    try:
        os.makedirs(tmp, exist_ok=True)
        zipfile.ZipFile(z).extractall(tmp)
        ds = xr.open_dataset(glob.glob(os.path.join(tmp, "*.nc"))[0])
        da = ds[list(ds.data_vars)[0]].sel(latitude=LAT, longitude=LON)
        s = da.to_series().rename(f"{short}_{LAT}_{LON}")
        s.index.name = "time"
        s.to_frame().to_csv(cache)
        ds.close()
    finally:
        try:
            os.remove(z); shutil.rmtree(tmp, ignore_errors=True)
        except OSError:
            pass
    return f"{tag}: {len(s)} h, mean {s.mean():.3f}, {round(time.time()-t)} s"


def job_year(var, short, y, months):
    """one request for several months of one year (CDS queue time dominates, so fewer requests = faster);
    the returned NetCDF is split into the usual monthly cell files."""
    tag = f"{short}_{y}_yr"
    z = os.path.join(OUT, f"my_{tag}.zip"); tmp = os.path.join(OUT, f"my_tmp_{tag}")
    t = time.time()
    for attempt in range(3):
        try:
            client().retrieve("sis-energy-derived-reanalysis", {
                "variable": [var], "spatial_aggregation": "original_grid",
                "energy_product_type": "capacity_factor_ratio", "temporal_aggregation": "hourly",
                "year": [str(y)], "month": [f"{m:02d}" for m in months]}, z)
            break
        except Exception as e:
            print(f"{tag} attempt {attempt+1} failed: {e}", flush=True); time.sleep(30)
    else:
        return f"{tag}: FAILED"
    try:
        os.makedirs(tmp, exist_ok=True)
        zipfile.ZipFile(z).extractall(tmp)
        series = []
        for nc in glob.glob(os.path.join(tmp, "*.nc")):
            ds = xr.open_dataset(nc)
            series.append(ds[list(ds.data_vars)[0]].sel(latitude=LAT, longitude=LON).to_series())
            ds.close()
        s = pd.concat(series).sort_index(); s = s[~s.index.duplicated()]
        s.name = f"{short}_{LAT}_{LON}"; s.index.name = "time"
        out = []
        for m in months:
            sm = s[(s.index.year == y) & (s.index.month == m)]
            if len(sm):
                sm.to_frame().to_csv(os.path.join(OUT, f"cell_{short}_{y}_{m:02d}.csv")); out.append(m)
    finally:
        try:
            os.remove(z)
        except OSError:
            pass
        shutil.rmtree(tmp, ignore_errors=True)
    return f"{tag}: months written {out}, {len(s)} h, mean {s.mean():.3f}, {round(time.time()-t)} s"


if __name__ == "__main__" and os.environ.get("C3S_MODE") == "year":
    import pandas as pd
    todo = {}
    for y in range(2019, 2026):
        for m in range(1, 13):
            for v, s in VARS.items():
                if not os.path.exists(os.path.join(OUT, f"cell_{s}_{y}_{m:02d}.csv")):
                    todo.setdefault((v, s, y), []).append(m)
    print(f"{len(todo)} year requests: {[(s, y, len(ms)) for (v, s, y), ms in todo.items()]}", flush=True)
    with ThreadPoolExecutor(4) as ex:
        futs = [ex.submit(job_year, v, s, y, ms) for (v, s, y), ms in todo.items()]
        for f in as_completed(futs):
            try:
                print(f.result(), flush=True)
            except Exception as e:
                print("ERROR", e, flush=True)
    print("DONE", flush=True)
    raise SystemExit

if __name__ == "__main__":
    # C3S constraints: hourly original_grid CF exists for all months only from 2019; 1979-2018 January only
    ym = [(y, 1) for y in (2016, 2017, 2018)] + [(y, m) for y in range(2019, 2026) for m in range(1, 13)]
    jobs = [(v, s, y, m) for y, m in ym for v, s in VARS.items()]
    jobs = [j for j in jobs if not os.path.exists(os.path.join(OUT, f"cell_{j[1]}_{j[2]}_{j[3]:02d}.csv"))]
    print(f"{len(jobs)} months to download", flush=True)
    with ThreadPoolExecutor(4) as ex:
        futs = [ex.submit(job, *j) for j in jobs]
        for f in as_completed(futs):
            try:
                print(f.result(), flush=True)
            except Exception as e:
                print("ERROR", e, flush=True)
    print("DONE", flush=True)
