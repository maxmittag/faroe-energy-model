# Faroe Islands without oil: cable to Iceland or Scotland (Julia/JuMP model)

Group project, CBS course *Energy System Economics and Modelling* (48609), state 31.10.2026.

## What the model does

The model asks how the Faroese main grid can run one full year without oil, and what that costs per year.
It is a linear capacity expansion model (course reader ch. 7) for one year in hourly steps: the existing hydro,
wind, biogas and battery stay, and the model may build new wind, solar, batteries and pumped hydro.
A cable to Iceland or to Scotland (reader ch. 6.4) can import power at that country's hourly market price,
either with a fixed size (25/50/100 MW) or with a size the model chooses itself.

## Quick start (no download needed)

All raw data and all intermediate files are included. To reproduce the main results you only need step 6 of the pipeline.

```
julia install.jl                      # once: installs JuMP, HiGHS, CSV, DataFrames
cd scenarios_2030
julia run_all_import_only.jl is_2030  # Iceland, 2030 demand, about 5 min
```

Then compare `scenarios_2030/results_import_only/summary_is_2030.csv` with the table under "Main results".

## Folders

| Folder | What is in it |
|---|---|
| `data/` | `01_download.py` (SEV, Open-Meteo, Elexon) and its raw files in `data/raw/` |
| `data/raw/c3s/` | Copernicus C3S wind and solar capacity factors, one file per month 2016 to 2026 (the model uses Oct 2025 to Sep 2026) + `download_c3s.py` |
| `study/data/raw/` | Elma (Iceland) day-ahead prices + ECB exchange rates, `fetch_elma.py`, `analyze_elma.py` |
| `model_v3/` | `prepare_v3.py`: cleans the SEV data, builds demand, hydro inflow, biogas, Elma price. `MODEL.md`: model documentation with all equations |
| `model_v4/` | base model `model_v4.jl` + `run_v4.jl` (today's demand, export allowed, older results), `prepare_v4.py` (wind/solar from C3S) |
| `scenarios_2030/` | **current model and results**: `model_spike.jl`, `run_import_only.jl`, input files in `data/`, results in `results_import_only/`, checks in `CHECKS_import_only.md`, group deck `Faroe_2030_Scenarios_Group.pdf` |
| `scenarios_2030/results/` | archived: the same runs with export allowed (before the group decision of 28.10.) |
| `scenarios_2030/_archive_with_export/` | archived export runs, read by `make_summary_import_only.py` for the comparison column |

## Pipeline

Run every command from the folder of the script. On macOS use `python3` instead of `python`.

| Step | Command (folder) | Reads | Writes | Can skip? |
|---|---|---|---|---|
| 1 | `python 01_download.py` (`data/`) | SEV API, Open-Meteo, Elexon | `data/raw/*` | yes, files included |
|   | `python download_c3s.py` (`data/raw/c3s/`) | Copernicus CDS | `cell_*.csv`, `c3s_faroe_cf_hourly.csv` | yes, files included |
|   | `python fetch_elma.py elma_dayahead.csv`, then `python analyze_elma.py` (`study/data/raw/`) | elma.is, ECB files | `elma_dayahead.csv` with EUR prices | yes, files included |

The two ECB exchange rate files (`ecb_isk_eur_daily.csv`, `ecb_usd_eur_daily.csv`) were downloaded by hand as CSV
from data-api.ecb.europa.eu (series EXR D.ISK.EUR.SP00.A and D.USD.EUR.SP00.A); there is no script for them.
`analyze_elma.py` adds the EUR price column to `elma_dayahead.csv`, so run it only once on a fresh download.

| Step | Command (folder) | Reads | Writes | Can skip? |
|---|---|---|---|---|
| 2 | `python prepare_v3.py` (`model_v3/`) | SEV raw file, Elma prices | `model_v3/data/input_hourly.csv` | yes, file included |
| 3 | `python prepare_v4.py` (`model_v4/`) | v3 input + C3S files | `model_v4/data/input_hourly.csv` | yes, file included |
| 4 | `python make_gb_input.py` (`scenarios_2030/`) | v4 input + Elexon GB price | `scenarios_2030/data/input_hourly.csv` (copy) and `input_hourly_gb.csv` | yes, files included |
| 5 | `python scale_demand.py` (`scenarios_2030/`) | both files of step 4 | `input_hourly_2030.csv`, `input_hourly_gb_2030.csv` (demand x 1.186) | yes, files included |
| 6 | `julia run_import_only.jl` (`scenarios_2030/`), see below | `scenarios_2030/data/` | `results_import_only/summary_<is,gb>_<2030,today>.csv` | no, this is the model |
| 7 | `python make_summary_import_only.py` (`scenarios_2030/`) | the four summaries | `summary_2030.csv`, `summary_today.csv` | |

What each input file contains (8,760 rows, model year 1 Oct 2025 to 30 Sep 2026, UTC):
`demand` (MW), `ava_wind`, `ava_pv` (capacity factor 0 to 1), `hydro_inflow` (MWh per hour), `biogas` (MW, fixed),
`pi` (import price, EUR/MWh). The Scotland files differ only in `pi`, the 2030 files only in `demand`.

### Step 6 in detail

`run_import_only.jl` is controlled by environment variables. One call = one counterpart and one demand case:

| Set | SPIKE_TAG | SPIKE_DEMAND_CASE | SPIKE_INPUT | SPIKE_CABLE_KM |
|---|---|---|---|---|
| Iceland, 2030 | is | 2030 | input_hourly_2030.csv | 450 |
| Scotland, 2030 | gb | 2030 | input_hourly_gb_2030.csv | 400 |
| Iceland, today | is | today | input_hourly.csv | 450 |
| Scotland, today | gb | today | input_hourly_gb.csv | 400 |

`SPIKE_NO_EXPORT=1` is always required (import only). The easiest way is the launcher, which sets everything
and works the same on Windows and macOS:

```
cd scenarios_2030
julia run_all_import_only.jl            # all four sets
julia run_all_import_only.jl gb_2030    # one set: is_2030, gb_2030, is_today or gb_today
```

Or set the variables yourself, example Iceland 2030:

macOS / Linux / Git Bash:
```
SPIKE_NO_EXPORT=1 SPIKE_TAG=is SPIKE_DEMAND_CASE=2030 SPIKE_INPUT=input_hourly_2030.csv SPIKE_CABLE_KM=450 julia run_import_only.jl
```

Windows PowerShell (the variables stay set in this window, so set all five every time):
```
$env:SPIKE_NO_EXPORT="1"; $env:SPIKE_TAG="is"; $env:SPIKE_DEMAND_CASE="2030"; $env:SPIKE_INPUT="input_hourly_2030.csv"; $env:SPIKE_CABLE_KM="450"; julia run_import_only.jl
```

Julia prints warnings about `t0` and `m` "in soft scope". They are harmless.

The `check_*.jl` scripts are the extra plausibility checks described in `CHECKS_import_only.md`; their
first lines show how to call them.

## Installation

- **Julia** 1.10 or newer (tested with 1.13.1), from https://julialang.org/downloads. Then once: `julia install.jl`
  (installs JuMP, HiGHS, CSV, DataFrames into your default environment; tested with JuMP 1.32, HiGHS 1.26).
- **Python** 3.10 or newer (tested with 3.11): `pip install -r requirements.txt` (pandas, numpy, tzdata, matplotlib).
  Only for re-downloading the Copernicus data you also need `cdsapi`, `xarray`, `netCDF4` and a free
  Copernicus CDS account with the key in `~/.cdsapirc` (see https://cds.climate.copernicus.eu/how-to-api).
  You must also accept the dataset licence once on the dataset web page.

## Runtime

- Python steps 2 to 5 and 7: a few seconds each.
- Julia: about 1 min to load the packages, then about 40 to 80 s per case (HiGHS interior point).
  One set has 5 or 6 cases, so about 4 to 7 min. All four sets: about 20 to 25 min.
- Re-downloading the raw data (step 1): SEV about 1 h (4 s pause per week of data), C3S 30 min or more (queue).

## Main results (import only)

Extra cost per year compared with today, M EUR (`results_import_only/summary_2030.csv` and `summary_today.csv`):

| Case | 2030 demand (578 GWh) | Today's demand (488 GWh) |
|---|---|---|
| No cable | 24.77 | 16.87 |
| Iceland 25 / 50 / 100 MW | 12.38 / 11.06 / 19.39 | 6.25 / 9.85 / 18.23 |
| Iceland, size chosen by model | 9.33 (35.0 MW) | 6.21 (25.2 MW) |
| Scotland 25 / 50 / 100 MW | 15.56 / 17.29 / 24.66 | 10.36 / 13.56 / 21.16 |
| Scotland, size chosen by model | 15.15 (31.2 MW) | 10.14 (21.6 MW) |

## Main assumptions

- **One model year** for all hourly data: 1 Oct 2025 to 30 Sep 2026 (8,760 h, UTC).
- **No oil** in any hour; demand must be met in every hour.
- **Import only** (group decision 28.10.2026): the cable never exports (`NoExport[t]: F_FO_IS[t] == 0`).
- **2030 demand** = today's hourly profile x 600/506 = **1.186** (578.5 GWh, peak 92.6 MW).
- **Cable lengths**: Iceland **450 km**, Scotland **400 km** (NAEN 2016, p. 9 and Table 1 p. 45, [PDF](https://vatnsidnadur.net/wp-content/uploads/2016/03/North-Atlantic-Energy-Network-Report.pdf)).
  Cable cost 3,220 EUR per MW and km plus 640,000 EUR per MW for the converters, 40 years, 5 % interest
  (DEA transport catalogue).
- **Prices**: Iceland = Elma day-ahead price (ISK converted with the ECB daily rate). Scotland = Elexon
  GB Market Index price (provider APXMIDP) x **1.16 EUR/GBP**. Both countries are price takers: they deliver
  any amount up to the cable size at that price.
- **Wind and solar**: weather based capacity factors from Copernicus C3S (ERA5), grid cell 62.25 N / 6.75 W,
  not historical output (lecturer advice, historical output contains curtailment).
- **Existing plants**: hydro 37.3 MW with a 5.85 GWh reservoir, wind 61.55 MW, battery 12 MW / 12.5 MWh,
  biogas as produced. New pumped hydro is limited to the Mýruverkið II site (40 MW turbine, 70 MW pump).
  All costs and capacities with their sources are in `technologies.csv`.

For the full equations read `model_v3/MODEL.md`. It describes model v3; v4 only replaces the wind and solar
profiles, and `scenarios_2030/model_spike.jl` adds three switches (cable size as a variable, cable length,
import only). All sanity checks of the current runs are in `scenarios_2030/CHECKS_import_only.md`.

## Data sources and licences

| Data | Source | Licence / terms |
|---|---|---|
| Hourly production per plant (demand, hydro, biogas) | SEV, www.sev.fo/api/elproduction | public data of the Faroese utility, no licence stated; cite SEV |
| Wind and solar capacity factors | Copernicus Climate Change Service (C3S), *Climate and energy indicators for Europe* (sis-energy-derived-reanalysis) | CC-BY 4.0, cite "Copernicus Climate Change Service" |
| Weather (only used for early checks) | Open-Meteo archive API (ERA5) | CC-BY 4.0 |
| GB day-ahead price | Elexon BMRS, Market Index Data | BMRS Data Licence (free use with attribution to Elexon) |
| Iceland day-ahead price | Elma, elma.is/en/market-data/day-ahead | public market data, no licence stated; cite Elma |
| Exchange rates ISK/EUR, USD/EUR | European Central Bank, data-api.ecb.europa.eu | free reuse with source attribution |
| Cable lengths | NAEN (2016) *North Atlantic Energy Network*, [PDF](https://vatnsidnadur.net/wp-content/uploads/2016/03/North-Atlantic-Energy-Network-Report.pdf) | report, cite |
| Technology costs | Danish Energy Agency technology catalogues, Tróndheim et al. 2021 | see `technologies.csv` |

## Reproducibility test (31.10.2026)

The package was unzipped into an empty folder and rebuilt from the raw data:

- Steps 2 to 5 (`prepare_v3.py`, `prepare_v4.py`, `make_gb_input.py`, `scale_demand.py`) after deleting all
  input files: all six `input_hourly*.csv` files are **byte for byte identical** (same md5) to the shipped ones,
  also `input_hourly_gb.csv`, whose original was made by hand in a test run on 28.10.
- Step 6, Iceland 2030 (5 cases, `run_import_only.jl`, 4 min 20 s): every number in `summary_is_2030.csv` is
  identical to the shipped file (cost difference 0.0 EUR in all cases, e.g. model-chosen cable 34.96 MW, 9.33 M EUR).
  `make_summary_import_only.py` then reproduces `summary_2030.csv` and `summary_today.csv` exactly.
- Step 6, Scotland today (5 cases, launcher `run_all_import_only.jl gb_today`, 4 min): identical as well
  (cost difference 0.0 EUR, model-chosen cable 21.62 MW, 10.14 M EUR). This run uses the rebuilt `input_hourly_gb.csv`.

Note for re-downloads: `01_download.py` downloads up to yesterday and only appends missing weeks to an existing
SEV file; `prepare_v3.py` cuts out the model year, so newer data does not change the inputs unless SEV revises
old values. For a clean download delete the files in `data/raw/` first.
